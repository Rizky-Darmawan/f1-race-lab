"""Load OpenF1 overtake rows for one session."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class Overtake:
    """One driver exchanging positions with another."""

    date: str
    meeting_key: int
    overtaken_driver_number: int
    overtaking_driver_number: int
    position: int
    session_key: int


class OvertakeData:
    """Wrapper for the OpenF1 overtakes endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/overtakes?session_key={session_key}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_overtakes_from_api(self) -> list[Overtake]:
        """Fetch the session overtakes and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Overtake(
                date=data["date"],
                meeting_key=data["meeting_key"],
                overtaken_driver_number=data["overtaken_driver_number"],
                overtaking_driver_number=data["overtaking_driver_number"],
                position=data["position"],
                session_key=data["session_key"],
            )
            results.append(result)
        return results
