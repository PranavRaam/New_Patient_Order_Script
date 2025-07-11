import os
import csv
import time
import logging
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)

import CommonUtil as cu  # Your local utility module

logging.basicConfig(
    filename="automation.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def wait_and_click(driver, by, value, timeout=15):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
    except Exception as e:
        logging.error(f"[Click Failed] {by} = {value} -> {e}")
        raise

def wait_and_send_keys(driver, by, value, text, timeout=15):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        element.clear()
        element.send_keys(text)
    except Exception as e:
        logging.error(f"[SendKeys Failed] {by} = {value} -> {e}")
        raise

def download_entire_signed_table(da_url, da_login, da_password, report_folder, helper_id):
    driver = None
    try:
        os.makedirs(report_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_path = os.path.join(report_folder, f"SignedDocuments_{timestamp}.csv")
        print(f"📁 CSV will be saved at: {csv_path}")

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()

        print("🔐 Logging in...")
        cu.login_to_da(da_url, da_login, da_password, driver)

        WebDriverWait(driver, 20).until(
            EC.url_contains("backoffice.doctoralliance.com")
        )
        print("✅ Login successful.")

        print("🔍 Navigating to Search page...")
        driver.get(f"{da_url}/Search")
        wait_and_send_keys(driver, By.ID, "Query", helper_id)
        wait_and_click(driver, By.ID, "select2-SearchType-container")
        wait_and_send_keys(driver, By.CLASS_NAME, "select2-search__field", "Users")
        wait_and_click(driver, By.XPATH, "//li[contains(@id, 'select2-SearchType-result')][1]")
        wait_and_click(driver, By.CLASS_NAME, "btn-success")

        print("👤 Impersonating user...")
        wait_and_click(driver, By.CLASS_NAME, "linkedRow")
        wait_and_click(driver, By.LINK_TEXT, "Impersonate")
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
        driver.switch_to.window(driver.window_handles[1])
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("✅ Impersonation successful.")

        print("📄 Opening Signed Documents...")
        wait_and_click(driver, By.XPATH, "//a[contains(@href, '/Documents/Signed')]")

        start_date = "07/01/2025"
        end_date = datetime.now().strftime("%m/%d/%Y")
        print(f"📅 Filtering from {start_date} to {end_date}")
        wait_and_send_keys(driver, By.ID, "StartDatePicker", start_date)
        wait_and_send_keys(driver, By.ID, "EndDatePicker", end_date)
        wait_and_click(driver, By.ID, "btnRefreshGrid")

        # Wait for data or no records message
        max_wait = 20
        poll_interval = 2
        elapsed = 0
        found_rows = False
        found_no_records = False

        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            rows = driver.find_elements(By.CSS_SELECTOR, "#signed-docs-grid tbody tr")
            no_records_msgs = driver.find_elements(By.XPATH, "//*[contains(text(), 'No matching records')]")

            if len(rows) > 0:
                found_rows = True
                break
            if len(no_records_msgs) > 0:
                found_no_records = True
                break

        if found_no_records:
            print("⚠️ No signed orders found.")
            return

        if not found_rows:
            print("⚠️ Timeout waiting for data rows or no records message.")
            container = driver.find_element(By.CSS_SELECTOR, "#signed-docs-grid")
            print(container.get_attribute('innerHTML'))
            return

        print("✅ Records found. Extracting...")

        seen_ids = set()
        page = 1

        with open(csv_path, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = None

            while True:
                print(f"📄 Processing Page {page}...")

                rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#signed-docs-grid tbody tr"))
                )

                if writer is None:
                    headers = [th.text.strip() for th in driver.find_elements(By.CSS_SELECTOR, "#signed-docs-grid thead th")]
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)

                page_data = []

                duplicate_found = False

                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        row_texts = [cell.text.strip() for cell in cells]
                        page_data.append(row_texts)

                        # Assuming document ID is in the 10th column (index 9) and contains a span with class 'text-muted'
                        doc_id_elem = cells[9].find_element(By.CSS_SELECTOR, "span.text-muted")
                        doc_id = doc_id_elem.text.strip()

                        if doc_id in seen_ids:
                            duplicate_found = True
                        else:
                            seen_ids.add(doc_id)
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        print(f"[Warning] Error processing a row: {e}")
                        continue

                # Print entire page data table to console
                print("Table data on this page:")
                for row_data in page_data:
                    print(row_data)
                print("-" * 80)

                # Write page data to CSV
                for row_data in page_data:
                    writer.writerow(row_data)

                if duplicate_found:
                    print("🔄 Duplicate document ID found, stopping pagination to avoid loops.")
                    break

                # Try clicking next page
                try:
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//li[@class='page-next']/a"))
                    )
                    next_button.click()
                    page += 1
                    time.sleep(2)  # wait for grid refresh
                except TimeoutException:
                    print("🔚 No more pages.")
                    break

        print(f"\n✅ Extraction complete. CSV saved at:\n{csv_path}")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        logging.error(f"[ERROR] {type(e).__name__}: {e}\n{traceback.format_exc()}")

    finally:
        if driver:
            driver.quit()
            print("👋 WebDriver closed.")
            logging.info("WebDriver closed.")

if __name__ == "__main__":
    download_entire_signed_table(
        da_url="https://backoffice.doctoralliance.com",
        da_login="sannidhay",
        da_password="DA@2025",
        report_folder="Orders",
        helper_id="dallianceph721"
    )
