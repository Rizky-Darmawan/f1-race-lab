"""Load OpenF1 stints and expand each stint into one snapshot per lap."""

import json
from dataclasses import dataclass, replace
from urllib.request import urlopen


@dataclass
class Stint:
    """One live snapshot of a tyre run.

    ``lap_end`` is the lap this snapshot has reached. On the first snapshot it
    equals ``lap_start``. Later snapshots advance it once per completed lap.
    """

    compound: str
    driver_number: int
    lap_end: int | None
    lap_start: int
    meeting_key: int
    session_key: int
    stint_number: int
    tyre_age_at_start: int


class _StintExploder:
    """Explode one finished stint into a snapshot for every lap it covers.

    The live feed publishes the stint when it appears, with ``lap_end`` equal
    to ``lap_start``, then again each time a later lap is completed. A stint
    from lap 12 through lap 28 therefore yields 17 snapshots, 16 of them added
    to the historical row. A stint with no ``lap_end`` yields only the
    appearance snapshot.
    """

    def explode(self, stint: Stint) -> list[Stint]:
        """Return one snapshot per lap from ``lap_start`` through ``lap_end``."""
        lap_end = stint.lap_start if stint.lap_end is None else stint.lap_end
        if lap_end < stint.lap_start:
            return [replace(stint)]
        return [replace(stint, lap_end=lap) for lap in range(stint.lap_start, lap_end + 1)]


class StintData:
    """Wrapper for the OpenF1 stints endpoint."""

    _BASE_URL = "https://api.openf1.org/v1/stints?session_key={session_key}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key
        self._url = self._BASE_URL.format(session_key=session_key)

    def construct_stints_from_api(self) -> list[Stint]:
        """Fetch stints and return a snapshot for each lap the stint covers."""
        response = urlopen(self._url).read().decode("utf-8")
        datas = json.loads(response)
        results = []
        for data in datas:
            result = Stint(
                compound=data["compound"],
                driver_number=data["driver_number"],
                lap_end=data["lap_end"],
                lap_start=data["lap_start"],
                meeting_key=data["meeting_key"],
                session_key=data["session_key"],
                stint_number=data["stint_number"],
                tyre_age_at_start=data["tyre_age_at_start"],
            )
            results.extend(_StintExploder().explode(result))
        return results
