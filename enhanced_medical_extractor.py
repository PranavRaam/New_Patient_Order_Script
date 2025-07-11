#!/usr/bin/env python3
"""
Enhanced Medical Document Extractor for PGs and HHAs
Handles: Patient Orders, POC, Face-to-face, Lab Reports, 485 Certificates
Extracts: Patient Name, DOB, Start of Care, Episode Dates, ICD Codes
"""
import csv
import io
import os
import sys
import base64
import time
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
except ImportError:
    print("\n[ERROR] azure-ai-documentintelligence package not found.")
    print("Install it with: pip install azure-ai-documentintelligence==1.0.2")
    sys.exit(1)

# Load configuration
load_dotenv()

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
DA_GETFILE_URL = os.getenv("DA_GETFILE_URL", "https://api.doctoralliance.com/document/getfile?docId.id={doc_id}")

AZURE_ENDPOINT = os.getenv("AZURE_FORM_ENDPOINT", "")
AZURE_KEY = os.getenv("AZURE_FORM_KEY", "")
AZURE_MODEL = os.getenv("AZURE_FORM_MODEL", "prebuilt-layout")

INPUT_CSV = sys.argv[1] if len(sys.argv) > 1 else "AthenaOrders/Inbox/Inbox_Extracted_Data.csv"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_CSV = f"csv_outputs/Medical_Extracted_{TIMESTAMP}.csv"

# Create output directory
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

