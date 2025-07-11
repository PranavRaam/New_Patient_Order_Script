import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import ReadConfig as rc
from datetime import datetime
import os

def upload_file(reportFolderName):
    configuration = rc.readConfig()
    working_folder = configuration["WorkingFolderPath"]
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")
    working_file=os.path.join(working_folder,"AgencyTemplate_"+formatted_date+".xlsx")
    api_key=configuration["APIKey"]
    api_url=configuration["APIBaseURL"]
    working_file = working_file.replace('\\', '/')
    file_name = working_file.split('/')[-1]
    api_endpoint=api_url+"api/Agency/UploadFileToBlob"

    with open(working_file, 'rb') as file_stream:
        file_content = file_stream.read()

    # Create the multipart encoder for the form data
    multipart_encoder = MultipartEncoder(
            fields={'file': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        )

    # Create the headers
    headers = {
        'X-SERVICE-KEY': api_key,
        'Content-Type': multipart_encoder.content_type,
    }

    # Make the POST request
    response = requests.post(f"{api_endpoint}?folderName={reportFolderName}", data=multipart_encoder, headers=headers, timeout=300)

    if response.status_code == requests.codes.ok:
        print("File uploaded successfully!")
    else:
        print(f"Error: {response.status_code} - {response.reason}")

#upload_file("Axxess-StandardHomeHealth")
