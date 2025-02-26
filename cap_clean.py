import json
import os

ACTIVE_ALERTS_FILE = "JSON_ALERTS/active_alerts.json"

def remove_ended_alerts():
    """Removes active alerts from JSON when a corresponding 'ENDED' alert is found, regardless of alert type."""
    try:
        # Load existing alerts
        with open(ACTIVE_ALERTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            active_alerts = data.get("alerts", [])
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ No valid active alerts file found. Exiting.")
        return

    ended_alerts = {}
    
    # Identify ended alerts and affected areas
    for alert in active_alerts:
        if "ENDED" in alert["headline"].upper():
            alert_type = alert["event"].lower()
            if alert_type not in ended_alerts:
                ended_alerts[alert_type] = set()
            for area in alert["affected_areas"]:
                if isinstance(area, dict) and "area_description" in area:
                    ended_alerts[alert_type].add(area["area_description"])
                elif isinstance(area, str):
                    ended_alerts[alert_type].add(area)
    
    # Remove active alerts of the same type and area
    updated_alerts = []
    for alert in active_alerts:
        if "IN EFFECT" in alert["headline"].upper() and alert["event"].lower() in ended_alerts:
            affected_area_names = set()
            for area in alert["affected_areas"]:
                if isinstance(area, dict) and "area_description" in area:
                    affected_area_names.add(area["area_description"])
                elif isinstance(area, str):
                    affected_area_names.add(area)
            
            if any(area in ended_alerts[alert["event"].lower()] for area in affected_area_names):
                continue  # Skip this alert (remove it)
        
        updated_alerts.append(alert)

    # Save updated alerts back to file
    with open(ACTIVE_ALERTS_FILE, "w", encoding="utf-8") as file:
        json.dump({"alerts": updated_alerts}, file, indent=4, ensure_ascii=False)
    
    print(f"✅ Active alerts updated. {len(updated_alerts)} remaining.")

# Run the cleanup function
if __name__ == "__main__":
    remove_ended_alerts()
