import os
import csv
import time
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Custom modules
import ReadConfig as rc
import CommonUtil as cu

# --- Helpers ---

def wait_and_click(driver, by, value, timeout=10):
    WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    ).click()

def wait_and_send_keys(driver, by, value, text, timeout=10):
    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )
    element.click()
    time.sleep(0.3)
    element.clear()
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.DELETE)
    time.sleep(0.3)
    element.send_keys(text)
    time.sleep(0.5)

# --- Inbox Table Extraction with Date Filter and seen_ids ---

def process_inbox_pages(driver, csv_path):
    page = 1
    cutoff_date = datetime.strptime("07/01/2025", "%m/%d/%Y")
    seen_ids = set()  # Track IDs seen across pages

    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        headers_written = False

        while True:
            print(f"\n📄 Processing Inbox Page {page}...")
            time.sleep(2)  # Wait before fetching rows

            try:
                rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#inbox-all-grid tbody tr"))
                )
                time.sleep(2)  # Give JS time to populate rows fully
            except TimeoutException:
                print("⚠️ Timeout waiting for inbox rows. Ending process.")
                break

            if not rows:
                print("⚠️ No rows found on this page. Ending process.")
                break

            page_data = []
            stop_flag = False

            # Process each row; refetch rows each time to avoid stale references
            for idx in range(len(rows)):
                try:
                    fresh_rows = driver.find_elements(By.CSS_SELECTOR, "#inbox-all-grid tbody tr")
                    row = fresh_rows[idx]
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 9:
                        print(f"[Warning] Row {idx+1} is malformed.")
                        continue

                    received_on = cells[7].text.strip()
                    if not received_on:
                        continue

                    received_date = datetime.strptime(received_on, "%m/%d/%Y")
                    if received_date < cutoff_date:
                        print(f"🛑 Stopping: Received On {received_on} is before 1st July.")
                        stop_flag = True
                        break

                    record_id = cells[8].text.strip()
                    if record_id in seen_ids:
                        print(f"[Info] Duplicate ID {record_id} found; skipping.")
                        continue
                    seen_ids.add(record_id)

                    row_data = [cell.text.strip() for cell in cells]
                    page_data.append(["Page " + str(page)] + row_data)

                except StaleElementReferenceException:
                    print(f"[Warning] Stale element in row {idx+1}, retrying.")
                    time.sleep(1)
                    continue
                except Exception as e:
                    print(f"[Warning] Failed to process row {idx+1}: {e}")
                    continue

            if page_data:
                print("📝 Extracted rows:")
                for row in page_data:
                    print(row)
                print("-" * 80)

                if not headers_written:
                    headers = ["Page"] + [th.text.strip() for th in driver.find_elements(By.CSS_SELECTOR, "#inbox-all-grid thead th")]
                    writer.writerow(headers)
                    headers_written = True

                for row in page_data:
                    writer.writerow(row)

            if stop_flag:
                break

            # Click next page if available
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//li[contains(@class,'page-next') and not(contains(@class, 'disabled'))]/a"))
                )
                next_button.click()
                page += 1
                time.sleep(2)  # Let the next page load
            except TimeoutException:
                print("🔚 No more pages in Inbox.")
                break


# --- Main Function ---

def open_impersonated_session(da_url, da_login, da_password, helper_id):
    driver = webdriver.Chrome()
    driver.maximize_window()

    try:
        cu.login_to_da(da_url, da_login, da_password, driver)
        driver.get("https://backoffice.doctoralliance.com/Search")

        wait_and_send_keys(driver, By.ID, "Query", helper_id)
        wait_and_click(driver, By.ID, "select2-SearchType-container")
        wait_and_send_keys(driver, By.CLASS_NAME, "select2-search__field", "Users")
        wait_and_click(driver, By.XPATH, "//li[contains(@id, 'select2-SearchType-result')][1]")
        wait_and_click(driver, By.CLASS_NAME, "btn-success")

        wait_and_click(driver, By.CLASS_NAME, "linkedRow")
        wait_and_click(driver, By.LINK_TEXT, "Impersonate")

        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
        driver.switch_to.window(driver.window_handles[1])

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        driver.get("https://live.doctoralliance.com/all/Inbox")
        print("✅ Impersonated session redirected to Inbox.")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.makedirs("Inbox", exist_ok=True)
        csv_path = os.path.join("Inbox", f"Inbox_Extracted_Data_{timestamp}.csv")
        print(f"📁 Saving CSV to: {csv_path}")

        process_inbox_pages(driver, csv_path)

        print("\n🟢 Browser remains open for manual inspection or continuation.")
        input("🕒 Press Enter here only when you're completely done using the browser...\n")

    except Exception as e:
        print(f"❌ Error occurred: {type(e).__name__}: {e}")
        traceback.print_exc()

    finally:
        driver.quit()
        print("👋 WebDriver closed.")

# --- Entry Point ---

if __name__ == "__main__":
    da_url = "https://backoffice.doctoralliance.com"
    da_login = "sannidhay"
    da_password = "DA@2025"
    helper_id = "dallianceph721"
    open_impersonated_session(da_url, da_login, da_password, helper_id)
