import requests
import json
import ReadConfig as rc

def getConfigData():
    configuration={}
    configuration=rc.readConfig()
    api_key=configuration["APIKey"]
    api_url=configuration["APIBaseURL"]
    rpaName=configuration["RPA"]

    headers = {}

    headers["X-SERVICE-KEY"] = api_key
    endpoint = f"/api/Config/GetConfigDataByName/{rpaName}"
    api_endpoint = api_url + endpoint
    config_data = {}
    response = requests.get(api_endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        json_str = json.dumps(data)
        if json_str:
            config_data = json.loads(json_str)

    return config_data

# print(getConfigData())
