"""Load OpenF1 starting grid for one session as reference data."""

import json
from dataclasses import dataclass, replace
from datetime import datetime
from urllib.request import urlopen

from src.historical.position import Position


@dataclass
class StartingGrid:
    """Initial starting grid for the session."""

    position: int
    driver_number: int
    lap_duration: float
    meeting_key: int
    session_key: int


class StartingGridData:
    """Wrapper for the OpenF1 starting grid endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/starting_grid?session_key={session_key}"
    _SESSIONS_URL = "https://api.openf1.org/v1/sessions"

    def __init__(self, session_key: int, position_data: list[Position]) -> None:
        self._session_key = session_key
        self._position_data = position_data

    def _get_quali_session_key(self) -> int:
        """Return the qualifying session that sets the grid for this meeting."""
        session_url = f"{self._SESSIONS_URL}?session_key={self._session_key}"
        response = urlopen(session_url).read().decode("utf-8")
        meeting_key = json.loads(response)[0]["meeting_key"]
        quali_url = f"{self._SESSIONS_URL}?meeting_key={meeting_key}&session_name=Qualifying"
        response = urlopen(quali_url).read().decode("utf-8")
        return json.loads(response)[0]["session_key"]

    def _get_initial_starting_grid(self) -> list[StartingGrid]:
        """Fetch the session intervals and return them in API order."""
        url = self._BASE_URL.format(session_key=self._get_quali_session_key())
        response = urlopen(url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = StartingGrid(
                position=data["position"],
                driver_number=data["driver_number"],
                lap_duration=data["lap_duration"],
                meeting_key=data["meeting_key"],
                session_key=data["session_key"],
            )
            results.append(result)
        return results

    def _get_latest_position_by_driver(self, date: str) -> list[Position]:
        cutoff = datetime.fromisoformat(date)
        latest: dict[int, tuple[datetime, Position]] = {}
        for row in self._position_data:
            row_date = datetime.fromisoformat(row.date)
            if row_date > cutoff:
                continue
            current = latest.get(row.driver_number)
            if current is None or row_date >= current[0]:
                latest[row.driver_number] = (row_date, row)
        ordered = sorted(
            latest.values(), key=lambda item: (item[1].position, item[1].driver_number)
        )
        return [row for _, row in ordered]

    def create_latest_grid_position(self, date: str) -> list[StartingGrid]:
        """Get the latest grid position based on given timestamp."""
        latest_by_driver = {
            row.driver_number: row.position for row in self._get_latest_position_by_driver(date)
        }
        updated: list[StartingGrid] = []
        for grid_row in self._get_initial_starting_grid():
            position = latest_by_driver.get(grid_row.driver_number)
            if position is None:
                updated.append(grid_row)
                continue
            updated.append(replace(grid_row, position=position))
        updated.sort(key=lambda row: (row.position, row.driver_number))
        return updated
