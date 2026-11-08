from datetime import UTC, datetime

from src.historical.interval import IntervalData
from src.historical.lap import LapData
from src.historical.position import PositionData
from src.simulation import LiveSimulation, HistoricalPayload

if __name__ == "__main__":
    interval = IntervalData(11253).construct_intervals_from_api()
    lap = LapData(11253).construct_laps_from_api()
    position = PositionData(11253).construct_positions_from_api()
    payload = HistoricalPayload(interval, lap, position)
    simulator = LiveSimulation(payload)
    start_date = datetime(2026, 3, 29, 5, 14, 0, tzinfo=UTC)
    simulator.run_clock(start_date)
