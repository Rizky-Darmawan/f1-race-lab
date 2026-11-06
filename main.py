from datetime import UTC, datetime

from src.historical.interval import IntervalData
from src.historical.lap import LapData
from src.simulation import LiveSimulation

if __name__ == "__main__":
    historical_interval = IntervalData(11253).construct_intervals_from_api()
    historical_laps = LapData(11253).construct_laps_from_api()
    simulator = LiveSimulation(historical_interval, historical_laps)
    start_date = datetime(2026, 3, 29, 5, 45, 0, tzinfo=UTC)
    simulator.run_clock(start_date)
