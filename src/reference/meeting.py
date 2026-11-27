"""Load OpenF1 meeting rows as reference data."""

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass
class Meeting:
    """One Grand Prix or testing weekend."""

    circuit_key: int
    circuit_info_url: str
    circuit_image: str
    circuit_short_name: str
    circuit_type: str
    country_code: str
    country_flag: str
    country_key: int
    country_name: str
    date_end: str
    date_start: str
    gmt_offset: str
    is_cancelled: bool
    location: str
    meeting_key: int
    meeting_name: str
    meeting_official_name: str
    year: int


class MeetingData:
    """Wrapper for the OpenF1 meetings endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/meetings?meeting_key={meeting_key}"

    def __init__(self, meeting_key: int) -> None:
        self._meeting_key = meeting_key
        self._url = self._BASE_URL.format(meeting_key=meeting_key)

    def construct_meetings_from_api(self) -> list[Meeting]:
        """Fetch the meetings and return them in API order."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Meeting(
                circuit_key=data["circuit_key"],
                circuit_info_url=data["circuit_info_url"],
                circuit_image=data["circuit_image"],
                circuit_short_name=data["circuit_short_name"],
                circuit_type=data["circuit_type"],
                country_code=data["country_code"],
                country_flag=data["country_flag"],
                country_key=data["country_key"],
                country_name=data["country_name"],
                date_end=data["date_end"],
                date_start=data["date_start"],
                gmt_offset=data["gmt_offset"],
                is_cancelled=data["is_cancelled"],
                location=data["location"],
                meeting_key=data["meeting_key"],
                meeting_name=data["meeting_name"],
                meeting_official_name=data["meeting_official_name"],
                year=data["year"],
            )
            results.append(result)
        return results
