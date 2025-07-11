#!/usr/bin/env python3
"""
Download sample medical documents for Azure Document Intelligence training
"""
import os
import csv
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
DA_GETFILE_URL = "https://api.doctoralliance.com/document/getfile?docId.id={doc_id}"
SAMPLES_DIR = "azure_training_samples"

def fetch_pdf_and_save(doc_id: str, token: str) -> bool:
    """Fetch PDF from DA API and save to samples directory"""
    try:
        url = DA_GETFILE_URL.format(doc_id=doc_id)
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"Fetching document {doc_id}...")
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code != 200:
            print(f"Failed to fetch {doc_id}: {response.status_code}")
            return False
            
        payload = response.json().get("value", {})
        buffer_b64 = payload.get("documentBuffer")
        
        if not buffer_b64:
            print(f"No document buffer for {doc_id}")
            return False
            
        # Decode and save PDF
        pdf_bytes = base64.b64decode(buffer_b64)
        file_path = os.path.join(SAMPLES_DIR, f"{doc_id}.pdf")
        
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
            
        print(f"✓ Saved {doc_id}.pdf ({len(pdf_bytes)} bytes)")
        return True
        
    except Exception as e:
        print(f"✗ Error fetching {doc_id}: {e}")
        return False

def main():
    # Read some document IDs from recent CSV
    csv_file = "AthenaOrders/Inbox/Inbox_Extracted_Data_2025-07-11_02-47-20.csv"
    
    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        print("Please update the csv_file path in the script")
        return
    
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    
    doc_ids = []
    physician_groups = set()  # Track different physician groups
    
    with open(csv_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if len(doc_ids) >= 15:  # Get 15 candidates to ensure we get 10 successful downloads
                break
            
            doc_id = row.get("ID") or row.get("DocID") or row.get("DocumentID")
            physician_group = row.get("PhysicianGroup") or row.get("Provider") or "Unknown"
            
            if doc_id:
                doc_ids.append(doc_id)
                physician_groups.add(physician_group)
                print(f"Found: {doc_id} from {physician_group}")
    
    print(f"\n📋 Found {len(doc_ids)} document IDs from {len(physician_groups)} different groups")
    print(f"Physician Groups: {', '.join(list(physician_groups)[:5])}...")
    
    if not AUTH_TOKEN:
        print("ERROR: AUTH_TOKEN not found in .env file")
        return
    
    successful = 0
    target_samples = 10
    
    for doc_id in doc_ids:
        if successful >= target_samples:
            break
            
        if fetch_pdf_and_save(doc_id, AUTH_TOKEN):
            successful += 1
            print(f"Progress: {successful}/{target_samples} samples collected")
    
    print(f"\n✅ Successfully downloaded {successful}/{target_samples} sample documents")
    print(f"📁 Samples saved in: {SAMPLES_DIR}/")
    
    if successful >= 8:  # Good enough for training
        print("\n🎯 Great! You have enough diverse samples for training")
        print("📊 Benefits of diverse samples:")
        print("   - Different physician group formats")
        print("   - Various document layouts")
        print("   - Regional variations in USA")
        print("   - Better model generalization")
    else:
        print(f"\n⚠️  Only got {successful} samples. Consider:")
        print("   - Running script again with different CSV")
        print("   - Checking DA API for more available documents")
    
    print("\n🚀 Next steps:")
    print("1. Create new Azure Document Intelligence resource")
    print("2. Upload these diverse samples to Azure Blob Storage")
    print("3. Label documents carefully (different formats may have different layouts)")
    print("4. Train custom model that handles multiple physician group formats")
    print("5. Update .env with new endpoint and model ID")

if __name__ == "__main__":
    main() 