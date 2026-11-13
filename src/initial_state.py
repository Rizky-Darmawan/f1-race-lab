"""Build the driver grid as it stands when a replay begins."""

from dataclasses import dataclass
from datetime import UTC, datetime

from src.historical.interval import Interval, IntervalData
from src.historical.lap import Lap, LapData
from src.historical.position import PositionData
from src.reference.driver import DriverData
from src.reference.starting_grid import StartingGrid, StartingGridData


@dataclass
class LiveGrid:
    """Driver grid information throughout the session."""

    driver_number: int
    driver_name: str
    position: int
    interval: float
    lap: int


class InitialState:
    """Driver grid at the moment the replay clock starts."""

    def __init__(self, session_key: int, start: datetime) -> None:
        self._session_key = session_key
        self._start = start if start.tzinfo is not None else start.replace(tzinfo=UTC)

    def _latest_by_driver(self, rows: list[Interval | Lap]) -> dict[int, Interval | Lap]:
        latest: dict[int, tuple[datetime, Interval | Lap]] = {}
        for row in rows:
            raw_date = row.date if isinstance(row, Interval) else row.date_start
            row_date = datetime.fromisoformat(raw_date)
            if row_date.tzinfo is None:
                row_date = row_date.replace(tzinfo=UTC)
            if row_date > self._start:
                continue
            current = latest.get(row.driver_number)
            if current is None or row_date >= current[0]:
                latest[row.driver_number] = (row_date, row)
        return {driver_number: row for driver_number, (_, row) in latest.items()}

    def _get_grid(self) -> list[StartingGrid]:
        positions = PositionData(self._session_key).construct_positions_from_api()
        return StartingGridData(self._session_key, positions).create_latest_grid_position(
            self._start.isoformat(timespec="microseconds")
        )

    def _get_driver_names(self) -> dict[int, str]:
        return {
            driver.driver_number: driver.full_name
            for driver in DriverData(self._session_key).construct_drivers_from_api()
        }

    def _get_intervals(self) -> dict[int, float]:
        latest = self._latest_by_driver(
            IntervalData(self._session_key).construct_intervals_from_api()
        )
        return {
            driver_number: row.interval
            for driver_number, row in latest.items()
            if isinstance(row, Interval)
        }

    def _get_laps(self) -> dict[int, int]:
        latest = self._latest_by_driver(LapData(self._session_key).construct_laps_from_api())
        return {
            driver_number: row.lap_number
            for driver_number, row in latest.items()
            if isinstance(row, Lap)
        }

    def create(self) -> dict[int, LiveGrid]:
        """Return each driver's state at the replay start, keyed by driver number.

        Driver names and the starting order come from the reference session.
        Interval, lap, and race position use the newest historical row at or
        before the start. A driver with no interval or lap yet starts at zero.
        """
        grid = self._get_grid()
        driver_names = self._get_driver_names()
        intervals = self._get_intervals()
        laps = self._get_laps()
        live_grid: dict[int, LiveGrid] = {}
        for row in grid:
            live_grid[row.driver_number] = LiveGrid(
                driver_number=row.driver_number,
                driver_name=driver_names[row.driver_number],
                position=row.position,
                interval=intervals.get(row.driver_number, 0.0),
                lap=laps.get(row.driver_number, 0),
            )
        return live_grid
