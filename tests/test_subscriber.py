"""Tests for the subscriber grid at the replay start."""

from datetime import UTC, datetime

from src.historical.position import Position, PositionData
from src.reference.starting_grid import StartingGrid, StartingGridData
from src.subscriber import Subscriber


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
    subscriber = Subscriber("127.0.0.1", 1883, ["position"])
    grid = subscriber.get_latest_grid_state(11253, datetime(2026, 3, 29, 5, 14, 0, tzinfo=UTC))
    assert [(row.driver_number, row.position, row.lap_duration) for row in grid] == [
        (44, 1, 70.4),
        (1, 2, 70.1),
    ]
