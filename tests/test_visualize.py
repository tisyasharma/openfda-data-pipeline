import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from adverse_event_api import AdverseEventAPI
from visualize import plot_route_death_rates


@pytest.fixture(scope="module")
def api():
    client = AdverseEventAPI()
    yield client
    client.close()


def test_chart_file_created(api):
    """Running the visualization pipeline should produce a PNG file."""
    results = api.get_death_rate_by_route(min_reports=20)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test_chart.png")
        plot_route_death_rates(results, output_path)
        assert os.path.exists(output_path)


def test_chart_file_not_empty(api):
    """The generated PNG should have a non-zero file size."""
    results = api.get_death_rate_by_route(min_reports=20)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test_chart.png")
        plot_route_death_rates(results, output_path)
        assert os.path.getsize(output_path) > 0
