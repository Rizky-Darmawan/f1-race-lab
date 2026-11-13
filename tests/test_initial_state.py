"""Tests for the driver grid at the replay start."""

from datetime import UTC, datetime

from src.historical.interval import Interval, IntervalData
from src.historical.lap import Lap, LapData
from src.historical.position import Position, PositionData
from src.initial_state import InitialState, LiveGrid
from src.reference.driver import Driver, DriverData
from src.reference.starting_grid import StartingGrid, StartingGridData


def _position(date: str, driver_number: int, position: int) -> Position:
    return Position(
        date=date,
        driver_number=driver_number,
        meeting_key=1,
        position=position,
        session_key=2,
    )


def _grid_row(position: int, driver_number: int, lap_duration: float) -> StartingGrid:
    return StartingGrid(
        position=position,
        driver_number=driver_number,
        lap_duration=lap_duration,
        meeting_key=1,
        session_key=2,
    )


def _driver(driver_number: int, full_name: str) -> Driver:
    return Driver(
        broadcast_name=full_name,
        driver_number=driver_number,
        first_name="",
        full_name=full_name,
        headshot_url="",
        last_name="",
        meeting_key=1,
        name_acronym="",
        session_key=2,
        team_colour="",
        team_name="",
    )


def _interval(date: str, driver_number: int, interval: float) -> Interval:
    return Interval(
        date=date,
        driver_number=driver_number,
        gap_to_leader=interval,
        interval=interval,
        meeting_key=1,
        session_key=2,
    )


def _lap(date_start: str, driver_number: int, lap_number: int) -> Lap:
    return Lap(
        date_start=date_start,
        driver_number=driver_number,
        duration_sector_1=None,
        duration_sector_2=None,
        duration_sector_3=None,
        i1_speed=None,
        i2_speed=None,
        is_pit_out_lap=False,
        lap_duration=None,
        lap_number=lap_number,
        meeting_key=1,
        segments_sector_1=None,
        segments_sector_2=None,
        segments_sector_3=None,
        session_key=2,
        st_speed=None,
    )


def test_grid_state_uses_positions_at_replay_start(monkeypatch) -> None:
    """Apply position changes from before the start and leave later ones alone."""
    positions = [
        _position("2026-03-29T05:00:00+00:00", driver_number=1, position=1),
        _position("2026-03-29T05:00:00+00:00", driver_number=44, position=2),
        _position("2026-03-29T05:10:00+00:00", driver_number=1, position=2),
        _position("2026-03-29T05:10:00+00:00", driver_number=44, position=1),
        _position("2026-03-29T06:00:00+00:00", driver_number=1, position=1),
        _position("2026-03-29T06:00:00+00:00", driver_number=44, position=2),
    ]
    initial = [
        _grid_row(position=1, driver_number=1, lap_duration=70.1),
        _grid_row(position=2, driver_number=44, lap_duration=70.4),
    ]
    monkeypatch.setattr(PositionData, "construct_positions_from_api", lambda self: positions)
    monkeypatch.setattr(StartingGridData, "_get_initial_starting_grid", lambda self: initial)
    monkeypatch.setattr(
        DriverData,
        "construct_drivers_from_api",
        lambda self: [_driver(1, "Max Verstappen"), _driver(44, "Lewis Hamilton")],
    )
    monkeypatch.setattr(IntervalData, "construct_intervals_from_api", lambda self: [])
    monkeypatch.setattr(LapData, "construct_laps_from_api", lambda self: [])
    live = InitialState(11253, datetime(2026, 3, 29, 5, 14, 0, tzinfo=UTC)).create()
    assert [(row.driver_number, row.position) for row in live.values()] == [
        (44, 1),
        (1, 2),
    ]


def test_live_grid_joins_reference_and_latest_history_by_driver(monkeypatch) -> None:
    """Use session reference data, and historical rows only from before the replay start."""
    positions = [
        _position("2026-03-29T05:10:00+00:00", driver_number=1, position=2),
        _position("2026-03-29T05:10:00+00:00", driver_number=44, position=1),
        _position("2026-03-29T06:00:00+00:00", driver_number=1, position=1),
    ]
    initial = [
        _grid_row(position=1, driver_number=1, lap_duration=70.1),
        _grid_row(position=2, driver_number=44, lap_duration=70.4),
        _grid_row(position=3, driver_number=63, lap_duration=70.9),
    ]
    drivers = [
        _driver(1, "Max Verstappen"),
        _driver(44, "Lewis Hamilton"),
        _driver(63, "George Russell"),
    ]
    intervals = [
        _interval("2026-03-29T05:10:00+00:00", driver_number=1, interval=0.4),
        _interval("2026-03-29T05:14:00+00:00", driver_number=1, interval=0.8),
        _interval("2026-03-29T05:12:00+00:00", driver_number=44, interval=0.0),
        _interval("2026-03-29T06:00:00+00:00", driver_number=1, interval=2.0),
    ]
    laps = [
        _lap("2026-03-29T05:05:00+00:00", driver_number=1, lap_number=2),
        _lap("2026-03-29T05:13:00+00:00", driver_number=1, lap_number=4),
        _lap("2026-03-29T06:00:00+00:00", driver_number=44, lap_number=9),
    ]
    monkeypatch.setattr(PositionData, "construct_positions_from_api", lambda self: positions)
    monkeypatch.setattr(StartingGridData, "_get_initial_starting_grid", lambda self: initial)
    monkeypatch.setattr(DriverData, "construct_drivers_from_api", lambda self: drivers)
    monkeypatch.setattr(IntervalData, "construct_intervals_from_api", lambda self: intervals)
    monkeypatch.setattr(LapData, "construct_laps_from_api", lambda self: laps)
    live = InitialState(11253, datetime(2026, 3, 29, 5, 14, 0, tzinfo=UTC)).create()
    assert list(live) == [44, 1, 63]
    assert live[44] == LiveGrid(
        driver_number=44,
        driver_name="Lewis Hamilton",
        position=1,
        interval=0.0,
        lap=0,
    )
    assert live[1].driver_name == "Max Verstappen"
    assert live[1].position == 2
    assert live[1].interval == 0.8
    assert live[1].lap == 4
    assert live[63].driver_name == "George Russell"
    assert live[63].position == 3
    assert live[63].interval == 0.0
    assert live[63].lap == 0
