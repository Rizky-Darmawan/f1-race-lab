"""Load OpenF1 session rows as reference data."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class Session:
    """One practice, qualifying, sprint, or race session."""

    circuit_key: int
    circuit_short_name: str
    country_code: str
    country_key: int
    country_name: str
    date_end: str
    date_start: str
    gmt_offset: str
    is_cancelled: bool
    location: str
    meeting_key: int
    session_key: int
    session_name: str
    session_type: str
    year: int


class SessionData:
    """Wrapper for the OpenF1 sessions endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/sessions?session_key={session_key}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_sessions_from_api(self) -> list[Session]:
        """Fetch the sessions and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Session(
                circuit_key=data["circuit_key"],
                circuit_short_name=data["circuit_short_name"],
                country_code=data["country_code"],
                country_key=data["country_key"],
                country_name=data["country_name"],
                date_end=data["date_end"],
                date_start=data["date_start"],
                gmt_offset=data["gmt_offset"],
                is_cancelled=data["is_cancelled"],
                location=data["location"],
                meeting_key=data["meeting_key"],
                session_key=data["session_key"],
                session_name=data["session_name"],
                session_type=data["session_type"],
                year=data["year"],
            )
            results.append(result)
        return results
