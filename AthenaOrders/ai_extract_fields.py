import csv
import io
import os
import sys
import base64
import time
import re
from datetime import datetime
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient  # type: ignore
    from azure.core.credentials import AzureKeyCredential  # type: ignore
except ImportError:
    print("\n[ERROR] azure-ai-documentintelligence package not found.\nInstall it with:  pip install azure-ai-documentintelligence==1.0.2\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration – load from .env or set directly here
# ---------------------------------------------------------------------------
load_dotenv()

AUTH_TOKEN   = os.getenv("AUTH_TOKEN", "")
DA_GETFILE_URL = os.getenv("DA_GETFILE_URL", "https://api.doctoralliance.com/document/getfile?docId.id={doc_id}")

AZURE_ENDPOINT = os.getenv("AZURE_FORM_ENDPOINT", "")  # e.g. https://<resource>.cognitiveservices.azure.com/
AZURE_KEY      = os.getenv("AZURE_FORM_KEY", "")
AZURE_MODEL    = os.getenv("AZURE_FORM_MODEL", "prebuilt-layout")  # Use prebuilt-layout for diverse formats

INPUT_CSV      = sys.argv[1] if len(sys.argv) > 1 else "Inbox/Inbox_Extracted_Data.csv"
TIMESTAMP      = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_CSV     = f"csv_outputs/Extracted_{TIMESTAMP}.csv"

# Create the output directory if it doesn't exist
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_da_token() -> str:
    """Return the pre-generated AUTH_TOKEN from environment."""
    if not AUTH_TOKEN:
        raise RuntimeError("AUTH_TOKEN not set in environment or .env file")
    return AUTH_TOKEN


def fetch_pdf_bytes(doc_id: str, token: str) -> bytes:
    url = DA_GETFILE_URL.format(doc_id=doc_id)
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[DA] GET {url}")
    r = requests.get(url, headers=headers, timeout=60)
    print(f"[DA] status {r.status_code}")
    payload = r.json().get("value", {})
    buffer_b64 = payload.get("documentBuffer")

    # Some instances require a JSON body with caretakerId to retrieve the buffer
    if not buffer_b64:
        print("[DA] missing buffer -> retry with body")
        request_body = {
            "onlyUnfiled": True,
            "careProviderId": {"id": 0, "externalId": ""},
            "dateFrom": None,
            "dateTo": None,
            "page": 1,
            "recordsPerPage": 10
        }
        r2 = requests.get(url, headers=headers, json=request_body, timeout=60)
        print(f"[DA] second attempt status {r2.status_code}")
        payload = r2.json().get("value", {})
        buffer_b64 = payload.get("documentBuffer")

    if not buffer_b64:
        raise RuntimeError("documentBuffer missing in response")
    pdf_bytes = base64.b64decode(buffer_b64)
    print(f"[DA] retrieved {len(pdf_bytes)} bytes")
    return pdf_bytes


def analyze_with_azure_robust(pdf_bytes: bytes) -> Dict[str, str]:
    """
    Multi-strategy extraction for diverse physician group formats
    """
    credential = AzureKeyCredential(AZURE_KEY)
    client = DocumentIntelligenceClient(AZURE_ENDPOINT, credential)

    print(f"[Azure] Multi-strategy analysis (bytes={len(pdf_bytes)})")
    
    # Strategy 1: Use prebuilt-layout for general structure
    try:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=pdf_bytes,
            content_type="application/pdf"
        )
        result = poller.result()
        print("[Azure] prebuilt-layout analysis completed")
    except Exception as e:
        print(f"[Azure] prebuilt-layout failed: {e}")
        # Fallback to prebuilt-read
        poller = client.begin_analyze_document(
            "prebuilt-read",
            body=pdf_bytes,
            content_type="application/pdf"
        )
        result = poller.result()
        print("[Azure] prebuilt-read analysis completed")

    extracted = {}
    
    # Strategy 1: Extract from key-value pairs (if available)
    if hasattr(result, "key_value_pairs") and result.key_value_pairs:
        print("[Azure] Extracting from key-value pairs")
        for kvp in result.key_value_pairs:
            if kvp.key and kvp.value:
                key = kvp.key.content.strip().lower()
                value = kvp.value.content.strip()
                extracted[key] = value
    
    # Strategy 2: Extract from tables (common in medical forms)
    if hasattr(result, "tables") and result.tables:
        print("[Azure] Extracting from tables")
        for table_idx, table in enumerate(result.tables):
            for cell in table.cells:
                if cell.content and len(cell.content.strip()) > 1:
                    # Create meaningful keys from table context
                    cell_key = f"table_{table_idx}_r{cell.row_index}_c{cell.column_index}"
                    extracted[cell_key] = cell.content.strip()
    
    # Strategy 3: Extract from paragraphs (for unstructured text)
    if hasattr(result, "paragraphs") and result.paragraphs:
        print("[Azure] Extracting from paragraphs")
        for para_idx, paragraph in enumerate(result.paragraphs):
            if paragraph.content:
                para_key = f"paragraph_{para_idx}"
                extracted[para_key] = paragraph.content.strip()
    
    # Strategy 4: Regex patterns on full content (for any format)
    if hasattr(result, "content") and result.content:
        print("[Azure] Applying regex patterns")
        content = result.content.lower()
        
        # Comprehensive patterns for USA physician groups
        patterns = {
            "mrn": [
                r"(?:mrn|medical record|patient id|record number|chart #|patient #)[\s:]*([a-zA-Z0-9\-]{3,20})",
                r"(?:id|identifier|record|chart)[\s:]*([a-zA-Z0-9\-]{5,15})",
                r"(?:pt|patient)[\s:]*(?:id|#)[\s:]*([a-zA-Z0-9\-]{3,15})"
            ],
            "dob": [
                r"(?:dob|date of birth|birth date|born)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:d\.o\.b\.?)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:birthday|birth)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
            ],
            "start_of_care": [
                r"(?:start of care|soc|care start|episode start)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:episode begins?|period from)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:certification period)[\s:]*(?:from)?[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
            ],
            "episode_start": [
                r"(?:episode start|cert period from|certification from)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:period starts?|from date)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:effective date|start date)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
            ],
            "episode_end": [
                r"(?:episode end|cert period to|certification to)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:period ends?|to date|through)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                r"(?:expiration date|end date)[\s:]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
            ],
            "patient_name": [
                r"(?:patient name|patient|name|client name)[\s:]*([a-zA-Z\s,\.]{5,50})",
                r"(?:pt name|client)[\s:]*([a-zA-Z\s,\.]{5,50})"
            ]
        }
        
        # Apply multiple patterns per field for better coverage
        for field, pattern_list in patterns.items():
            if field not in extracted or not extracted[field]:
                for pattern in pattern_list:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if len(value) > 2:  # Minimum viable data
                            extracted[field] = value
                            break
    
    # Strategy 5: Look for patterns in any text content
    all_text = ""
    if hasattr(result, "content"):
        all_text = result.content
    elif extracted:
        all_text = " ".join(str(v) for v in extracted.values())
    
    if all_text and len(extracted) < 3:
        print("[Azure] Emergency pattern matching on all text")
        # Emergency broad patterns
        emergency_patterns = {
            "mrn": r"(?:^|\s)([A-Z0-9]{6,15})(?:\s|$)",
            "dob": r"([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
            "dates": r"([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{4})"
        }
        
        for field, pattern in emergency_patterns.items():
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                if field == "dates":
                    # Assign dates to missing fields
                    date_fields = ["start_of_care", "episode_start", "episode_end"]
                    for i, date_field in enumerate(date_fields):
                        if date_field not in extracted and i < len(matches):
                            extracted[date_field] = matches[i]
                else:
                    if field not in extracted:
                        extracted[field] = matches[0]
    
    print(f"[Azure] Extracted {len(extracted)} fields using multi-strategy approach")
    return extracted


