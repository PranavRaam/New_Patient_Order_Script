# 🏥 Medical Document Intelligence Training Guide
## Custom Model for PGs and HHAs Medical Documents

### 📋 **Document Types We're Training For**

✅ **Patient Orders** (Home Health Referral Forms)  
✅ **Face-to-Face Encounter Forms**  
✅ **Plan of Care (POC)** Documents  
✅ **Physician Signatures** (Signed Orders)  
✅ **Lab Reports** / Diagnostic Summaries  
✅ **485 Certificates** (Home Health Certification)  
✅ **Episode Documentation**  

### 🎯 **Target Fields for Extraction**

**Primary Fields** (Must Extract):
- `patient_name` - Patient's full name
- `dob` - Date of birth
- `start_of_care` - Start of care date
- `episode_start` - Episode start date
- `episode_end` - Episode end date
- `mrn` - Medical record number
- `icd_codes` - ICD diagnosis codes (when present)

---

## 🚀 **Phase 1: Azure Resource Setup**

### **Step 1: Create Document Intelligence Resource**
1. **Go to**: https://portal.azure.com
2. **Create Resource**: Document Intelligence
3. **Configure**:
   ```
   Name: medical-docs-intelligence
   Resource Group: medical-processing-rg
   Region: East US
   Pricing: Free F0 (1000 pages/month)
   ```

### **Step 2: Create Storage Account**
1. **Create**: Storage Account
2. **Configure**:
   ```
   Name: medicaldocstraining
   Container: medical-documents
   Access: Container level
   ```

### **Step 3: Upload Your 10 Sample Documents**
Upload all PDFs from `azure_training_samples/` to the container.

---

## 🎯 **Phase 2: Medical Document Labeling Strategy**

### **Step 1: Document Intelligence Studio**
1. **Go to**: https://documentintelligence.ai.azure.com/studio
2. **Create Project**: `medical-extractor-pgs-hhas`
3. **Connect**: Your storage account and container

### **Step 2: Field Labeling for Medical Documents**

**🔍 Look for These Field Variations:**

#### **Patient Name**
```
Common Labels:
- "Patient Name:"
- "Patient:"
- "Name:"
- "Client Name:"
- "Pt Name:"

Locations:
- Top of document header
- Patient information section
- Demographics box
```

#### **Date of Birth**
```
Common Labels:
- "DOB:"
- "Date of Birth:"
- "Birth Date:"
- "D.O.B.:"
- "Born:"

Formats:
- MM/DD/YYYY
- MM-DD-YYYY
- Month DD, YYYY
```

#### **Start of Care**
```
Common Labels:
- "Start of Care:"
- "SOC:"
- "Care Start Date:"
- "Admission Date:"
- "Service Start:"

Context:
- Usually in certification section
- May be in episode information
```

#### **Episode Dates**
```
Episode Start:
- "Episode Start:"
- "Cert Period From:"
- "Episode From:"
- "From Date:"
- "Period Start:"

Episode End:
- "Episode End:"
- "Cert Period To:"
- "Episode To:"
- "To Date:"
- "Period End:"
```

#### **Medical Record Number**
```
Common Labels:
- "MRN:"
- "Medical Record #:"
- "Patient ID:"
- "Record Number:"
- "Chart #:"
- "MR #:"
```

#### **ICD Codes**
```
Common Labels:
- "ICD-10:"
- "Diagnosis Code:"
- "Primary Diagnosis:"
- "Secondary Diagnosis:"
- "Dx Code:"

Formats:
- A12.34 (ICD-10)
- Z51.89 (ICD-10)
- Multiple codes separated by commas
```

### **Step 3: Document-Specific Labeling Tips**

#### **Patient Orders / Referral Forms**
- Patient info usually at top
- Episode dates in certification section
- ICD codes in diagnosis section

#### **Face-to-Face Encounter Forms**
- Patient demographics in header
- Encounter date may be episode start
- Clinical findings may contain ICD codes

#### **Plan of Care (POC)**
- Comprehensive patient information
- Multiple episode dates possible
- Detailed diagnosis codes

#### **485 Certificates**
- Standard CMS format
- Episode dates clearly marked
- Primary/secondary diagnoses

#### **Lab Reports**
- Patient ID prominent
- Test dates important
- Diagnosis codes in results

### **Step 4: Labeling Process**

**For Each Document (All 10):**

1. **Open Document** in Studio
2. **Label Patient Name**:
   - Click and drag to select full name
   - Type: `patient_name`
   
