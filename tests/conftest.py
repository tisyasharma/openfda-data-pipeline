import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import JSON_FILE
from load_data import load_adverse_events


@pytest.fixture(scope="session", autouse=True)
def ensure_data_loaded():
    """Load the dataset into MongoDB before the test session begins."""
    if os.path.exists(JSON_FILE):
        load_adverse_events(JSON_FILE)
