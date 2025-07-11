import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import chromedriver_autoinstaller
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
import os
import shutil
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import pyautogui
import ReadConfig as rc
import CommonUtil as cu
from datetime import datetime

def wait_and_find_element(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def click_element(element):
    try:
        element.click()
    except Exception as ex:
        print(f"Error clicking element: {str(ex)}")
        exit()

def hover_and_click(driver, script, element):
    try:
        driver.execute_script(script, element)
        time.sleep(2)
    except Exception as ex:
        print(f"Error executing script: {str(ex)}")
        exit()

def order_download(url,email,password,helperId,reportFolderName):
    configuration = rc.readConfig()
    logFolder = configuration["LogPath"]
    logFilepath=logFolder+"log_"+str(datetime.now().year)+"-"+str(datetime.now().month)+"-"+str(datetime.now().day)+".txt"
    working_folder = cu.getFolderPath("O", reportFolderName)
    [os.remove(os.path.join(working_folder, f)) if os.path.isfile(os.path.join(working_folder, f)) else shutil.rmtree(os.path.join(working_folder, f)) for f in os.listdir(working_folder)]
    
    download_folder=configuration["DownloadPath"]

    driver = webdriver.Chrome()
    driver.maximize_window()
    try:
        for ctr in range(3):
            try:
                driver.get(url)
                actions = ActionChains(driver)
                time.sleep(3)
                email_input = wait_and_find_element(driver,By.CSS_SELECTOR, "input[placeholder='Username']")
                email_input.send_keys(email)

                password_input = wait_and_find_element(driver,By.CSS_SELECTOR, "input[placeholder='Password']")
                password_input.send_keys(password)
                time.sleep(2) 

                login_button = driver.find_element(By.XPATH, "//button[contains(text(),'Login')]")
                login_button.click()
                time.sleep(1)

                # search_button = driver.find_element(By.XPATH, "//a[contains(text(),'Search')]")
                # search_button.click()
                driver.get('https://backoffice.doctoralliance.com/Search')
                time.sleep(1)

                search_input = wait_and_find_element(driver,By.CSS_SELECTOR, "input[placeholder='Enter search text...']")
                search_input.send_keys(helperId)
                
                user_dd = wait_and_find_element(driver,By.ID, "select2-SearchType-container")
                user_dd.click()
                time.sleep(1)

                for i in range(8):
                    actions.send_keys(Keys.ARROW_DOWN)  # Scroll down
                actions.perform()                            

                select_users = wait_and_find_element(driver,By.XPATH, "//li[contains(text(),'Users')]")
                select_users.click()
                time.sleep(1)

                search_user = driver.find_element(By.XPATH, "//button[contains(text(),'Search')]")
                search_user.click()
                time.sleep(2)

                user_row = driver.find_element(By.CLASS_NAME, "linkedRow")
                user_row.click()
                time.sleep(4)

                impersonate_button = driver.find_element(By.XPATH, "//a[contains(text(),'Impersonate')]")
                impersonate_button.click()
                time.sleep(2)

                driver.switch_to.window(driver.window_handles[1])

                driver.get('https://live.doctoralliance.com/all/Documents/Signed?filter=signedunfiled')
                time.sleep(1)

                start_date = wait_and_find_element(driver,By.CSS_SELECTOR, "input[id='StartDatePicker']")
                start_date.send_keys('02/24/2024')

                end_date = wait_and_find_element(driver,By.CSS_SELECTOR, "input[id='EndDatePicker']")
                end_date.send_keys('02/28/2024')

                go_button = driver.find_element(By.XPATH, "//button[contains(text(),'Go')]")
                go_button.click()
                time.sleep(2)

                time.sleep(10)
                driver.quit() 

            except Exception as e:
                print(logFilepath, str(e))
    except Exception as e:
                print(logFilepath, str(e))