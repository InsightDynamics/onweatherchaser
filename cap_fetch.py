import os
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json

# Base CAP alerts directory
BASE_CAP_URL = "https://dd.weather.gc.ca/alerts/cap/"
REGION = "CWTO"

# Define paths for saving files
CAP_SAVE_PATH = "cap_alerts/"
JSON_SAVE_PATH = "JSON_ALERTS/"
ACTIVE_ALERTS_FILE = os.path.join(JSON_SAVE_PATH, "active_alerts.json")

# Ensure directories exist
os.makedirs(CAP_SAVE_PATH, exist_ok=True)
os.makedirs(JSON_SAVE_PATH, exist_ok=True)

# Step 1: Get the latest available CAP date
def get_latest_cap_date():
    response = requests.get(BASE_CAP_URL)
    if response.status_code != 200:
        print("⚠️ Unable to access the CAP main directory.")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    dates = [link.get("href").strip("/") for link in soup.find_all("a") if link.get("href").strip("/").isdigit()]
    
    return max(dates) if dates else None

# Step 2: Get available hourly subdirectories
def get_hourly_folders(cap_date):
    region_url = f"{BASE_CAP_URL}{cap_date}/{REGION}/"
    response = requests.get(region_url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    return [link.get("href").strip("/") for link in soup.find_all("a") if link.get("href").strip("/").isdigit()]

# Step 3: Get CAP XML files from hourly folders
def get_cap_files(cap_date, hourly_folders):
    cap_files = []
    for hour in hourly_folders:
        cap_url = f"{BASE_CAP_URL}{cap_date}/{REGION}/{hour}/"
        response = requests.get(cap_url)
        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        cap_files.extend([cap_url + link.get("href") for link in soup.find_all("a") if link.get("href").endswith(".cap")])

    return cap_files

# Step 4: Download CAP files
def download_cap_files(file_urls):
    saved_files = []
    
    for file_url in file_urls:
        file_name = file_url.split("/")[-1]
        file_path = os.path.join(CAP_SAVE_PATH, file_name)

        response = requests.get(file_url)
        if response.status_code == 200:
            with open(file_path, "wb") as file:
                file.write(response.content)
            saved_files.append(file_path)

    return saved_files

# Step 5: Convert CAP XML files to JSON
def parse_cap_to_json(cap_file_path):
    tree = ET.parse(cap_file_path)
    root = tree.getroot()
    namespace = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}

    info_blocks = root.findall("cap:info", namespace)
    selected_info = next((info for info in info_blocks if info.find("cap:language", namespace) is not None and "en" in info.find("cap:language", namespace).text), info_blocks[0] if info_blocks else None)

    if selected_info is None:
        return {}

    alert_info = {
        "headline": selected_info.find("cap:headline", namespace).text if selected_info.find("cap:headline", namespace) is not None else "N/A",
        "affected_areas": [
            area.find("cap:areaDesc", namespace).text if area.find("cap:areaDesc", namespace) is not None else "N/A"
            for area in selected_info.findall("cap:area", namespace)
        ]
    }
    return alert_info

# Step 6: Remove ended alerts
def remove_ended_alerts(active_alerts):
    ended_areas = set()

    for alert in active_alerts:
        if "ENDED" in alert["headline"].upper():
            ended_areas.update(alert["affected_areas"])

    return [
        alert for alert in active_alerts
        if not ("IN EFFECT" in alert["headline"].upper() and any(area in ended_areas for area in alert["affected_areas"]))
    ]

# Step 7: Process CAP files and update active alerts
def convert_to_json(cap_files):
    active_alerts = []
    for cap_file in cap_files:
        alert_data = parse_cap_to_json(cap_file)
        if alert_data:
            active_alerts.append(alert_data)

    try:
        with open(ACTIVE_ALERTS_FILE, "r", encoding="utf-8") as file:
            stored_alerts = json.load(file).get("alerts", [])
    except (FileNotFoundError, json.JSONDecodeError):
        stored_alerts = []

    updated_alerts = remove_ended_alerts(stored_alerts + active_alerts)

    with open(ACTIVE_ALERTS_FILE, "w", encoding="utf-8") as file:
        json.dump({"alerts": updated_alerts}, file, indent=4, ensure_ascii=False)

    print(f"✅ Active alerts updated. {len(updated_alerts)} remaining.")

# Step 8: Run the process
latest_date = get_latest_cap_date()
if latest_date:
    hourly_folders = get_hourly_folders(latest_date)
    if hourly_folders:
        cap_files = get_cap_files(latest_date, hourly_folders)
        if cap_files:
            downloaded_files = download_cap_files(cap_files)
            if downloaded_files:
                convert_to_json(downloaded_files)
