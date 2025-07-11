# Patient Creation Bot

A specialized bot for creating patients in Document Alliance (DA) when they don't exist in the system. This bot is designed to work in conjunction with Spencer's order creation workflow.

## Overview

When Spencer's order upload fails because a patient doesn't exist (patient MR number not mapped to any patient ID), this bot will:

1. **Fetch 485 certificates** from DA for the specified patients
2. **Extract patient information** using DA APIs and document details
3. **Create comprehensive patient payloads** from 485 certificate data
4. **Upload patients to DA** using the patient creation API
5. **Generate detailed reports** of creation results

## Features

- ✅ Selenium-based web scraping for 485 certificate retrieval
- ✅ DA API integration for document and patient data extraction
- ✅ Comprehensive patient payload creation
- ✅ Error handling and retry logic
- ✅ Excel report generation
- ✅ Configurable date ranges and patient filtering
- ✅ Dry-run mode for testing
- ✅ Command-line interface

## Prerequisites

- Python 3.8+
- Chrome browser
- ChromeDriver (automatically managed)
- Valid DA credentials and API access

## Installation

1. **Clone or copy the PatientCreationBot directory**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials** in `config.json`:
   ```json
   {
     "configuration": {
       "DA_URL": "https://backoffice.doctoralliance.com",
       "DA_USERNAME": "your_da_username",
       "DA_PASSWORD": "your_da_password",
       "DA_API_TOKEN_USERNAME": "your_api_username", 
       "DA_API_TOKEN_PASSWORD": "your_api_password",
       "DA_API_TOKEN_CLINICIAN_ID": "your_clinician_id",
       "DA_API_TOKEN_CARETAKER_ID": "your_caretaker_id"
     }
   }
   ```

## Usage

### Basic Usage

Process specific patients by name:
```bash
python main.py --patients "John Doe,Jane Smith" --helper-id "HELPER123"
```

Process patients from a file:
```bash
python main.py --patients-file failed_patients.txt --helper-id "HELPER123"
```

### Advanced Usage

With custom date range:
```bash
python main.py --patients "John Doe,Jane Smith" --helper-id "HELPER123" \
  --start-date "01/01/2024" --end-date "01/31/2024"
```

Dry run (testing mode):
```bash
python main.py --patients "John Doe,Jane Smith" --helper-id "HELPER123" --dry-run
```

Verbose output:
```bash
python main.py --patients "John Doe,Jane Smith" --helper-id "HELPER123" --verbose
```

### Input File Format

Create a text file with patient names (one per line):
```
John Doe
Jane Smith
Robert Johnson
Mary Williams
```

## Workflow

1. **Initialize** - Load configuration and validate credentials
2. **Setup Browser** - Initialize Chrome driver with proper settings
3. **Login to DA** - Authenticate with Document Alliance platform
4. **Impersonate Helper** - Switch to specified helper account
5. **Search Documents** - Find all documents in specified date range
6. **Filter 485 Certificates** - Identify certificates for target patients
7. **Extract Data** - Use DA APIs to get detailed patient information
8. **Create Payloads** - Build comprehensive patient creation payloads
9. **Upload Patients** - Create patients using DA patient API
10. **Generate Report** - Create Excel report with results

## Configuration

### Required Settings

- `DA_USERNAME` / `DA_PASSWORD` - DA platform login credentials
- `DA_API_TOKEN_USERNAME` / `DA_API_TOKEN_PASSWORD` - DA API credentials
- `DA_API_TOKEN_CLINICIAN_ID` - Clinician ID for patient creation
- `DA_API_TOKEN_CARETAKER_ID` - Caretaker ID for patient creation

### Optional Settings

- `DOWNLOAD_PATH` - Directory for downloaded files
- `REPORTS_PATH` - Directory for generated reports
- `LOGS_PATH` - Directory for log files
- `CHROME_DRIVER_PATH` - Custom ChromeDriver path

## Output

### Console Output
Real-time progress updates with patient processing status.

### Excel Report
Detailed Excel report with:
- Patient names and document IDs
- Creation status (Success/Failed)
- Error messages
- Extracted patient data (name, DOB, MRN, etc.)
- Care dates and physician information

### File Downloads
- 485 certificate PDFs downloaded to `reports/485_certificates/`
- Excel reports saved to `reports/`

## Error Handling

The bot includes comprehensive error handling for:
- Invalid credentials
- Network connectivity issues
- Missing patients or documents
- API failures
- Browser automation errors

Failed patients are logged with detailed error messages for manual review.

## Integration with Spencer's Workflow

This bot is designed to be called when Spencer's order creation fails due to missing patients:

1. Spencer's bot attempts to upload orders
2. If patient doesn't exist, Spencer's bot collects failed patient names
3. This bot is called with the list of failed patients
4. Bot creates missing patients
5. Spencer's bot can retry order upload for created patients

## Troubleshooting

### Common Issues

1. **Chrome driver issues**
   - Install latest Chrome browser
   - Check ChromeDriver compatibility
   - Verify Chrome executable permissions

2. **Login failures**
   - Verify DA credentials in config.json
   - Check network connectivity
   - Ensure account has proper permissions

3. **API authentication failures**
   - Verify DA API credentials
   - Check API endpoint URLs
   - Ensure API access is enabled for account

4. **No 485 certificates found**
   - Expand date range
   - Verify patient names are correct
   - Check if documents exist in DA

### Debug Mode

Use `--verbose` flag for detailed debugging information:
```bash
python main.py --patients "John Doe" --helper-id "HELPER123" --verbose
```

## Dependencies

- **selenium** - Web browser automation
- **webdriver-manager** - ChromeDriver management
- **requests** - HTTP API calls
- **openpyxl** - Excel file generation

## Architecture

```
PatientCreationBot/
├── main.py              # Entry point with CLI
├── patient_creator.py   # Main workflow logic
├── selenium_bot.py      # Web scraping automation
├── da_api_client.py     # DA API integration
├── config_reader.py     # Configuration management
├── config.json          # Configuration file
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Development

### Adding New Features

1. **Document Type Support** - Extend `_is_485_certificate()` to recognize additional document types
2. **Data Extraction** - Enhance `_extract_patient_info_from_doc()` for more comprehensive data extraction
3. **Validation** - Add data validation rules in `_create_patient_payload()`
4. **Reporting** - Extend `_generate_patient_creation_report()` for additional metrics

### Testing

Use dry-run mode for safe testing:
```bash
python main.py --patients "Test Patient" --helper-id "TEST123" --dry-run --verbose
```

## Support

For issues or questions, review:
1. Console output and error messages
2. Generated Excel reports
3. This README documentation
4. Original AthenaOrders codebase for reference patterns 