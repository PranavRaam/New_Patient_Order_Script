import json

def readConfig():
    config_file_path = './config.json'
    with open(config_file_path, 'r') as file:
        config_data = json.load(file)
    configuration_dict = config_data.get('configuration', {})
    return configuration_dict

#print(readConfig()["AgencyTemplatePath"])