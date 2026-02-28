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
    """
    Fetches adverse event records from the OpenFDA API in batches until we hit
    the target count. If we get rate limited, we wait and retry. Stops early
    if the API has no more results to return.

    Args:
        target: total number of records to collect across all pages
    """
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
    """
    Saves the records to a JSON file and creates a zipped copy at the same location.

    Args:
        records: list of adverse event report dicts to write out
        filepath: path to write the JSON file — the zip is saved to the same path with a .zip extension
    """
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
