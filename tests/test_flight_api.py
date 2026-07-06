import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flight_api"))

import pytest
import time
from flight_api import FlightAPI, PLANE_MODES


@pytest.fixture
def fc():
    """Fresh FlightAPI connection per test."""
    api = FlightAPI()
    api.connect()
    yield api
    api.disconnect()


def test_connect(fc):
    assert fc.master is not None
    assert fc.master.target_system > 0


def test_get_state(fc):
    state = fc.get_state()
    assert "position" in state
    assert "attitude" in state
    assert "velocity" in state
    assert "mode" in state


def test_position_values_sane(fc):
    pos = fc.get_position()
    assert -90 <= pos["lat"] <= 90
    assert -180 <= pos["lon"] <= 180
    assert 0 <= pos["heading_deg"] <= 360


def test_set_mode_validates_input(fc):
    with pytest.raises(ValueError):
        fc.set_mode("NOT_A_REAL_MODE")


def test_set_mode_changes_mode(fc):
    fc.set_mode("LOITER")
    time.sleep(2)
    assert fc.get_mode() == "LOITER"