class MedicalDocumentExtractor:
    def __init__(self):
        self.client = DocumentIntelligenceClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))
        
    def fetch_pdf_bytes(self, doc_id: str, token: str) -> bytes:
        """Fetch PDF from DA API"""
        url = DA_GETFILE_URL.format(doc_id=doc_id)
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"[DA] GET {url}")
        response = requests.get(url, headers=headers, timeout=60)
        print(f"[DA] status {response.status_code}")
        
        payload = response.json().get("value", {})
        buffer_b64 = payload.get("documentBuffer")
        
        # Retry with JSON body if no buffer
        if not buffer_b64:
            print("[DA] missing buffer -> retry with body")
            request_body = {
                "onlyUnfiled": True,
                "careProviderId": {"id": 0, "externalId": ""},
                "dateFrom": None, "dateTo": None,
                "page": 1, "recordsPerPage": 10
            }
            response = requests.get(url, headers=headers, json=request_body, timeout=60)
            print(f"[DA] second attempt status {response.status_code}")
            payload = response.json().get("value", {})
            buffer_b64 = payload.get("documentBuffer")
        
        if not buffer_b64:
            raise RuntimeError("documentBuffer missing in response")
            
        pdf_bytes = base64.b64decode(buffer_b64)
        print(f"[DA] retrieved {len(pdf_bytes)} bytes")
        return pdf_bytes
    
    def analyze_document(self, pdf_bytes: bytes) -> Dict[str, str]:
        """Analyze document using Azure Document Intelligence"""
        print(f"[Azure] Analyzing medical document (bytes={len(pdf_bytes)})")
        
        try:
            poller = self.client.begin_analyze_document(
                AZURE_MODEL,
                body=pdf_bytes,
                content_type="application/pdf"
            )
            result = poller.result()
            print("[Azure] analysis completed")
        except Exception as e:
            if "ModelNotFound" in str(e):
                print(f"[Azure] Model {AZURE_MODEL} not found, trying prebuilt-layout")
                poller = self.client.begin_analyze_document(
                    "prebuilt-layout",
                    body=pdf_bytes,
                    content_type="application/pdf"
                )
                result = poller.result()
                print("[Azure] analysis completed with prebuilt-layout")
            else:
                raise e
        
        return self.extract_medical_fields(result)
    
    def extract_medical_fields(self, result) -> Dict[str, str]:
        """Extract specific medical fields from Azure result"""
        extracted = {}
        
        # Extract from key-value pairs
        if hasattr(result, "key_value_pairs") and result.key_value_pairs:
            for kvp in result.key_value_pairs:
                if kvp.key and kvp.value:
                    key = kvp.key.content.strip().lower()
                    value = kvp.value.content.strip()
                    extracted[key] = value
        
        # Extract from tables
        if hasattr(result, "tables") and result.tables:
            for table in result.tables:
                for cell in table.cells:
                    if cell.content and cell.content.strip():
                        extracted[f"table_r{cell.row_index}_c{cell.column_index}"] = cell.content.strip()
        
        # Extract from full text using patterns
        if hasattr(result, "content") and result.content:
            pattern_matches = self.extract_with_patterns(result.content)
            extracted.update(pattern_matches)
        
        return self.map_to_target_fields(extracted)
    
    def extract_with_patterns(self, content: str) -> Dict[str, str]:
        """Extract fields using regex patterns for medical documents"""
        content_lower = content.lower()
        patterns = {}
        
        # Patient Name patterns
        name_patterns = [
            r"patient\s*name[:\s]*([^\n\r]+)",
            r"name[:\s]*([^\n\r]+)",
            r"patient[:\s]*([^\n\r]+)",
            r"client\s*name[:\s]*([^\n\r]+)"
        ]
        
        # DOB patterns
        dob_patterns = [
            r"(?:dob|date\s*of\s*birth|birth\s*date|born)[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
            r"d\.o\.b[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
        ]
        
        # Start of Care patterns
        soc_patterns = [
            r"(?:start\s*of\s*care|soc|care\s*start)[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
            r"(?:admission\s*date|admit\s*date)[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
        ]
        
        # Episode dates patterns
        episode_start_patterns = [
            r"(?:episode\s*start|cert\s*period\s*from|episode\s*from)[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
            r"(?:from\s*date|period\s*from)[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
        ]
        
        episode_end_patterns = [
            r"(?:episode\s*end|cert\s*period\s*to|episode\s*to)[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
            r"(?:to\s*date|period\s*to)[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"
        ]
        
        # MRN patterns
        mrn_patterns = [
            r"(?:mrn|medical\s*record|patient\s*id|record\s*number|chart\s*#)[:\s]*([^\s\n]+)",
            r"(?:mr\s*#|patient\s*#)[:\s]*([^\s\n]+)"
        ]
        
        # ICD Code patterns
        icd_patterns = [
            r"(?:icd[:\s]*(?:10|9)?[:\s]*)?([A-Z][0-9]{2}\.?[0-9A-Z]*)",  # ICD-10 format
            r"(?:diagnosis\s*code|dx\s*code)[:\s]*([A-Z][0-9]{2}\.?[0-9A-Z]*)",
            r"(?:primary\s*diagnosis|secondary\s*diagnosis)[:\s]*([A-Z][0-9]{2}\.?[0-9A-Z]*)"
        ]
        
        # Apply patterns
        pattern_groups = {
            'patient_name': name_patterns,
            'dob': dob_patterns,
            'start_of_care': soc_patterns,
            'episode_start': episode_start_patterns,
            'episode_end': episode_end_patterns,
            'mrn': mrn_patterns,
            'icd_codes': icd_patterns
        }
        
        for field, pattern_list in pattern_groups.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                if matches:
                    if field == 'icd_codes':
                        # Collect all ICD codes
                        patterns[field] = ', '.join(matches)
                    else:
                        patterns[field] = matches[0].strip()
                    break
        
        return patterns
    
    def map_to_target_fields(self, extracted: Dict[str, str]) -> Dict[str, str]:
        """Map extracted fields to target output fields"""
        mapped = {
            'patient_name': '',
            'dob': '',
            'start_of_care': '',
            'episode_start': '',
            'episode_end': '',
            'mrn': '',
            'icd_codes': ''
        }
        
        # Field mapping dictionary
        field_mappings = {
            'patient_name': ['patient_name', 'name', 'patient', 'client_name'],
            'dob': ['dob', 'date_of_birth', 'birth_date', 'born'],
            'start_of_care': ['start_of_care', 'soc', 'care_start', 'admission_date'],
            'episode_start': ['episode_start', 'cert_period_from', 'episode_from', 'from_date'],
            'episode_end': ['episode_end', 'cert_period_to', 'episode_to', 'to_date'],
            'mrn': ['mrn', 'medical_record', 'patient_id', 'record_number', 'chart_#'],
            'icd_codes': ['icd_codes', 'diagnosis_code', 'dx_code', 'primary_diagnosis']
        }
        
        # Map extracted fields to target fields
        for target_field, source_fields in field_mappings.items():
            for source_field in source_fields:
                if source_field in extracted and extracted[source_field]:
                    mapped[target_field] = extracted[source_field]
                    break
        
        return mapped
    
    def process_csv(self, input_file: str, output_file: str):
        """Process CSV file and extract medical fields"""
        if not AUTH_TOKEN:
            raise RuntimeError("AUTH_TOKEN not set in environment")
        
        with open(input_file, newline="", encoding="utf-8") as src, \
             open(output_file, "w", newline="", encoding="utf-8") as dest:
            
            reader = csv.DictReader(src)
            fieldnames = list(reader.fieldnames) + [
                "patient_name", "dob", "start_of_care", 
                "episode_start", "episode_end", "mrn", "icd_codes"
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
                    pdf_bytes = self.fetch_pdf_bytes(doc_id, AUTH_TOKEN)
                    medical_fields = self.analyze_document(pdf_bytes)
                    
                    # Add extracted fields to row
                    for field, value in medical_fields.items():
                        if value:
                            row[field] = value
                    
                    writer.writerow(row)
                    print("✔️")
                    
                except Exception as e:
                    print(f"Failed: {e}")
                    writer.writerow(row)
                    continue
                
                time.sleep(0.2)  # Rate limiting
        
        print(f"\n✅ Medical data extraction completed!")
        print(f"📄 Results saved to: {output_file}")

def main():
    """Main execution function"""
    print("🏥 Enhanced Medical Document Extractor")
    print("=" * 50)
    print("📋 Document Types: Patient Orders, POC, Face-to-face, Lab Reports, 485s")
    print("🎯 Target Fields: Name, DOB, Start of Care, Episode Dates, ICD Codes")
    print("=" * 50)
    
    extractor = MedicalDocumentExtractor()
    extractor.process_csv(INPUT_CSV, OUTPUT_CSV)

if __name__ == "__main__":
    main() 