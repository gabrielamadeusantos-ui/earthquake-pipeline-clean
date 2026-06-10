import os
import requests
from datetime import datetime, timezone

SUPABASE_URL = "https://dynwosbiluofbqdwwuvu.supabase.co"
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

DB_ENDPOINT = f"{SUPABASE_URL}/rest/v1/earthquake_history"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates"
}

def convert_ms(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()

def run_pipeline():

    # 1. pegar último registro
    r = requests.get(
        DB_ENDPOINT,
        headers=HEADERS,
        params={
            "select": "event_time",
            "order": "event_time.desc",
            "limit": 1
        }
    )

    if r.status_code != 200 or not r.json():
        print("No data found")
        return

    last_time = r.json()[0]["event_time"]

    # 2. USGS API
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    params = {
        "format": "geojson",
        "starttime": last_time,
        "minmagnitude": 3
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("USGS error")
        return

    data = response.json().get("features", [])

    if not data:
        print("No new earthquakes")
        return

    records = []

    for q in data:
        p = q["properties"]
        g = q["geometry"]

        records.append({
            "event_id": q["id"],
            "official_link": p.get("url"),
            "last_updated": convert_ms(p.get("updated")),
            "event_time": convert_ms(p.get("time")),
            "place": p.get("place"),
            "latitude": g["coordinates"][1],
            "longitude": g["coordinates"][0],
            "depth_km": g["coordinates"][2],
            "magnitude": p.get("mag")
        })

    requests.post(DB_ENDPOINT, headers=HEADERS, json=records)

    print(f"Inserted {len(records)} records")

if __name__ == "__main__":
    run_pipeline()