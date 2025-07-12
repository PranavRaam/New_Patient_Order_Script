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
        print(f"\n{'='*60}")
        print(f"📥 FETCHING PDF FROM DA API")
        print(f"{'='*60}")
        
        url = DA_GETFILE_URL.format(doc_id=doc_id)
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"🆔 Document ID: {doc_id}")
        print(f"🌐 API URL: {url}")
        print(f"🔑 Auth token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
        
        print(f"⏳ Making first API request...")
        response = requests.get(url, headers=headers, timeout=60)
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"📄 Response: {response.text[:200]}...")
            raise RuntimeError(f"API request failed: {response.status_code}")
        
        payload = response.json().get("value", {})
        buffer_b64 = payload.get("documentBuffer")
        
        # Retry with JSON body if no buffer
        if not buffer_b64:
            print(f"⚠️  No documentBuffer in response, trying with JSON body...")
            request_body = {
                "onlyUnfiled": True,
                "careProviderId": {"id": 0, "externalId": ""},
                "dateFrom": None, "dateTo": None,
                "page": 1, "recordsPerPage": 10
            }
            print(f"📤 Sending JSON body: {request_body}")
            response = requests.get(url, headers=headers, json=request_body, timeout=60)
            print(f"📊 Second attempt status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Second API request failed with status {response.status_code}")
                raise RuntimeError(f"Second API request failed: {response.status_code}")
                
            payload = response.json().get("value", {})
            buffer_b64 = payload.get("documentBuffer")
        
        if not buffer_b64:
            print(f"❌ No documentBuffer found in either response")
            print(f"📄 Response payload keys: {list(payload.keys())}")
            raise RuntimeError("documentBuffer missing in response")
            
        pdf_bytes = base64.b64decode(buffer_b64)
        print(f"✅ PDF retrieved successfully!")
        print(f"📄 PDF size: {len(pdf_bytes):,} bytes")
        print(f"🔍 Base64 buffer length: {len(buffer_b64):,} characters")
        
        return pdf_bytes
    
    def analyze_document(self, pdf_bytes: bytes) -> Dict[str, str]:
        """Analyze document using Azure Document Intelligence"""
        print(f"\n{'='*60}")
        print(f"🔍 ANALYZING DOCUMENT WITH AZURE AI")
        print(f"{'='*60}")
        print(f"📄 Document size: {len(pdf_bytes):,} bytes")
        print(f"🤖 Using model: {AZURE_MODEL}")
        print(f"🌐 Azure endpoint: {AZURE_ENDPOINT}")
        
        try:
            print(f"⏳ Starting analysis with custom model '{AZURE_MODEL}'...")
            poller = self.client.begin_analyze_document(
                AZURE_MODEL,
                body=pdf_bytes,
                content_type="application/pdf"
            )
            result = poller.result()
            print(f"✅ Analysis completed successfully with custom model!")
        except Exception as e:
            if "ModelNotFound" in str(e):
                print(f"❌ Custom model '{AZURE_MODEL}' not found!")
                print(f"🔄 Falling back to prebuilt-layout model...")
                poller = self.client.begin_analyze_document(
                    "prebuilt-layout",
                    body=pdf_bytes,
                    content_type="application/pdf"
                )
                result = poller.result()
                print(f"✅ Analysis completed with prebuilt-layout fallback")
            else:
                print(f"❌ Analysis failed with error: {e}")
                raise e
        
        return self.extract_medical_fields(result)
    
    def extract_medical_fields(self, result) -> Dict[str, str]:
        """Extract specific medical fields from Azure result"""
        print(f"\n{'='*60}")
        print(f"🎯 EXTRACTING MEDICAL FIELDS")
        print(f"{'='*60}")
        
        extracted = {}
        
        # PRIORITY 1: Extract from custom model document fields (most accurate)
        if hasattr(result, "documents") and result.documents:
            print(f"🏥 CUSTOM MODEL EXTRACTION")
            print(f"   📋 Found {len(result.documents)} document(s) from custom model")
            
            for doc_idx, doc in enumerate(result.documents):
                if hasattr(doc, "fields") and doc.fields:
                    print(f"   📝 Document {doc_idx + 1}: Found {len(doc.fields)} field(s)")
                    
                    for field_name, field_value in doc.fields.items():
                        if field_value:
                            # Try different ways to extract the value
                            value = None
                            if hasattr(field_value, 'content') and field_value.content:
                                value = field_value.content.strip()
                            elif hasattr(field_value, 'value') and field_value.value:
                                value = str(field_value.value).strip()
                            elif hasattr(field_value, 'value_string') and field_value.value_string:
                                value = field_value.value_string.strip()
                            
                            if value:
                                extracted[field_name] = value
                                print(f"   ✅ {field_name}: '{value}'")
                            else:
                                print(f"   ❌ {field_name}: No value found")
                        else:
                            print(f"   ❌ {field_name}: Field is empty")
                else:
                    print(f"   ❌ Document {doc_idx + 1}: No fields found")
        else:
            print(f"❌ No custom model documents found")
        
        # PRIORITY 2: Extract from key-value pairs (only if custom model didn't find fields)
        if not extracted and hasattr(result, "key_value_pairs") and result.key_value_pairs:
            print(f"\n🔍 FALLBACK: KEY-VALUE EXTRACTION")
            print(f"   📋 Custom model found no fields, trying {len(result.key_value_pairs)} key-value pair(s)")
            
            for kvp in result.key_value_pairs:
                if kvp.key and kvp.value:
                    key = kvp.key.content.strip()
                    value = kvp.value.content.strip()
                    # Only extract if key looks like a medical field
                    if any(medical_term in key.lower() for medical_term in ['dob', 'mrn', 'soc', 'soe', 'eoe', 'patient', 'name']):
                        extracted[key] = value
                        print(f"   ✅ {key}: '{value}'")
                    else:
                        print(f"   ⏭️  Skipping non-medical field: '{key}'")
        
        # PRIORITY 3: Extract from regex patterns (only as last resort)
        if not extracted and hasattr(result, "content") and result.content:
            print(f"\n🔍 FALLBACK: REGEX PATTERN EXTRACTION")
            print(f"   📋 No structured fields found, trying regex patterns on document text")
            pattern_matches = self.extract_with_patterns(result.content)
            extracted.update(pattern_matches)
            for key, value in pattern_matches.items():
                if value:
                    print(f"   ✅ {key}: '{value}'")
        
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"   🎯 Total fields extracted: {len([v for v in extracted.values() if v])}")
        print(f"   📝 Field names: {list(extracted.keys()) if extracted else 'None'}")
        
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
        print(f"\n{'='*60}")
        print(f"🗺️  MAPPING FIELDS TO OUTPUT COLUMNS")
        print(f"{'='*60}")
        
        mapped = {
            'patient_name': '',
            'dob': '',
            'start_of_care': '',
            'episode_start': '',
            'episode_end': '',
            'mrn': '',
            'icd_codes': ''
        }
        
        # Field mapping dictionary - prioritize custom model fields first
        field_mappings = {
            'patient_name': ['patient_name', 'name', 'patient', 'client_name'],
            'dob': ['DOB', 'dob', 'date_of_birth', 'birth_date', 'born'],
            'start_of_care': ['SOC', 'start_of_care', 'soc', 'care_start', 'admission_date'],
            'episode_start': ['SOE', 'episode_start', 'soe', 'cert_period_from', 'episode_from', 'from_date'],
            'episode_end': ['EOE', 'episode_end', 'eoe', 'cert_period_to', 'episode_to', 'to_date'],
            'mrn': ['MRN', 'mrn', 'medical_record', 'patient_id', 'record_number', 'chart_#'],
            'icd_codes': ['ICD', 'icd_codes', 'diagnosis_code', 'dx_code', 'primary_diagnosis']
        }
        
        print(f"📋 Available extracted fields: {list(extracted.keys())}")
        print(f"🎯 Target output columns: {list(mapped.keys())}")
        print(f"\n🔄 Field mapping process:")
        
        # Map extracted fields to target fields
        for target_field, source_fields in field_mappings.items():
            found = False
            for source_field in source_fields:
                if source_field in extracted and extracted[source_field] and extracted[source_field].strip():
                    mapped[target_field] = extracted[source_field].strip()
                    print(f"   ✅ {target_field}: '{source_field}' → '{mapped[target_field]}'")
                    found = True
                    break
            if not found:
                print(f"   ❌ {target_field}: No matching field found")
        
        print(f"\n📊 MAPPING SUMMARY:")
        filled_fields = [k for k, v in mapped.items() if v]
        empty_fields = [k for k, v in mapped.items() if not v]
        print(f"   ✅ Fields filled: {len(filled_fields)} - {filled_fields}")
        print(f"   ❌ Fields empty: {len(empty_fields)} - {empty_fields}")
        
        return mapped
    
    def process_csv(self, input_file: str, output_file: str):
        """Process CSV file and extract medical fields"""
        if not AUTH_TOKEN:
            raise RuntimeError("AUTH_TOKEN not set in environment")
        
        print(f"\n{'='*80}")
        print(f"🚀 STARTING MEDICAL DOCUMENT PROCESSING")
        print(f"{'='*80}")
        print(f"📁 Input file: {input_file}")
        print(f"📁 Output file: {output_file}")
        print(f"🤖 Azure model: {AZURE_MODEL}")
        print(f"🔑 Auth token: {AUTH_TOKEN[:20]}...{AUTH_TOKEN[-10:] if len(AUTH_TOKEN) > 30 else AUTH_TOKEN}")
        
        with open(input_file, newline="", encoding="utf-8") as src, \
             open(output_file, "w", newline="", encoding="utf-8") as dest:
            
            reader = csv.DictReader(src)
            fieldnames = list(reader.fieldnames) + [
                "patient_name", "dob", "start_of_care", 
                "episode_start", "episode_end", "mrn", "icd_codes"
            ]
            
            print(f"📋 Original CSV columns: {list(reader.fieldnames)}")
            print(f"📋 New columns being added: patient_name, dob, start_of_care, episode_start, episode_end, mrn, icd_codes")
            
            writer = csv.DictWriter(dest, fieldnames=fieldnames)
            writer.writeheader()
            
            row_count = 0
            success_count = 0
            error_count = 0
            
            for row in reader:
                row_count += 1
                doc_id = row.get("ID") or row.get("DocID") or row.get("DocumentID") or ""
                
                print(f"\n{'='*80}")
                print(f"📄 PROCESSING DOCUMENT {row_count}")
                print(f"{'='*80}")
                
                if not doc_id:
                    print(f"⚠️  No document ID found in row {row_count}")
                    print(f"📋 Available columns: {list(row.keys())}")
                    writer.writerow(row)
                    error_count += 1
                    continue
                
                try:
                    print(f"🆔 Document ID: {doc_id}")
                    print(f"👤 Patient: {row.get('Patient', 'Unknown')}")
                    print(f"🏥 Facility: {row.get('Facility', 'Unknown')}")
                    print(f"👨‍⚕️ Physician: {row.get('Physician', 'Unknown')}")
                    
                    pdf_bytes = self.fetch_pdf_bytes(doc_id, AUTH_TOKEN)
                    medical_fields = self.analyze_document(pdf_bytes)
                    
                    # Add extracted fields to row
                    fields_added = 0
                    for field, value in medical_fields.items():
                        if value:
                            row[field] = value
                            fields_added += 1
                    
                    writer.writerow(row)
                    success_count += 1
                    
                    print(f"\n✅ DOCUMENT {row_count} COMPLETED SUCCESSFULLY!")
                    print(f"   📊 Fields extracted: {fields_added}/7")
                    print(f"   📋 Extracted data: {[(k, v) for k, v in medical_fields.items() if v]}")
                    
                except Exception as e:
                    print(f"\n❌ DOCUMENT {row_count} FAILED!")
                    print(f"   🚨 Error: {str(e)}")
                    print(f"   📋 Original row data will be preserved")
                    writer.writerow(row)
                    error_count += 1
                    continue
                
                time.sleep(0.2)  # Rate limiting
        
        print(f"\n{'='*80}")
        print(f"🎉 PROCESSING COMPLETE!")
        print(f"{'='*80}")
        print(f"📊 FINAL STATISTICS:")
        print(f"   📄 Total documents processed: {row_count}")
        print(f"   ✅ Successful extractions: {success_count}")
        print(f"   ❌ Failed extractions: {error_count}")
        print(f"   📈 Success rate: {(success_count/row_count*100):.1f}%" if row_count > 0 else "   📈 Success rate: 0%")
        print(f"   📁 Results saved to: {output_file}")
        print(f"{'='*80}")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Open the output CSV file: {output_file}")
        print(f"   2. Check the new columns: patient_name, dob, start_of_care, episode_start, episode_end, mrn, icd_codes")
        print(f"   3. Verify the extracted data matches your expectations")
        print(f"   4. If accuracy is low, consider retraining your Azure model with more examples")

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