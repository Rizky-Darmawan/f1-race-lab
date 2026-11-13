from config import SESSION_KEY, START
from src.historical.interval import IntervalData
from src.historical.lap import LapData
from src.historical.position import PositionData
from src.simulation.live_simulation import HistoricalPayload, LiveSimulation

SPEED = 2

if __name__ == "__main__":
    interval = IntervalData(SESSION_KEY).construct_intervals_from_api()
    lap = LapData(SESSION_KEY).construct_laps_from_api()
    position = PositionData(SESSION_KEY).construct_positions_from_api()
    payload = HistoricalPayload(interval, lap, position)
    simulator = LiveSimulation(payload)
    simulator.run_clock(START, SPEED)
