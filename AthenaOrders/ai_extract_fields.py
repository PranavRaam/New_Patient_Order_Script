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

    print(f"[Azure] Analyzing (bytes={len(pdf_bytes)})")
    poller = client.begin_analyze_document(
        AZURE_MODEL,              # model_id positional
        body=pdf_bytes,           # changed from document= to body=
        content_type="application/pdf"
    )
    result = poller.result()
    print("[Azure] analysis completed")

    extracted: Dict[str, str] = {}

    # Collect key-value pairs (supports prebuilt-document or custom model)
    if hasattr(result, "key_value_pairs"):
        for kvp in result.key_value_pairs:
            if kvp.key and kvp.value:
                key = kvp.key.content.strip().lower()
                value = kvp.value.content.strip()
                extracted[key] = value
    else:
        # Fallback – extract from fields attribute
        for name, field in getattr(result, "fields", {}).items():
            if field and field.content:
                extracted[name.lower()] = field.content.strip()

    return extracted


def map_fields(kv: Dict[str, str]) -> Dict[str, str]:
    """Map arbitrary keys from Azure output to the few we care about."""
    def first(*candidates):
        for cand in candidates:
            if cand in kv:
                return kv[cand]
        return ""

    return {
        "doc_id": kv.get("documentid", ""),
        "mrn": first("mrn", "medical record number", "patient id"),
        "dob": first("dob", "date of birth", "birth date"),
        "start_of_care": first("start of care", "soc"),
        "episode_start": first("episode start", "cert period from", "episode start date"),
        "episode_end": first("episode end", "cert period to", "episode end date"),
    }

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
                kv_pairs = analyze_with_azure(pdf_bytes)
                mapped = map_fields(kv_pairs)
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