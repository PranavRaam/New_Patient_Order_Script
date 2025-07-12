#!/usr/bin/env python3
"""
CSV Cleaner for Medical Extracted Data
Cleans verbose extracted fields to contain just the values
"""
import csv
import re
import sys
from datetime import datetime

def clean_field_value(field_value: str) -> str:
    """Clean a field value by removing verbose text and extracting just the value"""
    if not field_value or field_value.strip() == "":
        return ""
    
    # Remove common prefixes and clean up the value
    value = field_value.strip()
    
    # Date of Birth cleaning
    if "date of birth" in value.lower() or "dob" in value.lower():
        # Extract date patterns
        date_patterns = [
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',  # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2})',    # MM/DD/YY or MM-DD-YY
        ]
        for pattern in date_patterns:
            match = re.search(pattern, value)
            if match:
                return match.group(1)
    
    # Start of Care cleaning
    if "start of care" in value.lower() or "soc" in value.lower():
        date_patterns = [
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, value)
            if match:
                return match.group(1)
    
    # Episode dates cleaning (From/To)
    if "from:" in value.lower() or "to:" in value.lower():
        # Extract date after "from:" or "to:"
        date_patterns = [
            r'(?:from:|to:)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:from:|to:)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                return match.group(1)
    
    # MRN cleaning
    if "mrn" in value.lower() or "medical record" in value.lower():
        # Extract everything after the label
        mrn_patterns = [
            r'(?:mrn|medical record no\.?|medical record number)[:\s]*([^\s\n,]+)',
            r'mrn:\s*([^\s\n,]+)',
            r'\(([^)]+)\)',  # Extract from parentheses
        ]
        for pattern in mrn_patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # ICD Codes cleaning - keep as is since they're already clean
    if re.match(r'^[A-Z]\d{2}', value) or '\n' in value:
        # This looks like ICD codes, clean up formatting
        codes = []
        for line in value.split('\n'):
            line = line.strip()
            if line and re.match(r'^[A-Z]\d{2}', line):
                codes.append(line)
        if codes:
            return '\n'.join(codes)
    
    # Generic cleaning - remove common prefixes
    prefixes_to_remove = [
        r'^date of birth[:\s]*',
        r'^dob[:\s]*',
        r'^start of care[:\s]*',
        r'^soc[:\s]*',
        r'^from[:\s]*',
        r'^to[:\s]*',
        r'^mrn[:\s]*',
        r'^medical record no\.?[:\s]*',
        r'^patient[:\s]*',
        r'^name[:\s]*',
    ]
    
    for prefix in prefixes_to_remove:
        value = re.sub(prefix, '', value, flags=re.IGNORECASE).strip()
    
    # Remove extra whitespace and newlines within the value
    value = re.sub(r'\s+', ' ', value).strip()
    
    return value

def clean_csv(input_file: str, output_file: str):
    """Clean the CSV file by extracting clean values from verbose fields"""
    print(f"🧹 Cleaning CSV file: {input_file}")
    print(f"📁 Output file: {output_file}")
    
    fields_to_clean = ['patient_name', 'dob', 'start_of_care', 'episode_start', 'episode_end', 'mrn', 'icd_codes']
    
    with open(input_file, 'r', newline='', encoding='utf-8') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()
        
        rows_processed = 0
        fields_cleaned = 0
        
        for row in reader:
            rows_processed += 1
            
            # Clean each field
            for field in fields_to_clean:
                if field in row and row[field]:
                    original_value = row[field]
                    cleaned_value = clean_field_value(original_value)
                    
                    if cleaned_value != original_value:
                        row[field] = cleaned_value
                        fields_cleaned += 1
                        print(f"Row {rows_processed} - {field}: '{original_value}' → '{cleaned_value}'")
            
            writer.writerow(row)
    
    print(f"\n✅ Cleaning completed!")
    print(f"📊 Statistics:")
    print(f"   - Rows processed: {rows_processed}")
    print(f"   - Fields cleaned: {fields_cleaned}")
    print(f"   - Output saved to: {output_file}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python clean_medical_csv.py <input_csv_file> [output_csv_file]")
        print("Example: python clean_medical_csv.py Medical_Extracted_2025-07-12_04-51-24.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        # Generate output filename
        base_name = input_file.replace('.csv', '')
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = f"{base_name}_cleaned_{timestamp}.csv"
    
    try:
        clean_csv(input_file, output_file)
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 