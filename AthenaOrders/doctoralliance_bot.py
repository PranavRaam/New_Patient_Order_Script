import os
import time
import csv
import sys
from typing import List
import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = "https://backoffice.doctoralliance.com/Home/Login"

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def get_credentials() -> tuple[str, str]:
    """Return (username, password) pair from env vars or raise ValueError."""
    username = os.getenv("DOCTORALLIANCE_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("DOCTORALLIANCE_PASSWORD") or os.getenv("PASSWORD")
    if not (username and password):
        raise ValueError(
            "Username/password not set. Export DOCTORALLIANCE_USERNAME and DOCTORALLIANCE_PASSWORD env vars."
        )
    return username, password


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Return a configured Chrome WebDriver instance."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


# ---------------------------------------------------------------------------
# CSV utilities
# ---------------------------------------------------------------------------

def load_patient_names(csv_path: str) -> List[str]:
    """Return a list of patient names from the first column of csv_path."""
    names: List[str] = []
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as fp:
            reader = csv.reader(fp)
            for row in reader:
                if row and row[0].strip():
                    names.append(row[0].strip())
    except FileNotFoundError:
        print(f"[error] Patient CSV not found: {csv_path}")
        sys.exit(1)
    if not names:
        print(f"[error] No patient names found in: {csv_path}")
        sys.exit(1)
    return names


# ---------------------------------------------------------------------------
# Page interaction helpers
# ---------------------------------------------------------------------------

def ensure_on_search_page(driver: webdriver.Chrome) -> None:
    """Guarantee that we are currently on the /Search route (logs in first)."""
    if "/Search" not in driver.current_url:
        # Try sidebar link first
        try:
            search_link = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="/Search"]'))
            )
            search_link.click()
            WebDriverWait(driver, 10).until(lambda d: "/Search" in d.current_url)
            return
        except Exception:
            driver.get("https://backoffice.doctoralliance.com/Search")
            WebDriverWait(driver, 10).until(lambda d: "/Search" in d.current_url)


def choose_search_type_patients(driver: webdriver.Chrome) -> None:
    """Select the "Patients" option in the Select2 dropdown once per session."""
    # Click the select2 container to open dropdown
    driver.find_element(By.CSS_SELECTOR, "span.select2-selection--single").click()
    # Wait for dropdown options
    option_locator = (By.CSS_SELECTOR, "li.select2-results__option")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located(option_locator))
    options = driver.find_elements(*option_locator)
    for opt in options:
        if opt.text.strip().lower() == "patients":
            opt.click()
            break
    else:
        print("[warn] 'Patients' option not found in search type dropdown.")


def search_one_patient(driver: webdriver.Chrome, name: str) -> List[dict[str, str]]:
    """Perform a search for a single patient name and return parsed rows."""
    ensure_on_search_page(driver)

    # Enter name into #Query input
    query_input = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "Query"))
    )
    query_input.clear()
    query_input.send_keys(name)

    # Make sure search type is set to Patients (only the first time, detect by container text)
    try:
        container = driver.find_element(By.ID, "select2-SearchType-container")
        if container.text.strip().lower() != "patients":
            choose_search_type_patients(driver)
    except Exception:
        # If container missing, best-effort select
        choose_search_type_patients(driver)

    # Click Search button (assume button with text "Search" or type submit)
    try:
        search_btn = driver.find_element(By.CSS_SELECTOR, "button[type=submit], button.btn-primary")
        search_btn.click()
    except Exception:
        # Press Enter key in query input as fallback
        query_input.send_keys("\n")

    # Wait for results table refresh (could use explicit wait on a data row)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table#patientsTable tbody tr"))
    )

    rows = driver.find_elements(By.CSS_SELECTOR, "table#patientsTable tbody tr")
    results = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            results.append({"id": cells[0].text.strip(), "name": cells[1].text.strip()})
    return results


# ---------------------------------------------------------------------------
# Core fetch loop
# ---------------------------------------------------------------------------

