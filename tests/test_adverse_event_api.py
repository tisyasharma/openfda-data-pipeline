import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from adverse_event_api import AdverseEventAPI


@pytest.fixture(scope="module")
def api():
    """Shared API instance for the test module, requires loaded data in MongoDB."""
    client = AdverseEventAPI()
    yield client
    client.close()


def test_get_events_by_drug_returns_results(api):
    """Querying a common drug should return at least one result."""
    results = api.get_events_by_drug("aspirin")
    assert len(results) > 0
    assert "safetyreportid" in results[0]


def test_get_events_by_drug_serious_filter(api):
    """With serious_only=True, every result should have serious='1'."""
    results = api.get_events_by_drug("aspirin", serious_only=True, limit=50)
    for r in results:
        assert r["serious"] == "1"


def test_get_events_by_drug_respects_limit(api):
    results = api.get_events_by_drug("aspirin", limit=3)
    assert len(results) <= 3


def test_get_reaction_frequency_structure(api):
    """Each result should have an _id (reaction name) and a count."""
    results = api.get_reaction_frequency("metformin", top_n=5)
    for r in results:
        assert isinstance(r["_id"], str)
        assert isinstance(r["count"], int)
        assert r["count"] > 0


def test_get_demographic_breakdown_by_sex(api):
    """Sex codes should be in the known set: 0 (unknown), 1 (male), 2 (female)."""
    results = api.get_demographic_breakdown(group_by="sex")
    assert len(results) > 0
    valid_codes = {"0", "1", "2", None}
    for r in results:
        assert r["_id"] in valid_codes


def test_get_demographic_breakdown_by_country(api):
    results = api.get_demographic_breakdown(group_by="country")
    assert len(results) > 0
    # US should be one of the top reporting countries
    countries = [r["_id"] for r in results]
    assert "US" in countries


def test_get_top_drugs_sorted_descending(api):
    """Results should come back in descending order of event count."""
    results = api.get_top_drugs_by_event_count(top_n=10)
    assert len(results) > 0
    counts = [r["event_count"] for r in results]
    assert counts == sorted(counts, reverse=True)


def test_get_top_drugs_serious_only(api):
    results = api.get_top_drugs_by_event_count(serious_only=True, top_n=5)
    assert len(results) > 0
