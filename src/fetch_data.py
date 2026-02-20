import json
import os
import time
import zipfile

import requests

from config import DATA_DIR

BASE_URL = "https://api.fda.gov/drug/event.json"
TARGET_RECORDS = 5000
BATCH_SIZE = 100
RATE_LIMIT_DELAY = 0.3


def fetch_adverse_events(target: int = TARGET_RECORDS) -> list[dict]:
    """Pull adverse event reports from the OpenFDA drug adverse events endpoint."""
    all_records = []
    skip = 0

    while len(all_records) < target:
        params = {
            "limit": BATCH_SIZE,
            "skip": skip,
        }

        response = requests.get(BASE_URL, params=params)

        if response.status_code == 429:
            print("Rate limited, backing off for 5s...")
            time.sleep(5)
            continue

        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        all_records.extend(results)
        skip += BATCH_SIZE

        print(f"Fetched {len(all_records)} / {target} records")
        time.sleep(RATE_LIMIT_DELAY)

    return all_records[:target]


def save_json(records: list[dict], filepath: str) -> None:
    """Write records to a JSON file and create a compressed zip alongside it."""
    with open(filepath, "w") as f:
        json.dump(records, f, indent=2)

    zip_path = filepath.replace(".json", ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(filepath, os.path.basename(filepath))

    print(f"Saved {len(records)} records to {filepath}")
    print(f"Compressed to {zip_path}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, "adverse_events.json")

    records = fetch_adverse_events()
    save_json(records, filepath)


if __name__ == "__main__":
    main()
