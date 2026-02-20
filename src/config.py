import os

MONGO_CONFIG = {
    "host": "localhost",
    "port": 27017,
}

DB_NAME = "openfda"
COLLECTION_NAME = "adverse_events"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
JSON_FILE = os.path.join(DATA_DIR, "adverse_events.json")