def fetch_patients_for_names(driver: webdriver.Chrome, names: List[str]) -> List[dict[str, str]]:
    all_results: List[dict[str, str]] = []
    for idx, name in enumerate(names, 1):
        print(f"[bot] ({idx}/{len(names)}) Searching for '{name}' …")
        try:
            rows = search_one_patient(driver, name)
            all_results.extend(rows)
            print(f"      ↳ found {len(rows)} rows")
        except Exception as exc:
            print(f"[warn] Failed to search for '{name}': {exc}")
    return all_results


# ---------------------------------------------------------------------------
# Core bot logic
# ---------------------------------------------------------------------------

def login(driver: webdriver.Chrome, username: str, password: str) -> None:
    """Open the login page and authenticate."""
    driver.get(LOGIN_URL)

    # Wait for username field to be present
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "Username")))

    # Fill credentials
    driver.find_element(By.ID, "Username").send_keys(username)
    driver.find_element(By.ID, "Password").send_keys(password)

    # Attempt to locate a button with text "Login" or type submit
    # Fallback: press ENTER on password field
    try:
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button, input[type=submit]")
        submit_btn.click()
    except Exception:
        driver.find_element(By.ID, "Password").send_keys("\n")

    # Wait for redirect after successful login (URL change or presence of logout link)
    WebDriverWait(driver, 20).until(lambda d: d.current_url != LOGIN_URL)


def fetch_patients(driver: webdriver.Chrome) -> List[dict[str, str]]:
    """Navigate to the Search page and return a list of patient dicts.

    The function now clicks the sidebar link <a href="/Search"> and waits for the
    page to load. Update selectors as needed for the actual Search results table.
    """
    patients: List[dict[str, str]] = []

    # Click the sidebar "Search" link (href="/Search")
    try:
        search_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="/Search"]'))
        )
        search_link.click()
        # Wait until the URL contains "/Search" or a known element appears.
        WebDriverWait(driver, 15).until(lambda d: "/Search" in d.current_url)
    except Exception:
        print("[warn] Could not click the Search link; falling back to direct navigation.")
        driver.get("https://backoffice.doctoralliance.com/Search")
        WebDriverWait(driver, 15).until(lambda d: "/Search" in d.current_url)

    # TODO: Once on the Search page, enter any required filters or press search.
    # For now, attempt to grab patients from a table similar to earlier placeholder.

    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table#patientsTable tbody tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 2:
                patients.append({
                    "id": cells[0].text.strip(),
                    "name": cells[1].text.strip(),
                })
    except Exception:
        print("[warn] Could not locate patient table on Search page; update selectors in fetch_patients().")

    return patients


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Doctor Alliance Backoffice patient fetch bot (Selenium).")
    parser.add_argument("--headless", dest="headless", action="store_true", help="Run Chrome in headless mode (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run Chrome with visible window")
    parser.set_defaults(headless=True)
    parser.add_argument("--csv", dest="csv_path", help="Optional path to write patients CSV (default patients_TIMESTAMP.csv)")
    parser.add_argument("--patients", dest="patients_path", required=False, default="patient_name.csv", help="CSV file containing patient names (first column; default patient_name.csv)")

    args = parser.parse_args()

    username, password = get_credentials()
    driver = create_driver(headless=args.headless)

    try:
        print("[bot] Logging in …")
        login(driver, username, password)
        print("[bot] Login successful. Fetching patients …")
        patient_names = load_patient_names(args.patients_path)
        patients = fetch_patients_for_names(driver, patient_names)
        print(f"[bot] Collected {len(patients)} patient records from search queries.")

        if args.csv_path or patients:
            ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            csv_path = args.csv_path or f"patients_{ts}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as fp:
                writer = csv.DictWriter(fp, fieldnames=["id", "name"])
                writer.writeheader()
                writer.writerows(patients)
            print(f"[bot] CSV written: {csv_path}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main() 