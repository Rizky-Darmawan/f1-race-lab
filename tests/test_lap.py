"""Tests for expanding one finished lap into live sector events."""

from dataclasses import replace

import pytest

from src.historical.lap import Lap, _LapExploder

START = "2026-03-29T06:00:00+00:00"
SECTOR_2_START = "2026-03-29T06:00:30.000000+00:00"
SECTOR_3_START = "2026-03-29T06:01:10.000000+00:00"
LAP_END = "2026-03-29T06:01:40.000000+00:00"


def _lap(**overrides: object) -> Lap:
    """Some test mutates properties, this function is needed to build new Lap for each tests"""
    lap = Lap(
        date_start=START,
        driver_number=1,
        duration_sector_1=30.0,
        duration_sector_2=40.0,
        duration_sector_3=25.0,
        i1_speed=280,
        i2_speed=290,
        is_pit_out_lap=False,
        lap_duration=100.0,
        lap_number=3,
        meeting_key=1,
        segments_sector_1=[1],
        segments_sector_2=[2],
        segments_sector_3=[3],
        session_key=2,
        st_speed=300,
    )
    return replace(lap, **overrides)


@pytest.fixture
def finished_lap() -> Lap:
    return _lap()


@pytest.fixture
def exploder() -> _LapExploder:
    return _LapExploder()


def test_explode_complete_lap(exploder: _LapExploder, finished_lap: Lap) -> None:
    """Return 4 elements (lap start, sector starts, and lap end) with the correct timings."""
    events = exploder.explode(finished_lap)
    assert len(events) == 4
    lap_start, sector_2, sector_3, lap_end = events
    assert lap_start.date_start == START
    assert lap_start.duration_sector_1 is None
    assert lap_start.duration_sector_2 is None
    assert lap_start.duration_sector_3 is None
    assert lap_start.lap_duration is None
    assert sector_2.date_start == SECTOR_2_START
    assert sector_2.duration_sector_1 == 30.0
    assert sector_2.duration_sector_2 is None
    assert sector_2.duration_sector_3 is None
    assert sector_2.lap_duration is None
    assert sector_3.date_start == SECTOR_3_START
    assert sector_3.duration_sector_1 == 30.0
    assert sector_3.duration_sector_2 == 40.0
    assert sector_3.duration_sector_3 is None
    assert sector_3.lap_duration is None
    assert lap_end.date_start == LAP_END
    assert lap_end.duration_sector_1 == 30.0
    assert lap_end.duration_sector_2 == 40.0
    assert lap_end.duration_sector_3 == 25.0
    assert lap_end.lap_duration == 100.0


def test_explode_does_not_mutate_source(exploder: _LapExploder, finished_lap: Lap) -> None:
    """Leave the source lap unchanged."""
    original = replace(finished_lap)
    exploder.explode(finished_lap)
    assert finished_lap == original


@pytest.mark.parametrize("missing", [None, True])
def test_missing_sector_1_drops_sector_starts(
    exploder: _LapExploder,
    missing: None | bool,
) -> None:
    """Drop the sector 2 and sector 3 events when sector 1 has no duration."""
    events = exploder.explode(_lap(duration_sector_1=missing))
    assert [event.date_start for event in events] == [START, LAP_END]
    assert events[0].lap_duration is None
    assert events[1].lap_duration == 100.0


@pytest.mark.parametrize("missing", [None, True])
def test_missing_sector_2_drops_sector_3_start(
    exploder: _LapExploder,
    missing: None | bool,
) -> None:
    """Drop only the sector 3 event when sector 2 has no duration."""
    events = exploder.explode(_lap(duration_sector_2=missing))
    assert [event.date_start for event in events] == [START, SECTOR_2_START, LAP_END]
    assert events[1].duration_sector_1 == 30.0
    assert events[1].duration_sector_2 is None
    assert events[1].lap_duration is None


@pytest.mark.parametrize("missing", [None, True])
def test_missing_lap_duration_drops_lap_end(
    exploder: _LapExploder,
    missing: None | bool,
) -> None:
    """Drop the lap-end event when the lap duration is missing."""
    events = exploder.explode(_lap(lap_duration=missing))
    assert [event.date_start for event in events] == [START, SECTOR_2_START, SECTOR_3_START]
    assert events[-1].duration_sector_1 == 30.0
    assert events[-1].duration_sector_2 == 40.0
    assert events[-1].duration_sector_3 is None
    assert events[-1].lap_duration is None


@pytest.mark.parametrize(
    ("sector_1", "expected_date"),
    [
        (0.0000004, "2026-03-29T06:00:00.000000+00:00"),
        (0.0000006, "2026-03-29T06:00:00.000001+00:00"),
    ],
)
def test_fractional_duration_rounds_to_microsecond(
    exploder: _LapExploder,
    sector_1: float,
    expected_date: str,
) -> None:
    """Shift a fractional sector duration to the nearest microsecond."""
    events = exploder.explode(_lap(duration_sector_1=sector_1))
    sector_2 = events[1]
    assert sector_2.date_start == expected_date
    assert sector_2.duration_sector_1 == sector_1
