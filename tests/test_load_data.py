import json
import os
import sys
import tempfile

import pytest
from pymongo import MongoClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import MONGO_CONFIG, DB_NAME, COLLECTION_NAME, JSON_FILE
from load_data import load_adverse_events, INDEXES

SAMPLE_RECORDS = [
    {
        "safetyreportid": f"TEST-{i}",
        "serious": "1",
        "receivedate": "20230601",
        "primarysource": {"reportercountry": "US", "qualification": "1"},
        "patient": {
            "patientsex": "2",
            "reaction": [{"reactionmeddrapt": "HEADACHE"}],
            "drug": [
                {
                    "medicinalproduct": "ASPIRIN",
                    "openfda": {"generic_name": ["ASPIRIN"]},
                }
            ],
        },
    }
    for i in range(10)
]


@pytest.fixture
def sample_json():
    """Write sample records to a temp JSON file, clean up after."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(SAMPLE_RECORDS, f)
        filepath = f.name

    yield filepath
    os.unlink(filepath)


@pytest.fixture(scope="module", autouse=True)
def restore_collection():
    """Reload the real dataset after load tests finish."""
    yield
    if os.path.exists(JSON_FILE):
        load_adverse_events(JSON_FILE)


def test_insert_count(sample_json):
    """Verify that all records from the JSON file are inserted."""
    count = load_adverse_events(sample_json)
    assert count == len(SAMPLE_RECORDS)

    client = MongoClient(**MONGO_CONFIG)
    actual = client[DB_NAME][COLLECTION_NAME].count_documents({})
    client.close()
    assert actual == len(SAMPLE_RECORDS)


def test_indexes_created(sample_json):
    """Verify that all expected indexes exist after loading."""
    load_adverse_events(sample_json)

    client = MongoClient(**MONGO_CONFIG)
    index_info = client[DB_NAME][COLLECTION_NAME].index_information()
    client.close()

    indexed_fields = set()
    for idx in index_info.values():
        for field, _ in idx["key"]:
            indexed_fields.add(field)

    for field in INDEXES:
        assert field in indexed_fields, f"Missing index on {field}"


def test_idempotent_reload(sample_json):
    """Loading twice should not double the record count."""
    load_adverse_events(sample_json)
    load_adverse_events(sample_json)

    client = MongoClient(**MONGO_CONFIG)
    actual = client[DB_NAME][COLLECTION_NAME].count_documents({})
    client.close()
    assert actual == len(SAMPLE_RECORDS)
