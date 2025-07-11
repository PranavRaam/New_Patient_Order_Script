import json
import os

def read_config():
    """Read configuration from config.json file"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as file:
            config_data = json.load(file)
            return config_data['configuration']
    except FileNotFoundError:
        raise Exception(f"Configuration file not found at {config_path}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON format in configuration file")
    except KeyError:
        raise Exception("Missing 'configuration' key in config file")

def get_da_credentials():
    """Get DA login credentials"""
    config = read_config()
    return {
        'url': config['DA_WEB_URL'],
        'username': config['DA_USERNAME'],
        'password': config['DA_PASSWORD']
    }

def get_da_api_credentials():
    """Get DA API credentials"""
    config = read_config()
    return {
        'token_url': config['DA_API_TOKEN_URL'],
        'base_url': config['DA_API_BASE_URL'],
        'username': config['DA_API_TOKEN_USERNAME'],
        'password': config['DA_API_TOKEN_PASSWORD'],
        'clinician_id': config['DA_API_TOKEN_CLINICIAN_ID'],
        'caretaker_id': config['DA_API_TOKEN_CARETAKER_ID']
    }

def get_helper_id():
    """Get helper ID from config"""
    config = read_config()
    return config.get('HELPER_ID', '')

def get_paths():
    """Get various paths from config"""
    config = read_config()
    return {
        'download_path': config.get('DOWNLOAD_PATH', './downloads/'),
        'reports_path': config.get('REPORTS_PATH', './reports/'),
        'logs_path': config.get('LOGS_PATH', './logs/'),
        'chrome_driver_path': config.get('CHROME_DRIVER_PATH', '')
    } 