# Sannidhay & Pranav's Independent Bot System

A complete automation system for medical document processing, independent of Athena orders.

## 🎯 Overview

This system consists of 4 main bots that work together to automate medical document processing:

1. **Spencer's Order Extraction Bot** - Extracts orders from Athena Inbox
2. **AI Field Extraction Bot** - Uses Azure Document Intelligence to extract medical fields
3. **Patient Creation Bot** - Creates patients in Physician Group systems
4. **Signed Document Bot** - Extracts signed documents

## 📁 Directory Structure

```
SannidhayPranavBots/
├── main_orchestrator.py          # Main entry point
├── config.py                     # Configuration settings
├── requirements.txt              # Dependencies
├── README.md                     # This file
├── Final_All_Inboxed.py         # Spencer's Order Extraction Bot
├── ai_extract_fields.py         # AI Field Extraction Bot
├── Final_patient_bot.py         # Patient Creation Bot
├── Final_signed_bot.py          # Signed Document Bot
├── Inbox/                       # Input files
├── Reports/                     # Output CSV files
├── Downloads/                   # Downloaded files
│   └── PDFs/                    # PDF storage
└── Logs/                        # Log files
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Settings
Edit `config.py` and update these critical values:

```python
# Physician Group API Configuration
PG_CONFIG = {
    "api_key": "your_actual_pg_api_key",    # UPDATE THIS
    "company_pg_id": "your_pg_id",          # UPDATE THIS
}

# Azure Document Intelligence Configuration
AZURE_CONFIG = {
    "endpoint": "https://your-resource.cognitiveservices.azure.com/",  # UPDATE THIS
    "key": "your_azure_key",                # UPDATE THIS
}
```

### 3. Run the System

#### Complete Workflow
```bash
python main_orchestrator.py
```

#### Individual Steps
```bash
# Step 1: Extract Spencer's Orders
python main_orchestrator.py --step 1

# Step 2: AI Field Extraction
python main_orchestrator.py --step 2

# Step 3: Patient Creation
python main_orchestrator.py --step 3

# Step 4: Signed Document Extraction
python main_orchestrator.py --step 4
```

## 🔧 Configuration

### Changing Physician Group (PG)

To configure for a different PG, update `config.py`:

```python
PG_CONFIG = {
    "api_key": "new_pg_api_key",
    "company_pg_id": "new_pg_id", 
    "company_id": "new_company_id"  # if needed
}
```

### Azure Setup

1. Create an Azure Document Intelligence resource
2. Get your endpoint and key from Azure portal
3. Update `AZURE_CONFIG` in `config.py`

## 📊 Workflow

```
Spencer's Orders → AI Extraction → Patient Creation → Signed Documents
      ↓               ↓               ↓               ↓
   Reports/         Reports/        Reports/        Reports/
Spencer_Orders_*  AI_Extracted_*  Patients_*      Signed_Orders_*
```

## 🤖 Individual Bot Details

### 1. Spencer's Order Extraction Bot (`Final_All_Inboxed.py`)
- **Purpose**: Extracts orders from Athena Inbox using Selenium
- **Input**: Athena web interface
- **Output**: `Reports/Spencer_Orders_YYYY-MM-DD_HH-MM-SS.csv`
- **Features**: Date filtering (07/01/2025+), pagination, duplicate detection

### 2. AI Field Extraction Bot (`ai_extract_fields.py`)
- **Purpose**: Extracts medical fields from PDFs using Azure Document Intelligence
- **Input**: Spencer's orders CSV
- **Output**: `Reports/AI_Extracted_YYYY-MM-DD_HH-MM-SS.csv`
- **Fields**: MRN, DOB, start_of_care, episode dates

### 3. Patient Creation Bot (`Final_patient_bot.py`)
- **Purpose**: Creates patients in PG system from failed orders
- **Input**: `Inbox/failed_orders.csv`
- **Output**: `Reports/Patients_Created_YYYY-MM-DD_HH-MM-SS.csv`
- **Features**: Duplicate handling, API integration, comprehensive logging

### 4. Signed Document Bot (`Final_signed_bot.py`)
- **Purpose**: Extracts signed documents using Selenium
- **Input**: Web interface
- **Output**: `Reports/Signed_Orders_YYYY-MM-DD_HH-MM-SS.csv`
- **Features**: Date filtering, automated navigation

## 📝 Logs

All bots generate detailed logs in the `Logs/` directory:
- `spencer_orders.log` - Spencer's bot activities
- `patient_creation.log` - Patient creation activities
- `signed_orders.log` - Signed document activities
- `ai_extraction.log` - AI extraction activities

## 🔒 Security

- All credentials are stored in `config.py`
- Use environment variables for production
- API keys are masked in logs
- Rate limiting prevents API abuse

## 🐛 Troubleshooting

### Common Issues

1. **"PG API key not configured"**
   - Update `PG_CONFIG["api_key"]` in `config.py`

2. **"Azure endpoint not configured"**
   - Update `AZURE_CONFIG` in `config.py`

3. **"No Spencer orders file found"**
   - Run step 1 first: `python main_orchestrator.py --step 1`

4. **Selenium WebDriver issues**
   - Ensure Chrome is installed
   - Update Chrome WebDriver if needed

### Getting Help

1. Check the logs in `Logs/` directory
2. Validate configuration: `python -c "from config import validate_config; validate_config()"`
3. Run individual steps to isolate issues

## 🔄 Updates

To update for a new PG:
1. Update `config.py` with new PG details
2. Test with `python main_orchestrator.py --step 3`
3. Verify patient creation works correctly

## 📞 Support

For issues or questions about this bot system, check:
- Log files in `Logs/` directory
- Configuration in `config.py`
- Individual bot scripts for specific functionality 