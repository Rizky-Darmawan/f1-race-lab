"""Tests for the latest position held by each driver at a given time."""

from src.historical.position import Position
from src.historical.starting_grid import StartingGrid, StartingGridData


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


def _grid_row(position: int, driver_number: int, lap_duration: float) -> StartingGrid:
    return StartingGrid(
        position=position,
        driver_number=driver_number,
        lap_duration=lap_duration,
        meeting_key=1,
        session_key=2,
    )


def test_create_latest_grid_position_uses_race_order_and_keeps_lap_time() -> None:
    """Apply the latest race position to each starter and keep the qualifying lap."""
    positions = [
        _position("2026-03-29T06:00:00+00:00", driver_number=1, position=1),
        _position("2026-03-29T06:00:00+00:00", driver_number=44, position=2),
        _position("2026-03-29T06:01:00+00:00", driver_number=1, position=2),
        _position("2026-03-29T06:01:00+00:00", driver_number=44, position=1),
        _position("2026-03-29T06:01:00+00:00", driver_number=81, position=4),
    ]
    grid = StartingGridData(session_key=2, position_data=positions)
    initial = [
        _grid_row(position=1, driver_number=1, lap_duration=70.1),
        _grid_row(position=2, driver_number=44, lap_duration=70.4),
        _grid_row(position=3, driver_number=63, lap_duration=70.9),
    ]
    grid._get_initial_starting_grid = lambda: initial
    before_race = grid.create_latest_grid_position("2026-03-29T05:00:00+00:00")
    assert [(row.driver_number, row.position, row.lap_duration) for row in before_race] == [
        (1, 1, 70.1),
        (44, 2, 70.4),
        (63, 3, 70.9),
    ]
    mid_race = grid.create_latest_grid_position("2026-03-29T06:01:00+00:00")
    assert [(row.driver_number, row.position, row.lap_duration) for row in mid_race] == [
        (44, 1, 70.4),
        (1, 2, 70.1),
        (63, 3, 70.9),
    ]
