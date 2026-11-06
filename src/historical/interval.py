"""Load OpenF1 interval rows for one session."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class Interval:
    """Gap to the leader and the car ahead at one timestamp."""

    date: str
    driver_number: int
    gap_to_leader: float
    interval: float
    meeting_key: int
    session_key: int


class IntervalData:
    """Wrapper for the OpenF1 intervals endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/intervals?session_key={session_key}&driver_number=1"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_intervals_from_api(self) -> list[Interval]:
        """Fetch the session intervals and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Interval(
                date=data["date"],
                driver_number=data["driver_number"],
                gap_to_leader=data["gap_to_leader"],
                interval=data["interval"],
                meeting_key=data["meeting_key"],
                session_key=data["session_key"],
            )
            results.append(result)
        return results
