"""Tests for applying live topics onto the driver grid."""

import json
from dataclasses import asdict

from src.historical.interval import Interval
from src.historical.lap import Lap
from src.historical.position import Position
from src.initial_state import LiveGrid
from src.subscriber import Subscriber


def _grid() -> dict[int, LiveGrid]:
    return {
        1: LiveGrid(
            driver_number=1,
            driver_name="Max Verstappen",
            position=2,
            interval=0.4,
            lap=3,
        ),
        44: LiveGrid(
            driver_number=44,
            driver_name="Lewis Hamilton",
            position=1,
            interval=0.0,
            lap=3,
        ),
    }


def _subscriber(grid: dict[int, LiveGrid]) -> Subscriber:
    return Subscriber("127.0.0.1", 1883, ["interval", "lap", "position"], grid)


def _lap(driver_number: int, lap_number: int) -> Lap:
    return Lap(
        date_start="2026-03-29T05:15:00+00:00",
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


def test_each_topic_updates_only_its_field_for_that_driver() -> None:
    """Join interval, lap, and position messages by driver number."""
    grid = _grid()
    subscriber = _subscriber(grid)
    subscriber._update_live_grid(
        "interval",
        json.dumps(
            asdict(
                Interval(
                    date="2026-03-29T05:15:00+00:00",
                    driver_number=1,
                    gap_to_leader=1.2,
                    interval=1.2,
                    meeting_key=1,
                    session_key=2,
                )
            )
        ).encode(),
    )
    subscriber._update_live_grid("lap", json.dumps(asdict(_lap(1, 5))).encode())
    subscriber._update_live_grid(
        "position",
        json.dumps(
            asdict(
                Position(
                    date="2026-03-29T05:15:00+00:00",
                    driver_number=44,
                    meeting_key=1,
                    position=3,
                    session_key=2,
                )
            )
        ).encode(),
    )
    assert grid[1] == LiveGrid(
        driver_number=1,
        driver_name="Max Verstappen",
        position=2,
        interval=1.2,
        lap=5,
    )
    assert grid[44] == LiveGrid(
        driver_number=44,
        driver_name="Lewis Hamilton",
        position=3,
        interval=0.0,
        lap=3,
    )


def test_unknown_driver_leaves_the_grid_unchanged() -> None:
    """A driver who is not already on the grid is not added."""
    grid = _grid()
    subscriber = _subscriber(grid)
    subscriber._update_live_grid(
        "position",
        json.dumps(
            asdict(
                Position(
                    date="2026-03-29T05:15:00+00:00",
                    driver_number=63,
                    meeting_key=1,
                    position=4,
                    session_key=2,
                )
            )
        ).encode(),
    )
    assert list(grid) == [1, 44]


def test_missing_interval_does_not_clear_the_current_gap() -> None:
    """A null gap leaves the driver's last numeric interval in place."""
    grid = _grid()
    subscriber = _subscriber(grid)
    payload = {
        "date": "2026-03-29T05:15:00+00:00",
        "driver_number": 1,
        "gap_to_leader": None,
        "interval": None,
        "meeting_key": 1,
        "session_key": 2,
    }
    subscriber._update_live_grid("interval", json.dumps(payload).encode())
    assert grid[1].interval == 0.4


def test_format_live_grid_shows_the_leaders_lap_and_gaps_behind() -> None:
    """Read like the timing tower: one lap from position 1, gaps for the rest."""
    grid = _grid()
    grid[1].lap = 9
    grid[1].interval = 0.8
    text = _subscriber(grid)._format_live_grid(grid, "2026-03-29T05:14:04+00:00")
    assert json.loads(text) == {
        "at": "2026-03-29T05:14:04+00:00",
        "lap": 3,
        "rows": [
            {
                "position": 1,
                "driver_number": 44,
                "driver_name": "Lewis Hamilton",
                "interval": None,
            },
            {
                "position": 2,
                "driver_number": 1,
                "driver_name": "Max Verstappen",
                "interval": 0.8,
            },
        ],
    }
