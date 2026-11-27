"""Load OpenF1 race control rows for one session."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class RaceControl:
    """One race-control message, such as a flag, safety car, or incident."""

    category: str
    date: str
    driver_number: int | None
    flag: str | None
    lap_number: int | None
    meeting_key: int
    message: str
    qualifying_phase: int | None
    scope: str
    sector: int | None
    session_key: int


class RaceControlData:
    """Wrapper for the OpenF1 race control endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/race_control?session_key={session_key}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_race_controls_from_api(self) -> list[RaceControl]:
        """Fetch the session race-control messages and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = RaceControl(
                category=data["category"],
                date=data["date"],
                driver_number=data["driver_number"],
                flag=data["flag"],
                lap_number=data["lap_number"],
                meeting_key=data["meeting_key"],
                message=data["message"],
                qualifying_phase=data["qualifying_phase"],
                scope=data["scope"],
                sector=data["sector"],
                session_key=data["session_key"],
            )
            results.append(result)
        return results
