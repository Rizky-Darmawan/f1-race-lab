"""Load OpenF1 pit rows for one session."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class Pit:
    """One car's pass through the pit lane.

    ``date`` is when the car leaves the pit lane. OpenF1 records the
    live-timing message time, which is published once ``lane_duration`` is
    known. Entry time is ``date`` minus ``lane_duration``.
    """

    date: str
    driver_number: int
    lane_duration: float
    lap_number: int
    meeting_key: int
    pit_duration: float
    session_key: int
    stop_duration: float | None


class PitData:
    """Wrapper for the OpenF1 pit endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/pit?session_key={session_key}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_pits_from_api(self) -> list[Pit]:
        """Fetch the session pit stops and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Pit(
                date=data["date"],
                driver_number=data["driver_number"],
                lane_duration=data["lane_duration"],
                lap_number=data["lap_number"],
                meeting_key=data["meeting_key"],
                pit_duration=data["pit_duration"],
                session_key=data["session_key"],
                stop_duration=data["stop_duration"],
            )
            results.append(result)
        return results
