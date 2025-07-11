import csv
import io
import os
import sys
import base64
import time
from datetime import datetime
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient  # type: ignore
    from azure.core.credentials import AzureKeyCredential  # type: ignore
except ImportError:
    print("\n[ERROR] azure-ai-documentintelligence package not found.\nInstall it with:  pip install azure-ai-documentintelligence==1.0.0b2\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration – load from .env or set directly here
# ---------------------------------------------------------------------------
load_dotenv()

AUTH_TOKEN   = os.getenv("AUTH_TOKEN", "")
DA_GETFILE_URL = os.getenv("DA_GETFILE_URL", "https://api.doctoralliance.com/document/getfile?docId.id={doc_id}")

AZURE_ENDPOINT = os.getenv("AZURE_FORM_ENDPOINT", "")  # e.g. https://<resource>.cognitiveservices.azure.com/
AZURE_KEY      = os.getenv("AZURE_FORM_KEY", "")
AZURE_MODEL    = os.getenv("AZURE_FORM_MODEL", "prebuilt-document")  # or custom model id

INPUT_CSV      = sys.argv[1] if len(sys.argv) > 1 else "Inbox/Inbox_Extracted_Data.csv"
TIMESTAMP      = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_CSV     = f"csv_outputs/Extracted_{TIMESTAMP}.csv"

# Create the output directory if it doesn’t exist
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


def analyze_with_azure(pdf_bytes: bytes) -> Dict[str, str]:
    credential = AzureKeyCredential(AZURE_KEY)
    client = DocumentIntelligenceClient(AZURE_ENDPOINT, credential)

    print(f"[Azure] Analyzing (bytes={len(pdf_bytes)}) with custom model: {AZURE_MODEL}")
    
    try:
        poller = client.begin_analyze_document(
            AZURE_MODEL,              # Your custom model ID
            body=pdf_bytes,
            content_type="application/pdf"
        )
        result = poller.result()
        print("[Azure] Custom model analysis completed")
    except Exception as e:
        print(f"[Azure] Error with custom model: {e}")
        # If custom model fails, don't fallback - fix the model instead
        raise e

    extracted: Dict[str, str] = {}

    # For custom models, extract from fields (trained fields)
    if hasattr(result, "documents") and result.documents:
        document = result.documents[0]  # Get first document
        
        if hasattr(document, "fields") and document.fields:
            print(f"[Azure] Found {len(document.fields)} trained fields")
            for field_name, field_value in document.fields.items():
                if field_value and field_value.content:
                    extracted[field_name.lower()] = field_value.content.strip()
                    print(f"[Azure] Extracted {field_name}: {field_value.content.strip()}")
        else:
            print("[Azure] No fields found in custom model response")
    
    # Fallback: Extract from key-value pairs if fields are empty
    if not extracted and hasattr(result, "key_value_pairs") and result.key_value_pairs:
        print("[Azure] Fallback to key-value pairs")
        for kvp in result.key_value_pairs:
            if kvp.key and kvp.value:
                key = kvp.key.content.strip().lower()
                value = kvp.value.content.strip()
                extracted[key] = value
    
    # Additional fallback: Pattern matching from content
    if len(extracted) < 3 and hasattr(result, "content") and result.content:
        print("[Azure] Fallback to pattern matching")
        content = result.content.lower()
        
        # Enhanced patterns for medical documents
        patterns = {
            "mrn": [
                r"(?:mrn|medical record|patient id|record number|chart #)[\s:]*([^\s\n,]+)",
                r"(?:mr #|mr#|patient #)[\s:]*([^\s\n,]+)"
            ],
            "dob": [
                r"(?:dob|date of birth|birth date|born)[\s:]*([0-9/\-]{8,10})",
                r"(?:d\.o\.b\.?)[\s:]*([0-9/\-]{8,10})"
            ],
            "patient_name": [
                r"(?:patient name|patient|name)[\s:]*([a-zA-Z\s,]+?)(?:\n|$|dob|mrn)",
                r"(?:client name)[\s:]*([a-zA-Z\s,]+?)(?:\n|$)"
            ],
            "start_of_care": [
                r"(?:start of care|soc|care start)[\s:]*([0-9/\-]{8,10})",
                r"(?:effective date|start date)[\s:]*([0-9/\-]{8,10})"
            ],
            "episode_start": [
                r"(?:episode start|cert period from|from date)[\s:]*([0-9/\-]{8,10})",
                r"(?:certification from)[\s:]*([0-9/\-]{8,10})"
            ],
            "episode_end": [
                r"(?:episode end|cert period to|to date)[\s:]*([0-9/\-]{8,10})",
                r"(?:certification to)[\s:]*([0-9/\-]{8,10})"
            ]
        }
        
        import re
        for field, pattern_list in patterns.items():
            if field not in extracted:
                for pattern in pattern_list:
                    match = re.search(pattern, content)
                    if match:
                        extracted[field] = match.group(1).strip()
                        print(f"[Azure] Pattern matched {field}: {extracted[field]}")
                        break

    print(f"[Azure] Total extracted fields: {len(extracted)}")
    return extracted


def map_fields(extracted: Dict[str, str]) -> Dict[str, str]:
    """Map extracted fields to expected output columns"""
    mapped = {}
    
    # Direct mapping for custom model fields
    field_mapping = {
        "mrn": "mrn",
        "dob": "dob", 
        "patient_name": "patient_name",
        "start_of_care": "start_of_care",
        "episode_start": "episode_start",
        "episode_end": "episode_end"
    }
    
    for extracted_key, output_key in field_mapping.items():
        if extracted_key in extracted:
            mapped[output_key] = extracted[extracted_key]
    
    # Handle common variations in extracted field names
    variations = {
        "mrn": ["medical_record_number", "patient_id", "record_number", "chart_number"],
        "dob": ["date_of_birth", "birth_date", "birthdate"],
        "start_of_care": ["soc", "care_start_date", "effective_date"],
        "episode_start": ["episode_start_date", "cert_from", "certification_from"],
        "episode_end": ["episode_end_date", "cert_to", "certification_to"]
    }
    
    for target_field, variations_list in variations.items():
        if target_field not in mapped:
            for variation in variations_list:
                if variation in extracted:
                    mapped[target_field] = extracted[variation]
                    break
    
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
            "mrn", "dob", "patient_name", "start_of_care", "episode_start", "episode_end"
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
                extracted_fields = analyze_with_azure(pdf_bytes)
                mapped_fields = map_fields(extracted_fields)
                for k, v in mapped_fields.items():
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