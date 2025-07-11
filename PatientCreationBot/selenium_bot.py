import time
import os
import shutil
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import config_reader

class DASeleniumBot:
    def __init__(self):
        self.config = config_reader.read_config()
        self.da_creds = config_reader.get_da_credentials()
        self.driver = None
        self.wait = None
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Set download preferences
            prefs = {
                "download.default_directory": self.config['DOWNLOAD_PATH'],
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Try different driver initialization methods
            print("Initializing Chrome driver...")
            
            try:
                # Method 1: Use webdriver-manager with latest driver
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("Chrome driver initialized with webdriver-manager")
            except Exception as e1:
                print(f"webdriver-manager failed: {str(e1)}")
                try:
                    # Method 2: Use specified path if available
                    if os.path.exists(self.config['CHROME_DRIVER_PATH']):
                        service = Service(self.config['CHROME_DRIVER_PATH'])
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        print("Chrome driver initialized with specified path")
                    else:
                        raise Exception("No Chrome driver path specified")
                except Exception as e2:
                    print(f"Specified path failed: {str(e2)}")
                    # Method 3: Try without explicit service
                    try:
                        self.driver = webdriver.Chrome(options=chrome_options)
                        print("Chrome driver initialized without explicit service")
                    except Exception as e3:
                        raise Exception(f"All Chrome driver initialization methods failed. Last error: {str(e3)}")
            
            # Remove the maximize_window call that's causing issues
            # self.driver.maximize_window()
            
            # Set window size instead
            self.driver.set_window_size(1920, 1080)
            self.wait = WebDriverWait(self.driver, 10)
            print("Chrome driver setup completed successfully")
            
        except Exception as e:
            print(f"Chrome driver setup error: {str(e)}")
            raise Exception(f"Failed to initialize Chrome driver: {str(e)}")
    
    def login_to_da(self):
        """Login to Document Alliance platform using proven selectors"""
        print(f"Logging into DA: {self.da_creds['url']}")
        self.driver.get(self.da_creds['url'])
        
        try:
            time.sleep(3)
            print(f"Current URL: {self.driver.current_url}")
            print(f"Page title: {self.driver.title}")
            
            # Use the proven selectors from SignedOrderDownload.py
            print("Looking for username field...")
            username_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Username']")))
            print("Found username field")
            
            print("Looking for password field...")
            password_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Password']")))
            print("Found password field")
            
            # Clear and fill credentials
            username_field.clear()
            username_field.send_keys(self.da_creds['username'])
            print("Username entered")
            
            password_field.clear()
            password_field.send_keys(self.da_creds['password'])
            print("Password entered")
            
            time.sleep(2)
            
            # Use the proven login button selector
            print("Looking for login button...")
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button.btn.btn-primary.btn-block")
            print("Found login button")
            
            login_button.click()
            print("Login button clicked")
            
            # Wait for login to complete
            print("Waiting for login to complete...")
            time.sleep(5)
            
            current_url = self.driver.current_url
            print(f"After login URL: {current_url}")
            
            # Simple check - if URL changed or we can find dashboard elements, assume success
            if current_url != self.da_creds['url']:
                print("Login successful - URL changed")
            else:
                print("Login completed - same URL")
            
        except Exception as e:
            print(f"Login error details: {str(e)}")
            # Save screenshot for debugging
            try:
                screenshot_path = "/tmp/login_error.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to: {screenshot_path}")
            except:
                pass
            raise Exception(f"Login failed: {str(e)}")
    
    def navigate_to_search(self, helper_id):
        """Navigate to search page and impersonate user"""
        print("Clicking on Search in the left sidebar...")
        
        try:
            # Click on the Search link in the left sidebar
            search_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/Search') or contains(text(), 'Search')]")))
            search_link.click()
            time.sleep(5)
            print("Clicked on Search in sidebar")
            
            # Search for the helper ID
            query_input = self.wait.until(EC.presence_of_element_located((By.ID, "Query")))
            query_input.send_keys(helper_id)
            time.sleep(2)
            
            # Select "Users" from dropdown
            search_type_dropdown = self.driver.find_element(By.ID, "select2-SearchType-container")
            search_type_dropdown.click()
            time.sleep(1)
            
            input_field = self.driver.find_element(By.CLASS_NAME, "select2-search__field")
            input_field.send_keys("Users")
            time.sleep(2)
            
            # Click first result
            first_result = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@id, 'select2-SearchType-result')][1]")))
            first_result.click()
            time.sleep(2)
            
            # Click search button
            search_button = self.driver.find_element(By.CLASS_NAME, "btn-success")
            search_button.click()
            time.sleep(5)
            
            # Click on the user row
            user_row = self.driver.find_element(By.CLASS_NAME, "linkedRow")
            user_row.click()
            time.sleep(3)
            
            # Click impersonate link
            impersonate_link = self.driver.find_element(By.LINK_TEXT, "Impersonate")
            impersonate_link.click()
            time.sleep(7)
            
            # Switch to new window
            self.driver.switch_to.window(self.driver.window_handles[1])
            print(f"Successfully impersonated helper ID: {helper_id}")
            
        except Exception as e:
            raise Exception(f"Failed to navigate and impersonate: {str(e)}")
    
    def fetch_485_certificates(self, patient_names, start_date=None, end_date=None):
        """Fetch 485 certificates for specific patients"""
        print("Fetching 485 certificates...")
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")
        if not end_date:
            end_date = datetime.now().strftime("%m/%d/%Y")
        
        try:
            # Navigate to documents section - try multiple selectors like the existing code
            print("Looking for Documents link in sidebar...")
            
            # Try different selectors for Documents link
            documents_selectors = [
                "//a[contains(@href, '/Documents')]",
                "//a[contains(text(), 'Documents')]",
                "//a[@href='/Documents']",
                "//li[contains(text(), 'Documents')]//a",
                "//*[contains(text(), 'Documents')]"
            ]
            
            documents_link = None
            for selector in documents_selectors:
                try:
                    documents_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    print(f"Found Documents link with selector: {selector}")
                    break
                except:
                    continue
            
            if not documents_link:
                # If still not found, let's see what links are available
                print("Could not find Documents link. Available links in sidebar:")
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for i, link in enumerate(links[:10]):  # Show first 10 links
                    href = link.get_attribute("href") or "no-href"
                    text = link.text or "no-text"
                    print(f"  Link {i}: href='{href}', text='{text}'")
                
                # Try to navigate directly to Documents URL
                print("Trying direct navigation to Documents...")
                current_url = self.driver.current_url
                base_url = current_url.split('/')[0] + '//' + current_url.split('/')[2]
                documents_url = f"{base_url}/Documents"
                print(f"Navigating to: {documents_url}")
                self.driver.get(documents_url)
                time.sleep(3)
            else:
                documents_link.click()
                time.sleep(3)
            
            print("Successfully navigated to Documents section")
            
            # Navigate to "All" tab in Documents section
            print("Clicking on 'All' tab...")
            try:
                # Try different selectors for the "All" tab
                all_tab_selectors = [
                    "//a[contains(text(), 'All')]",
                    "//li/a[contains(text(), 'All')]",
                    "//a[@href='#all']",
                    "//a[contains(@href, 'All')]",
                    "//*[contains(text(), 'All') and contains(@class, 'nav')]//a"
                ]
                
                all_tab_found = False
                for selector in all_tab_selectors:
                    try:
                        all_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        all_tab.click()
                        time.sleep(2)
                        print(f"Successfully clicked 'All' tab with selector: {selector}")
                        all_tab_found = True
                        break
                    except:
                        continue
                
                if not all_tab_found:
                    print("Warning: Could not find 'All' tab, continuing with default view...")
            except Exception as e:
                print(f"Warning: Error clicking 'All' tab: {str(e)}, continuing...")
            
            # Set date range
            print("Setting date range...")
            start_date_input = self.wait.until(EC.presence_of_element_located((By.ID, "StartDatePicker")))
            start_date_input.clear()
            start_date_input.send_keys(start_date)
            time.sleep(1)
            
            end_date_input = self.driver.find_element(By.ID, "EndDatePicker")
            end_date_input.clear()
            end_date_input.send_keys(end_date)
            time.sleep(1)
            
            # Click refresh/go button
            print("Clicking refresh button...")
            go_button = self.driver.find_element(By.ID, "btnRefreshGrid")
            go_button.click()
            time.sleep(5)
            
            # Check if any records found
            try:
                no_records = self.driver.find_element(By.XPATH, "//td[contains(text(), 'No matching records found')]")
                print("No documents found in the specified date range")
                return []
            except:
                pass  # Records found, continue
            
            print("Processing documents table...")
            
            # Extract 485 certificates
            certificates_485 = []
            page_num = 1
            
            while True:
                print(f"Processing page {page_num}...")
                
                # Get all rows from current page - try different table selectors
                table_selectors = [
                    "#signed-docs-grid tbody tr",
                    "#docs-grid tbody tr", 
                    "table tbody tr",
                    ".table tbody tr"
                ]
                
                table_rows = []
                for selector in table_selectors:
                    try:
                        table_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if table_rows:
                            print(f"Found {len(table_rows)} rows with selector: {selector}")
                            break
                    except:
                        continue
                
                if not table_rows:
                    print("No table rows found")
                    break
                
                for row in table_rows:
                    try:
                        # Extract row data - fix column positions based on actual DA table structure
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 9:  # Need at least 9 columns based on screenshot
                            continue
                            
                        # Correct column positions based on DA platform screenshot:
                        # Column 1: Checkbox, Column 2: Physician, Column 3: Doc Type, 
                        # Column 4: Facility, Column 5: Facility Type, Column 6: Patient, 
                        # Column 7: Status, Column 8: Received On, Column 9: ID
                        physician = self._clean_text(cells[1].text)     # Column 2: Physician
                        doc_type = self._clean_text(cells[2].text)      # Column 3: Doc Type
                        facility = self._clean_text(cells[3].text)      # Column 4: Facility
                        patient_name = self._clean_text(cells[5].text)  # Column 6: Patient
                        status = self._clean_text(cells[6].text)        # Column 7: Status
                        received_on = self._clean_text(cells[7].text)   # Column 8: Received On
                        doc_id = self._clean_text(cells[8].text)        # Column 9: ID
                        
                        # Check if this is a 485 certificate and patient is in our target list
                        if self._is_485_certificate(doc_type) and self._is_target_patient(patient_name, patient_names):
                            cert_data = {
                                'patient_name': patient_name,
                                'doc_type': doc_type,
                                'doc_id': doc_id,
                                'order_date': received_on,  # Use received_on as order_date
                                'status': status,
                                'physician': physician,
                                'facility': facility
                            }
                            certificates_485.append(cert_data)
                            print(f"Found 485 certificate for patient: {patient_name} (Doc ID: {doc_id}, Type: {doc_type})")
                    
                    except Exception as e:
                        print(f"Error processing row: {str(e)}")
                        continue
                
                # Check if there's a next page
                try:
                    next_button = self.driver.find_element(By.XPATH, "//a[@aria-label='Next']")
                    if 'disabled' in next_button.get_attribute('class'):
                        break
                    next_button.click()
                    time.sleep(3)
                    page_num += 1
                except:
                    break  # No more pages
            
            print(f"Found {len(certificates_485)} 485 certificates")
            return certificates_485
            
        except Exception as e:
            print(f"Error details: {str(e)}")
            # Save screenshot for debugging
            try:
                screenshot_path = "/tmp/documents_error.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to: {screenshot_path}")
            except:
                pass
            raise Exception(f"Failed to fetch 485 certificates: {str(e)}")
    
    def _clean_text(self, text):
        """Clean and normalize text data"""
        if text:
            return text.strip().replace('\n', ' ').replace('\r', '')
        return ""
    
    def _is_485_certificate(self, doc_type):
        """Check if document type indicates a 485 certificate"""
        if not doc_type:
            return False
        doc_type_lower = doc_type.lower()
        return any(term in doc_type_lower for term in [
            '485',
            'plan of care', 
            'poc',
            'recert',  # Added to catch "485 Recert" from screenshot
            'certification',
            'care plan'
        ])
    
    def _is_target_patient(self, patient_name, target_names):
        """Check if patient is in the target list"""
        if not patient_name or not target_names:
            return True  # If no filter provided, include all
        
        patient_name_lower = patient_name.lower().strip()
        
        for target_name in target_names:
            target_name_lower = target_name.lower().strip()
            
            # Direct match
            if target_name_lower == patient_name_lower:
                return True
            
            # Check if target name appears in patient name
            if target_name_lower in patient_name_lower:
                return True
            
            # Handle "Last, First" format - try matching parts
            if ',' in patient_name_lower:
                # Split "Ostendorf, Pat" into ["Ostendorf", "Pat"]
                name_parts = [part.strip() for part in patient_name_lower.split(',')]
                for part in name_parts:
                    if part in target_name_lower or target_name_lower in part:
                        return True
            
            # Handle "First Last" format in target vs "Last, First" in patient
            if ',' not in target_name_lower and ',' in patient_name_lower:
                # Convert "John Doe" to match against "Doe, John"
                target_parts = target_name_lower.split()
                if len(target_parts) >= 2:
                    first_name = target_parts[0]
                    last_name = target_parts[-1]
                    if (first_name in patient_name_lower and last_name in patient_name_lower):
                        return True
        
        return False
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("Browser closed") 