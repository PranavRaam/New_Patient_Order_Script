# 🚀 Azure Document Intelligence Setup Guide
## Complete Guide to Create Custom Medical Document Model

### 📋 **Phase 1: Create New Azure Document Intelligence Resource**

#### **Step 1: Azure Portal Setup**
1. **Go to**: https://portal.azure.com
2. **Sign in** with your Azure account
3. **Click**: "Create a resource" (+ symbol)
4. **Search**: "Document Intelligence"
5. **Select**: "Document Intelligence" by Microsoft
6. **Click**: "Create"

#### **Step 2: Configure Resource**
```
Subscription: [Your Azure Subscription]
Resource Group: medical-docs-rg (create new)
Region: East US (or closest region)
Name: medical-document-processor-v2
Pricing Tier: Free F0 (1000 pages/month) or Standard S0
```

#### **Step 3: Get New Credentials**
After deployment:
1. **Go to**: Your new resource
2. **Click**: "Keys and Endpoint" (left sidebar)
3. **Copy and Save**:
   - **Endpoint**: `https://medical-document-processor-v2.cognitiveservices.azure.com/`
   - **Key 1**: `[32-character key]`

---

### 🛠️ **Phase 2: Create Azure Storage Account** 

#### **Step 1: Create Storage Account**
1. **In Azure Portal**: Create a resource → Storage Account
2. **Configure**:
   ```
   Name: medicaldocsstorage
   Performance: Standard
   Redundancy: LRS (cheapest)
   ```

#### **Step 2: Create Container**
1. **Go to**: Storage Account → Containers
2. **Click**: "+ Container"
3. **Name**: `training-documents`
4. **Public access level**: Container

#### **Step 3: Upload Sample Documents**
1. **Click**: Your container
2. **Upload**: All 10 PDFs from `azure_training_samples/` folder
   - `9390352.pdf` (86KB) - Large format document
   - `9391210.pdf` (7KB) - Compact format
   - `9391217.pdf` (94KB) - Detailed format
   - `9391219.pdf` (15KB) - Medium format
   - `9391258.pdf` (23KB) - Standard format
   - `9391276.pdf` (47KB) - Mid-size format
   - `9391277.pdf` (85KB) - Extended format
   - `9391291.pdf` (7KB) - Minimal format
   - `9391297.pdf` (80KB) - Full format
   - `9391526.pdf` (127KB) - Comprehensive format

---

### 🎯 **Phase 3: Train Custom Model**

#### **Step 1: Document Intelligence Studio**
1. **Go to**: https://documentintelligence.ai.azure.com/studio
2. **Sign in** with same Azure account
3. **Select**: Your new Document Intelligence resource

#### **Step 2: Create Custom Model**
1. **Click**: "Custom models" → "Custom extraction model"
2. **Project Name**: `medical-document-extractor-usa`
3. **Connect to Azure Blob Storage**:
   - **Storage Account**: Select your storage account
   - **Container**: `training-documents`
   - **Folder**: (leave empty)

#### **Step 3: Label Your Documents** ⚠️ **CRITICAL FOR SUCCESS**

**🎯 Strategy for Diverse USA Physician Groups:**

For **each PDF** (all 10 documents), label these fields consistently:

**Required Medical Fields:**
- `mrn` (Medical Record Number)
- `dob` (Date of Birth)
- `patient_name` (Patient Full Name)
- `start_of_care` (Start of Care Date)
- `episode_start` (Episode Start Date)
- `episode_end` (Episode End Date)

**🔍 Labeling Tips for Diverse Formats:**

1. **Look for Field Variations** across different physician groups:
   ```
   MRN: "MRN", "Medical Record #", "Patient ID", "Record Number", "Chart #"
   DOB: "DOB", "Date of Birth", "Birth Date", "Born", "D.O.B."
   Name: "Patient Name", "Patient", "Name", "Client Name"
   Dates: "SOC", "Start of Care", "Episode From", "Cert Period", "Care Start"
   ```

2. **Handle Different Layouts**:
   - Some docs: Fields in left column
   - Others: Fields scattered throughout
   - Tables: Data in table cells
   - Headers: Information in document headers

3. **Label Even If Format Differs**:
   - Small docs (7KB): May have minimal info
   - Large docs (127KB): May have extensive details
   - Label whatever fields you can find

4. **Consistency is Key**:
   - Always use exact same field names
   - `mrn` not `MRN` or `medical_record_number`
   - `dob` not `date_of_birth` or `DOB`

#### **Step 4: Train Model**
1. **Click**: "Train" button
2. **Model Name**: `medical-extractor-usa-v1`
3. **Wait**: 10-20 minutes for training (longer with 10 docs)
4. **Copy**: Model ID when training completes

---

### ⚙️ **Phase 4: Update Your Script**

#### **Step 1: Update .env File**
```env
# New Azure Credentials
AZURE_FORM_ENDPOINT=https://medical-document-processor-v2.cognitiveservices.azure.com/
AZURE_FORM_KEY=[your-new-32-character-key]
AZURE_FORM_MODEL=[your-custom-model-id]

# Keep existing DA credentials
AUTH_TOKEN=NWz6GsEawCOc2ZRAXcq3B2Mrn9rQck5rJWpTu_73SgYVIx5Q08...
DA_USERNAME=sannidhay
DA_PASSWORD=DA@2025
DA_GETFILE_URL=https://api.doctoralliance.com/document/getfile?docId.id={doc_id}
```

#### **Step 2: Enhanced Field Mapping**
Your script will now handle multiple physician group formats!

---

### 🧪 **Phase 5: Test Your Custom Model**

#### **Step 1: Test Script**
```bash
python AthenaOrders/ai_extract_fields.py AthenaOrders/Inbox/Inbox_Extracted_Data_2025-07-11_02-47-20.csv
```

#### **Step 2: Expected Improved Output**
```
Processing 9391526 … [DA] GET https://api.doctoralliance.com/...
[DA] status 200
[DA] retrieved 130494 bytes
[Azure] Analyzing (bytes=130494)
[Azure] analysis completed
Extracted: {'mrn': '12345', 'dob': '01/15/1980', 'patient_name': 'John Doe', 'start_of_care': '01/01/2025', 'episode_start': '01/01/2025', 'episode_end': '03/31/2025'}
✔️
```

---

### 📊 **Expected Benefits of 10 Diverse Samples**

✅ **Multi-Format Recognition**: Handles various physician group layouts  
✅ **Regional Adaptability**: Works across different USA healthcare systems  
✅ **Size Flexibility**: Processes both compact (7KB) and comprehensive (127KB) docs  
✅ **Higher Accuracy**: Better field detection across format variations  
✅ **Robust Model**: Less likely to fail on new document formats  

---

### 💡 **Pro Tips for USA Physician Groups**

1. **Document Size Variation**: Your samples range from 7KB to 127KB - perfect diversity
2. **Label Thoroughly**: Even if a field appears in unusual location, label it
3. **Field Variations**: USA physicians use different terminology - capture all variations
4. **Regional Differences**: Different states may have different form requirements
5. **Iterative Improvement**: Test model → Add more samples → Retrain as needed

---

### 🆘 **Troubleshooting Multi-Format Documents**

**Low Accuracy on New Docs:**
- Add samples from that specific physician group
- Retrain model with additional diversity

**Missing Fields:**
- Check if field names vary (MRN vs Medical Record)
- Add more labeling for that field type

**Format-Specific Issues:**
- Label more examples of that document layout
- Ensure consistent field naming across all formats

---

**Ready to create your robust multi-format model?** Follow Phase 1 with your 10 diverse samples! 🚀 