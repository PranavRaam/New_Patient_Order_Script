import os
import csv
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List

import requests

###############################################################################
# Config – replace the placeholder values below or load them from environment #
###############################################################################

DA_TOKEN_URL = "https://backoffice.doctoralliance.com/token"          # OAuth-style token endpoint
DA_USERNAME   = "sannidhay"
DA_PASSWORD   = "DA@2025"
DA_DOCUMENT_URL = "https://backoffice.doctoralliance.com/api/documents/{doc_id}"
DA_PATIENT_URL  = "https://backoffice.doctoralliance.com/api/patients/{patient_id}"

PG_BASE_URL   = "https://live.doctoralliance.com/api"                 # Example endpoint
PG_API_KEY    = "your_pg_api_key"
PG_CREATE_PATIENT = f"{PG_BASE_URL}/patients"                         # POST

INPUT_CSV     = "Inbox/failed_orders.csv"  # Spencer’s failure sheet – update as needed
OUTPUT_CSV    = f"Patients_Created_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"

# Folder where PDFs were downloaded – not mandatory in this minimal version
PDF_FOLDER    = "Downloads/PDFs"

# ----------------------------------------------------------------------------
logging.basicConfig(
    filename="patient_creation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_da_token() -> str:
    """Fetch JWT access_token from DA."""
    data = {
        "grant_type": "password",
        "username": DA_USERNAME,
        "password": DA_PASSWORD
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(DA_TOKEN_URL, data=data, headers=headers, timeout=30)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Could not retrieve DA token")
    return token


def da_get(url: str, token: str) -> dict:
    """Helper to GET from DA with bearer token."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_da_patient_info(doc_id: str, token: str) -> Optional[Dict]:
    """Given a document ID, return the DA patient details dict or None."""
    try:
        doc = da_get(DA_DOCUMENT_URL.format(doc_id=doc_id), token)
        patient_id = str(doc.get("value", {}).get("patientId"))
        if not patient_id:
            logging.warning(f"No patientId in doc {doc_id}")
            return None
        patient = da_get(DA_PATIENT_URL.format(patient_id=patient_id), token)
        return patient.get("value")
    except Exception as e:
        logging.error(f"DA fetch failed for doc {doc_id}: {e}")
        return None


def build_pg_payload(patient_info: Dict) -> Dict:
    """Transform DA patient data -> PG payload (minimal fields)."""
    info = patient_info.get("patientInfo", {}) if patient_info else {}

    def _clean(val):
        return val or ""

    name = _clean(info.get("name"))
    first_name = _clean(info.get("firstName"))
    last_name = _clean(info.get("lastName"))
    dob = _clean(info.get("dob"))
    mrn = _clean(info.get("medicalRecordNumber"))

    # Fallback if first/last not split
    if not first_name or not last_name:
        if "," in name:
            last_name, first_name = [p.strip() for p in name.split(",", 1)]

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "mrn": mrn,
        # These two company IDs might come from Spencer’s sheet; we’ll leave blank here.
        "company_id": "",
        "company_pg_id": "",
        "source": "automated_da_bot"
    }
    return payload


def create_pg_patient(payload: Dict) -> Tuple[bool, str]:
    """POST payload to PG. Returns (success, patient_id_or_error)."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": PG_API_KEY
    }
    try:
        resp = requests.post(PG_CREATE_PATIENT, headers=headers, json=payload, timeout=30)
        if resp.status_code == 201:
            pid = resp.json().get("id") or "created"
            return True, str(pid)
        elif resp.status_code == 409:
            return True, "exists"
        else:
            return False, f"{resp.status_code} {resp.text}"
    except Exception as e:
        return False, str(e)


def process_failure_sheet():
    token = get_da_token()

    with open(INPUT_CSV, newline="", encoding="utf-8") as infile, \
         open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["creation_status", "pg_patient_result"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            doc_id = row.get("ID") or row.get("Doc_ID") or ""
            if not doc_id:
                row["creation_status"] = "skipped – no doc_id"
                row["pg_patient_result"] = ""
                writer.writerow(row)
                continue

            logging.info(f"Processing doc_id {doc_id} for patient {row.get('Patient')}")

            patient_info = fetch_da_patient_info(doc_id, token)
            if not patient_info:
                row["creation_status"] = "failed – DA lookup"
                row["pg_patient_result"] = ""
                writer.writerow(row)
                continue

            payload = build_pg_payload(patient_info)
            success, result = create_pg_patient(payload)

            row["creation_status"] = "CREATED" if success else "FAILED"
            row["pg_patient_result"] = result
            writer.writerow(row)
            # Quick pause to respect rate-limits
            time.sleep(0.3)

    print(f"✅ Patient creation run complete. Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    process_failure_sheet() 