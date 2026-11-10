"""Load OpenF1 starting grid for one session as reference data."""

import json
from dataclasses import dataclass
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
    """Wrapper for the OpenF1 intervals endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/starting_grid?session_key={session_key}"

    def __init__(self, session_key: int, position_data: list[Position]) -> None:
        self._session_key = session_key
        self._position_data = position_data
        self._url = self._BASE_URL.format(session_key=session_key)

    def _get_initial_starting_grid(self) -> list[StartingGrid]:
        """Fetch the session intervals and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
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
