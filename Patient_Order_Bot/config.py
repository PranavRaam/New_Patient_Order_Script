"""
Configuration file for Sannidhay & Pranav's Independent Bot System
================================================================

This file contains all the configuration settings for the bot system.
Update these values according to your specific setup.
"""

# Doctor Alliance API Configuration
DA_CONFIG = {
    "base_url": "https://backoffice.doctoralliance.com",
    "username": "sannidhay",
    "password": "DA@2025",
    "helper_id": "dallianceph721",
    "token_url": "https://backoffice.doctoralliance.com/token",
    "document_url": "https://backoffice.doctoralliance.com/api/documents/{doc_id}",
    "patient_url": "https://backoffice.doctoralliance.com/api/patients/{patient_id}",
    "getfile_url": "https://api.doctoralliance.com/document/getfile?docId.id={doc_id}"
}

# Physician Group API Configuration
PG_CONFIG = {
    "base_url": "https://live.doctoralliance.com/api",
    "api_key": "your_pg_api_key",  # UPDATE THIS
    "company_id": "",  # UPDATE THIS if needed
    "company_pg_id": "",  # UPDATE THIS
    "create_patient_endpoint": "/patients"
}

# Azure Document Intelligence Configuration
AZURE_CONFIG = {
    "endpoint": "",  # UPDATE THIS - e.g. https://<resource>.cognitiveservices.azure.com/
    "key": "",  # UPDATE THIS
    "model": "prebuilt-document"  # or custom model id
}

# File Paths and Directories
PATHS = {
    "inbox_dir": "Inbox",
    "reports_dir": "Reports", 
    "downloads_dir": "Downloads",
    "pdfs_dir": "Downloads/PDFs",
    "logs_dir": "Logs"
}

# Bot Settings
BOT_SETTINGS = {
    "date_filter": "07/01/2025",  # Orders from this date onwards
    "rate_limit_delay": 0.3,  # Seconds between API calls
    "selenium_timeout": 10,  # Selenium wait timeout
    "api_timeout": 30  # API request timeout
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "spencer_log": "Logs/spencer_orders.log",
    "patient_log": "Logs/patient_creation.log",
    "signed_log": "Logs/signed_orders.log",
    "ai_log": "Logs/ai_extraction.log"
}

# CSV File Templates
CSV_TEMPLATES = {
    "spencer_orders": "Reports/Spencer_Orders_{timestamp}.csv",
    "ai_extracted": "Reports/AI_Extracted_{timestamp}.csv", 
    "patients_created": "Reports/Patients_Created_{timestamp}.csv",
    "signed_orders": "Reports/Signed_Orders_{timestamp}.csv",
    "failed_orders": "Inbox/failed_orders.csv"
}

def get_pg_config():
    """Get PG configuration with validation"""
    config = PG_CONFIG.copy()
    config["create_patient_url"] = f"{config['base_url']}{config['create_patient_endpoint']}"
    return config

def get_azure_config():
    """Get Azure configuration with validation"""
    config = AZURE_CONFIG.copy()
    if not config["endpoint"] or not config["key"]:
        raise ValueError("Azure endpoint and key must be configured")
    return config

def validate_config():
    """Validate all configuration settings"""
    errors = []
    
    # Check PG configuration
    if PG_CONFIG["api_key"] == "your_pg_api_key":
        errors.append("PG API key not configured")
    
    # Check Azure configuration  
    if not AZURE_CONFIG["endpoint"]:
        errors.append("Azure endpoint not configured")
    if not AZURE_CONFIG["key"]:
        errors.append("Azure key not configured")
    
    if errors:
        print("⚠️  Configuration Issues Found:")
        for error in errors:
            print(f"   - {error}")
        print("\n📝 Please update config.py with your actual values")
        return False
    
    return True 