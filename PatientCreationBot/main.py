#!/usr/bin/env python3
"""
Patient Creation Bot - Main Entry Point
For creating patients in DA when they don't exist in the system

Usage:
    python main.py --patients "John Doe,Jane Smith" --helper-id "HELPER123"
    python main.py --patients-file patients.txt --helper-id "HELPER123" --start-date "01/01/2024"
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from patient_creator import PatientCreator
import config_reader

def read_patients_from_file(file_path):
    """Read patient names from a text file (one per line)"""
    try:
        with open(file_path, 'r') as f:
            patients = [line.strip() for line in f.readlines() if line.strip()]
        return patients
    except FileNotFoundError:
        raise Exception(f"Patient file not found: {file_path}")

def validate_date(date_str):
    """Validate date format (MM/DD/YYYY)"""
    try:
        datetime.strptime(date_str, '%m/%d/%Y')
        return True
    except ValueError:
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Patient Creation Bot - Create patients from 485 certificates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --patients "John Doe,Jane Smith" --helper-id "HELPER123"
  %(prog)s --patients-file patients.txt --helper-id "HELPER123" --start-date "01/01/2024" --end-date "01/31/2024"
        """
    )
    
    # Patient input options (mutually exclusive)
    patient_group = parser.add_mutually_exclusive_group(required=True)
    patient_group.add_argument(
        '--patients',
        type=str,
        help='Comma-separated list of patient names to process'
    )
    patient_group.add_argument(
        '--patients-file',
        type=str,
        help='Path to text file containing patient names (one per line)'
    )
    
    # Required arguments
    parser.add_argument(
        '--helper-id',
        type=str,
        required=True,
        help='Helper ID for DA impersonation'
    )
    
    # Optional date range
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for search (MM/DD/YYYY format, default: 30 days ago)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for search (MM/DD/YYYY format, default: today)'
    )
    
    # Configuration options
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without actually creating patients (for testing)'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate configuration
        print("Loading configuration...")
        config = config_reader.read_config()
        
        # Check if credentials are set
        da_creds = config_reader.get_da_credentials()
        da_api_creds = config_reader.get_da_api_credentials()
        
        if not da_creds['username'] or not da_creds['password']:
            print("ERROR: DA credentials not configured. Please set DA_USERNAME and DA_PASSWORD in config.json")
            sys.exit(1)
        
        # Check API credentials but don't exit if missing (for testing)
        api_creds_available = da_api_creds['username'] and da_api_creds['password']
        if not api_creds_available:
            print("WARNING: DA API credentials not configured. Patient creation via API will be skipped.")
            print("         Set DA_API_TOKEN_USERNAME and DA_API_TOKEN_PASSWORD for full functionality.")
            print("         Continuing with document search and data extraction only...")
        
        # Get patient list
        if args.patients:
            patient_list = [name.strip() for name in args.patients.split(',') if name.strip()]
        else:
            patient_list = read_patients_from_file(args.patients_file)
        
        if not patient_list:
            print("ERROR: No patients specified")
            sys.exit(1)
        
        print(f"Processing {len(patient_list)} patients: {', '.join(patient_list)}")
        
        # Validate dates
        start_date = args.start_date
        end_date = args.end_date
        
        if start_date and not validate_date(start_date):
            print("ERROR: Invalid start date format. Use MM/DD/YYYY")
            sys.exit(1)
        
        if end_date and not validate_date(end_date):
            print("ERROR: Invalid end date format. Use MM/DD/YYYY")
            sys.exit(1)
        
        # Set default dates if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")
            print(f"Using default start date: {start_date}")
        
        if not end_date:
            end_date = datetime.now().strftime("%m/%d/%Y")
            print(f"Using default end date: {end_date}")
        
        print(f"Search date range: {start_date} to {end_date}")
        print(f"Helper ID: {args.helper_id}")
        
        if args.dry_run:
            print("DRY RUN MODE: No patients will actually be created")
        
        # Create directories
        os.makedirs(config['REPORTS_PATH'], exist_ok=True)
        os.makedirs(config['LOGS_PATH'], exist_ok=True)
        
        # Initialize and run patient creator
        print("\nStarting patient creation workflow...")
        patient_creator = PatientCreator()
        
        if args.dry_run:
            print("DRY RUN: Testing workflow with the following patients:")
            for i, patient in enumerate(patient_list, 1):
                print(f"  {i}. {patient}")
            print("DRY RUN: Will test login, document search, and data extraction...")
            print("DRY RUN: No patients will actually be created.")
        
        # Run the main workflow
        results = patient_creator.process_failed_patients(
            patient_list=patient_list,
            helper_id=args.helper_id,
            start_date=start_date,
            end_date=end_date,
            dry_run=args.dry_run,
            api_available=api_creds_available
        )
        
        # Print summary
        print(f"\n{'='*60}")
        print("PATIENT CREATION SUMMARY")
        print(f"{'='*60}")
        
        total_processed = len(results)
        successful = len([r for r in results if r['creation_status'] == 'Success'])
        failed = total_processed - successful
        
        print(f"Total patients processed: {total_processed}")
        print(f"Successfully created: {successful}")
        print(f"Failed: {failed}")
        
        if args.verbose and results:
            print(f"\nDetailed Results:")
            for result in results:
                status_symbol = "✓" if result['creation_status'] == 'Success' else "✗"
                print(f"  {status_symbol} {result['patient_name']}: {result['creation_message']}")
        
        print(f"\nReport saved to: {config['REPORTS_PATH']}")
        print("Patient creation workflow completed.")
        
    except KeyboardInterrupt:
        print("\nWorkflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 