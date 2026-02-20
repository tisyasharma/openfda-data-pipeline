import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fetch_data import fetch_adverse_events, save_json

EXPECTED_KEYS = {"safetyreportid", "patient", "serious"}


def test_fetch_small_batch():
    """Pull a small batch and verify each record has the expected top-level keys."""
    records = fetch_adverse_events(target=5)
    assert len(records) > 0
    for record in records:
        assert EXPECTED_KEYS.issubset(record.keys())


def test_json_file_written():
    """Fetch a few records, save to JSON, verify the file is valid."""
    records = fetch_adverse_events(target=3)
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_events.json")
        save_json(records, filepath)

        assert os.path.exists(filepath)
        with open(filepath) as f:
            loaded = json.load(f)
        assert len(loaded) == len(records)


def test_zip_file_created():
    """Verify a zip archive is created alongside the JSON file."""
    records = fetch_adverse_events(target=3)
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_events.json")
        save_json(records, filepath)

        zip_path = filepath.replace(".json", ".zip")
        assert os.path.exists(zip_path)
        assert os.path.getsize(zip_path) > 0
