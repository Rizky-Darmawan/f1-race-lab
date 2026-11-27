"""Tests for expanding one finished stint into a snapshot per lap."""

from dataclasses import replace

import pytest

from src.historical.stint import Stint, _StintExploder


def _stint(**overrides: object) -> Stint:
    stint = Stint(
        compound="SOFT",
        driver_number=1,
        lap_end=28,
        lap_start=12,
        meeting_key=1,
        session_key=2,
        stint_number=1,
        tyre_age_at_start=0,
    )
    return replace(stint, **overrides)


@pytest.fixture
def exploder() -> _StintExploder:
    return _StintExploder()


def test_explode_adds_one_snapshot_per_lap_before_the_end(exploder: _StintExploder) -> None:
    """Add lap_end - lap_start snapshots before the historical row."""
    events = exploder.explode(_stint())
    assert len(events) == (28 - 12) + 1
    assert [event.lap_end for event in events] == list(range(12, 29))
    assert all(event.lap_start == 12 for event in events)
    assert all(event.compound == "SOFT" for event in events)
    assert all(event.tyre_age_at_start == 0 for event in events)


def test_explode_one_lap_stint_stays_one_snapshot(exploder: _StintExploder) -> None:
    """Keep a stint whose start and end lap match as a single snapshot."""
    events = exploder.explode(_stint(lap_start=12, lap_end=12))
    assert [event.lap_end for event in events] == [12]


def test_explode_missing_lap_end_publishes_the_appearance(exploder: _StintExploder) -> None:
    """Publish the appearance snapshot when the stint has not recorded an end."""
    events = exploder.explode(_stint(lap_end=None))
    assert [event.lap_end for event in events] == [12]


def test_explode_does_not_mutate_source(exploder: _StintExploder) -> None:
    """Leave the source stint unchanged."""
    stint = _stint()
    original = replace(stint)
    exploder.explode(stint)
    assert stint == original
