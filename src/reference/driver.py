"""Load OpenF1 driver for one session as reference data."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class Driver:
    """Driver reference row for one session."""

    broadcast_name: str
    driver_number: int
    first_name: str
    full_name: str
    headshot_url: str
    last_name: str
    meeting_key: int
    name_acronym: str
    session_key: int
    team_colour: str
    team_name: str


class DriverData:
    """Wrapper for the OpenF1 drivers endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/drivers?session_key={session_key}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_drivers_from_api(self) -> list[Driver]:
        """Fetch the session drivers and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Driver(
                broadcast_name=data["broadcast_name"],
                driver_number=data["driver_number"],
                first_name=data["first_name"],
                full_name=data["full_name"],
                headshot_url=data["headshot_url"],
                last_name=data["last_name"],
                meeting_key=data["meeting_key"],
                name_acronym=data["name_acronym"],
                session_key=data["session_key"],
                team_colour=data["team_colour"],
                team_name=data["team_name"],
            )
            results.append(result)
        return results
