from datetime import UTC, datetime, timedelta

import pytest

from src.historical import LapHistorical

START = datetime(2026, 3, 29, 6, 0, tzinfo=UTC)
START_ISO = "2026-03-29T06:00:00+00:00"


@pytest.fixture
def laps() -> LapHistorical:
    return LapHistorical(0)


@pytest.fixture
def finished_lap() -> dict:
    return {
        "driver_number": 1,
        "date_start": START_ISO,
        "duration_sector_1": 30.0,
        "duration_sector_2": 40.0,
        "duration_sector_3": 25.0,
        "segments_sector_1": [1],
        "segments_sector_2": [2],
        "segments_sector_3": [3],
        "lap_duration": 100.0,
    }


def test_latest_empty(laps: LapHistorical) -> None:
    """Return an empty list when no lap rows are given."""
    assert laps.get_latest_data_for_each_driver([]) == []


def test_latest_keeps_later_lap_for_one_driver(laps: LapHistorical) -> None:
    """Keep the lap with the later start time for a single driver."""
    early = {"driver_number": 44, "date_start": "2026-03-29T06:00:00+00:00", "lap_number": 1}
    late = {"driver_number": 44, "date_start": "2026-03-29T06:02:00+00:00", "lap_number": 2}
    assert laps.get_latest_data_for_each_driver([early, late]) == [late]


def test_latest_keeps_each_driver_in_first_seen_order(laps: LapHistorical) -> None:
    """Keep each driver's latest lap in the order that driver was first seen."""
    first_early = {"driver_number": 1, "date_start": "2026-03-29T06:00:00+00:00", "lap_number": 1}
    second = {"driver_number": 16, "date_start": "2026-03-29T06:01:00+00:00", "lap_number": 3}
    first_late = {"driver_number": 1, "date_start": "2026-03-29T06:01:30+00:00", "lap_number": 2}
    latest = laps.get_latest_data_for_each_driver([first_early, second, first_late])
    assert latest == [first_late, second]


def test_latest_equal_date_keeps_first_row(laps: LapHistorical) -> None:
    """Keep the first row when two laps share the same start time."""
    first = {"driver_number": 4, "date_start": "2026-03-29T06:00:00+00:00", "lap_number": 1}
    second = {"driver_number": 4, "date_start": "2026-03-29T06:00:00+00:00", "lap_number": 2}
    latest = laps.get_latest_data_for_each_driver([first, second])
    assert latest == [first]
    assert latest[0] is first


def test_latest_skips_invalid_rows_and_keeps_driver_zero(laps: LapHistorical) -> None:
    """Skip rows with no driver or a non-string start time, and keep driver 0."""
    missing_driver = {"date_start": "2026-03-29T06:00:00+00:00"}
    bad_date = {"driver_number": 10, "date_start": None}
    zero = {"driver_number": 0, "date_start": "2026-03-29T06:00:00+00:00"}
    assert laps.get_latest_data_for_each_driver([missing_driver, bad_date, zero]) == [zero]


def test_latest_does_not_mutate_input(laps: LapHistorical) -> None:
    """Leave the input list and its lap rows unchanged."""
    row = {"driver_number": 1, "date_start": "2026-03-29T06:00:00+00:00", "lap_number": 1}
    data = [row]
    laps.get_latest_data_for_each_driver(data)
    assert data == [row]
    assert data[0] is row
    assert row == {"driver_number": 1, "date_start": "2026-03-29T06:00:00+00:00", "lap_number": 1}


def _tick(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


@pytest.mark.parametrize(
    ("seconds", "kept_sectors", "lap_kept"),
    [
        (0, (), False),
        (30, (1,), False),
        (50, (1,), False),
        (95, (1, 2, 3), False),
        (100, (1, 2, 3), True),
    ],
)
def test_mask_clears_splits_still_in_the_future(
    laps: LapHistorical,
    finished_lap: dict,
    seconds: float,
    kept_sectors: tuple[int, ...],
    lap_kept: bool,
) -> None:
    """Clear sector and lap timings that have not been reached at the tick."""
    masked = laps.mask_unfinished_timings(finished_lap, _tick(seconds))
    for sector in (1, 2, 3):
        if sector in kept_sectors:
            assert masked[f"duration_sector_{sector}"] == finished_lap[f"duration_sector_{sector}"]
            assert masked[f"segments_sector_{sector}"] == [sector]
        else:
            assert masked[f"duration_sector_{sector}"] is None
            assert masked[f"segments_sector_{sector}"] is None
    if lap_kept:
        assert masked["lap_duration"] == 100.0
    else:
        assert masked["lap_duration"] is None


def test_mask_broken_chain_keeps_later_sectors(laps: LapHistorical, finished_lap: dict) -> None:
    """Leave later sectors unchanged when an earlier sector duration is missing."""
    finished_lap["duration_sector_2"] = None
    before_lap = laps.mask_unfinished_timings(finished_lap, _tick(50))
    at_lap = laps.mask_unfinished_timings(finished_lap, _tick(100))
    assert before_lap["duration_sector_1"] == 30.0
    assert before_lap["duration_sector_2"] is None
    assert before_lap["segments_sector_2"] == [2]
    assert before_lap["duration_sector_3"] == 25.0
    assert before_lap["segments_sector_3"] == [3]
    assert before_lap["lap_duration"] is None
    assert at_lap["duration_sector_2"] is None
    assert at_lap["segments_sector_2"] == [2]
    assert at_lap["duration_sector_3"] == 25.0
    assert at_lap["segments_sector_3"] == [3]
    assert at_lap["lap_duration"] == 100.0


def test_mask_bool_duration_breaks_the_chain(laps: LapHistorical, finished_lap: dict) -> None:
    """Treat a boolean sector duration as missing and leave later sectors unchanged."""
    finished_lap["duration_sector_2"] = True
    masked = laps.mask_unfinished_timings(finished_lap, _tick(50))
    assert masked["duration_sector_1"] == 30.0
    assert masked["duration_sector_2"] is True
    assert masked["segments_sector_2"] == [2]
    assert masked["duration_sector_3"] == 25.0
    assert masked["segments_sector_3"] == [3]


def test_mask_non_string_date_start_leaves_timings(laps: LapHistorical, finished_lap: dict) -> None:
    """Leave timings unchanged when the lap start time is not a string."""
    finished_lap["date_start"] = None
    masked = laps.mask_unfinished_timings(finished_lap, _tick(0))
    assert masked["duration_sector_1"] == 30.0
    assert masked["segments_sector_1"] == [1]
    assert masked["duration_sector_2"] == 40.0
    assert masked["duration_sector_3"] == 25.0
    assert masked["lap_duration"] == 100.0
    assert masked is not finished_lap


def test_mask_does_not_mutate_original_row(laps: LapHistorical, finished_lap: dict) -> None:
    """Return a masked copy and leave the original lap row unchanged."""
    original = {
        "duration_sector_1": 30.0,
        "duration_sector_2": 40.0,
        "duration_sector_3": 25.0,
        "segments_sector_1": [1],
        "segments_sector_2": [2],
        "segments_sector_3": [3],
        "lap_duration": 100.0,
    }
    laps.mask_unfinished_timings(finished_lap, _tick(0))
    assert {key: finished_lap[key] for key in original} == original
