"""Tests for the latest position held by each driver at a given time."""

from src.historical.position import Position
from src.historical.starting_grid import StartingGridData


def _position(date: str, driver_number: int, position: int) -> Position:
    return Position(
        date=date,
        driver_number=driver_number,
        meeting_key=1,
        position=position,
        session_key=2,
    )


def test_latest_position_keeps_one_row_per_driver_at_or_before_date() -> None:
    """Keep the newest row for each driver that is not after the cutoff."""
    positions = [
        _position("2026-03-29T06:00:00+00:00", driver_number=1, position=1),
        _position("2026-03-29T06:00:00+00:00", driver_number=44, position=2),
        _position("2026-03-29T06:01:00+00:00", driver_number=1, position=2),
        _position("2026-03-29T06:01:00+00:00", driver_number=44, position=1),
        _position("2026-03-29T06:02:00+00:00", driver_number=1, position=3),
    ]
    grid = StartingGridData(session_key=2, position_data=positions)
    mid_session = grid._get_latest_position_by_driver("2026-03-29T06:01:00+00:00")
    assert [(row.driver_number, row.position, row.date) for row in mid_session] == [
        (44, 1, "2026-03-29T06:01:00+00:00"),
        (1, 2, "2026-03-29T06:01:00+00:00"),
    ]
    at_end = grid._get_latest_position_by_driver("2026-03-29T06:02:00+00:00")
    assert [(row.driver_number, row.position, row.date) for row in at_end] == [
        (44, 1, "2026-03-29T06:01:00+00:00"),
        (1, 3, "2026-03-29T06:02:00+00:00"),
    ]


def test_latest_position_omits_drivers_with_no_row_yet() -> None:
    """Skip a driver whose first position change is still in the future."""
    positions = [
        _position("2026-03-29T06:02:00+00:00", driver_number=1, position=1),
        _position("2026-03-29T06:00:00+00:00", driver_number=44, position=2),
    ]
    grid = StartingGridData(session_key=2, position_data=positions)
    latest = grid._get_latest_position_by_driver("2026-03-29T06:01:00+00:00")
    assert [(row.driver_number, row.position, row.date) for row in latest] == [
        (44, 2, "2026-03-29T06:00:00+00:00"),
    ]