def map_fields(extracted_data: Dict[str, str]) -> Dict[str, str]:
    """Map extracted data to our target fields"""
    mapped = {
        "mrn": "",
        "dob": "",
        "start_of_care": "",
        "episode_start": "",
        "episode_end": ""
    }
    
    # Direct mapping
    for target_field in mapped.keys():
        if target_field in extracted_data:
            mapped[target_field] = extracted_data[target_field]
    
    # Fuzzy mapping for variations
    for key, value in extracted_data.items():
        key_lower = key.lower()
        
        # MRN variations
        if not mapped["mrn"] and any(term in key_lower for term in ["mrn", "medical", "record", "patient", "id", "chart"]):
            if re.match(r"^[A-Z0-9\-]{3,20}$", value.strip()):
                mapped["mrn"] = value.strip()
        
        # DOB variations  
        if not mapped["dob"] and any(term in key_lower for term in ["dob", "birth", "born"]):
            if re.match(r"[0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4}", value.strip()):
                mapped["dob"] = value.strip()
        
        # Date field variations
        if re.match(r"[0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4}", value.strip()):
            if not mapped["start_of_care"] and any(term in key_lower for term in ["start", "care", "soc"]):
                mapped["start_of_care"] = value.strip()
            elif not mapped["episode_start"] and any(term in key_lower for term in ["episode", "from", "begin"]):
                mapped["episode_start"] = value.strip()
            elif not mapped["episode_end"] and any(term in key_lower for term in ["end", "to", "through", "expir"]):
                mapped["episode_end"] = value.strip()
    
    return mapped

# ---------------------------------------------------------------------------
# Main procedure
# ---------------------------------------------------------------------------

def main():
    token = get_da_token()

    with open(INPUT_CSV, newline="", encoding="utf-8") as src, \
         open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as dest:

        reader = csv.DictReader(src)
        fieldnames = reader.fieldnames + [
            "mrn", "dob", "start_of_care", "episode_start", "episode_end"
        ]
        writer = csv.DictWriter(dest, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            doc_id = row.get("ID") or row.get("DocID") or row.get("DocumentID") or ""
            if not doc_id:
                writer.writerow(row)
                continue

            try:
                print(f"Processing {doc_id} …", end=" ")
                pdf_bytes = fetch_pdf_bytes(doc_id, token)
                extracted_data = analyze_with_azure_robust(pdf_bytes)
                mapped = map_fields(extracted_data)
                
                # Add extracted fields to row
                for k, v in mapped.items():
                    if v:
                        row[k] = v
                
                writer.writerow(row)
                print("✔️")
                
            except Exception as e:
                print(f"Failed: {e}")
                writer.writerow(row)
                continue
            time.sleep(0.2)  # rudimentary rate-limit

    print(f"\nDone. Extracted data written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main() 