import requests
import json
import base64
import os
from datetime import datetime
import config_reader

class DAAPIClient:
    def __init__(self):
        self.api_config = config_reader.get_da_api_credentials()
        self.access_token = None
    
    def get_access_token(self):
        """Get access token for DA API"""
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'password',
            'username': self.api_config['username'],
            'password': self.api_config['password']
        }
        
        response = requests.post(self.api_config['token_url'], headers=headers, data=data)
        
        if response.status_code == 200:
            json_response = response.json()
            self.access_token = json_response.get('access_token')
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")
    
    def get_document_by_id(self, doc_id):
        """Get document details by document ID"""
        if not self.access_token:
            self.get_access_token()
        
        url = f"{self.api_config['document_url']}/get?docId.id={doc_id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get document: {response.status_code} - {response.text}")
    
    def get_document_file(self, doc_id, download_folder=None):
        """Download document file by document ID"""
        if not self.access_token:
            self.get_access_token()
        
        url = f"{self.api_config['document_url']}/getfile?docId.id={doc_id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        data = {
            "onlyUnfiled": True,
            "careProviderId": {
                "id": self.api_config['caretaker_id'],
                "externalId": ""
            },
            "dateFrom": None,
            "dateTo": None,
            "page": 1,
            "recordsPerPage": 10
        }
        
        response = requests.get(url, headers=headers, json=data)
        
        if response.status_code == 200:
            response_json = response.json()
            document_buffer = response_json['value']['documentBuffer']
            document_data_bytes = base64.b64decode(document_buffer)
            
            if download_folder:
                os.makedirs(download_folder, exist_ok=True)
                file_path = os.path.join(download_folder, f"{doc_id}.pdf")
                with open(file_path, "wb") as f:
                    f.write(document_data_bytes)
                return file_path, response_json
            else:
                return document_data_bytes, response_json
        else:
            raise Exception(f"Failed to download document: {response.status_code} - {response.text}")
    
    def get_patient_by_id(self, patient_id):
        """Get patient details by patient ID"""
        if not self.access_token:
            self.get_access_token()
        
        url = f"{self.api_config['patient_url']}/get?patientId.id={patient_id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get patient: {response.status_code} - {response.text}")
    
    def create_patient(self, patient_data):
        """Create a new patient in DA"""
        if not self.access_token:
            self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        response = requests.post(self.api_config['patient_url'], headers=headers, data=json.dumps(patient_data))
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to create patient: {response.status_code} - {response.text}") 