3. **Label DOB**:
   - Select date value only
   - Type: `dob`
   
4. **Label Start of Care**:
   - Select date value
   - Type: `start_of_care`
   
5. **Label Episode Dates**:
   - Episode start → `episode_start`
   - Episode end → `episode_end`
   
6. **Label MRN**:
   - Select ID/number only
   - Type: `mrn`
   
7. **Label ICD Codes**:
   - Select each code
   - Type: `icd_codes`
   - Label multiple if present

**⚠️ Critical Rules:**
- Use exact field names shown above
- Label consistently across all documents
- If field not present, skip it
- Label partial matches (better than nothing)

---

## 🏗️ **Phase 3: Model Training**

### **Step 1: Train Custom Model**
1. **Click**: "Train" in Studio
2. **Model Name**: `medical-extractor-v1`
3. **Wait**: 15-25 minutes (10 documents)
4. **Copy**: Model ID when complete

### **Step 2: Test Model**
1. **Test** with sample documents
2. **Verify** field extraction accuracy
3. **Retrain** if accuracy < 80%

---

## ⚙️ **Phase 4: Integration**

### **Step 1: Update .env File**
```env
# New Azure Medical Model
AZURE_FORM_ENDPOINT=https://medical-docs-intelligence.cognitiveservices.azure.com/
AZURE_FORM_KEY=[your-32-character-key]
AZURE_FORM_MODEL=[your-custom-model-id]

# Keep existing DA credentials
AUTH_TOKEN=NWz6GsEawCOc2ZRAXcq3B2Mrn9rQck5rJWpTu_73SgYVIx5Q08...
```

### **Step 2: Run Enhanced Extractor**
```bash
python enhanced_medical_extractor.py AthenaOrders/Inbox/Inbox_Extracted_Data_2025-07-11_02-47-20.csv
```

### **Step 3: Expected Output**
```
Processing 9391526 … [DA] GET https://api.doctoralliance.com/...
[DA] status 200
[DA] retrieved 130494 bytes
[Azure] Analyzing medical document (bytes=130494)
[Azure] analysis completed
✔️

Results in: csv_outputs/Medical_Extracted_2025-01-27_15-30-45.csv
```

**Output CSV will contain:**
- All original Spencer data
- `patient_name`: "John Doe"
- `dob`: "01/15/1980"
- `start_of_care`: "01/01/2025"
- `episode_start`: "01/01/2025"
- `episode_end`: "03/31/2025"
- `mrn`: "12345678"
- `icd_codes`: "Z51.89, M79.3"

---

## 📊 **Expected Benefits**

✅ **Multi-Document Support**: Handles all PG/HHA document types  
✅ **Comprehensive Extraction**: Gets all 7 critical fields  
✅ **ICD Code Detection**: Extracts diagnosis codes automatically  
✅ **High Accuracy**: Custom trained on your specific formats  
✅ **Scalable**: Processes hundreds of documents efficiently  

---

## 🔧 **Advanced Features**

### **Regex Fallback Patterns**
If Azure model misses fields, regex patterns catch:
- Various date formats
- Different MRN formats
- Multiple ICD code formats
- Name variations

### **Multi-Layer Extraction**
1. **Azure Key-Value Pairs** (primary)
2. **Azure Table Data** (secondary)
3. **Regex Patterns** (fallback)

### **Error Handling**
- Continues processing if one document fails
- Logs all extraction attempts
- Provides detailed error messages

---

## 🆘 **Troubleshooting Medical Documents**

**Low Patient Name Accuracy:**
- Check if names are in tables vs. text
- Look for "Last, First" vs. "First Last" formats
- Add more name variations in labeling

**Missing Episode Dates:**
- Verify date formats (MM/DD vs. DD/MM)
- Check for "From/To" vs. "Start/End" terminology
- Label date ranges in tables

**ICD Code Issues:**
- Ensure codes follow ICD-10 format (A12.34)
- Check for multiple codes in same field
- Look for codes in different document sections

**Document Type Specific Issues:**
- **485s**: Standard format, high accuracy expected
- **POCs**: Multiple sections, may need more labeling
- **Lab Reports**: Dates may be test dates, not episode dates
- **Face-to-Face**: May have encounter dates vs. episode dates

---

**Ready to build your medical document intelligence system?** 🚀

Follow this guide to create a robust extractor that handles all your PG and HHA document types! 