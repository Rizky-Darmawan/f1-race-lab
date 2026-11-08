"""Load OpenF1 position rows for one session."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class Position:
    """Event on when driver position changes, marked by date."""

    date: str
    driver_number: int
    meeting_key: int
    position: int
    session_key: int


class PositionData:
    """Wrapper for the OpenF1 position endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/position?session_key={session_key}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_positions_from_api(self) -> list[Position]:
        """Fetch the session intervals and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Position(
                date=data["date"],
                driver_number=data["driver_number"],
                meeting_key=data["meeting_key"],
                position=data["position"],
                session_key=data["session_key"],
            )
            results.append(result)
        return results
