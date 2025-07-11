import SignedOrderDownload as sod
import FetchAthenaConfig as fc
import ReadConfig as rc
import os
import json
from datetime import datetime

def test_signed_order_download():
    try:
        # Get configuration
        try:
            config_data = fc.getConfigData()
        except Exception as e:
            print(f"Could not fetch config from API: {e}")
            print("Using local data.json instead...")
            # Use local data.json as fallback
            with open('data.json', 'r') as f:
                config_data = json.load(f)
        
        configuration = rc.readConfig()
        
        # Use the first credential from the config
        if config_data["credentials"]:
            cred = config_data["credentials"][0]
            
            # Extract parameters
            da_url = cred["daDevUrl"] if config_data["isUAT"] else cred["daProdUrl"]
            da_login = cred["daDevLoginUser"] if config_data["isUAT"] else cred["daProdLoginUser"]
            da_password = cred["daDevLoginPassword"] if config_data["isUAT"] else cred["daProdLoginPassword"]
            report_folder_name = cred["reportStorage"]
            location = cred["locationCode"] or ""
            cred_name = cred["credentialName"]
            helper_id = cred["additionals"][0]['value'] if cred["additionals"] else ""
            
            print(f"Testing SignedOrderDownload with:")
            print(f"  DA URL: {da_url}")
            print(f"  Report Folder: {report_folder_name}")
            print(f"  Credential: {cred_name}")
            print(f"  Helper ID: {helper_id}")
            print("=" * 50)
            
            # Create the working directory with proper permissions
            curr_date_str = datetime.now().strftime("%Y-%m-%d")
            working_folder = f"{configuration['OrderFolderPath']}/{curr_date_str}/{report_folder_name}"
            working_folder = working_folder.replace('\\', '/')
            
            # Create directories with proper permissions
            os.makedirs(working_folder, mode=0o755, exist_ok=True)
            print(f"Created working directory: {working_folder}")
            
            print("Starting SignedOrderDownload...")
            print("This will open a Chrome browser window...")
            
            # Run the download function
            sod.download_signed_orders(
                da_url=da_url,
                da_login=da_login,
                da_password=da_password,
                reportFolderName=report_folder_name,
                location=location,
                credName=cred_name,
                helper_id=helper_id
            )
            
            print("=" * 50)
            print("SignedOrderDownload completed successfully!")
            print(f"Check the output in: {working_folder}/OrderTemplate.xlsx")
            
        else:
            print("No credentials found in configuration!")
            
    except Exception as e:
        print(f"Error running SignedOrderDownload: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_signed_order_download() 