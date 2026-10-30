from datetime import UTC, datetime

from src.simulation import LiveSimulation

if __name__ == "__main__":
    simulator = LiveSimulation(11253)
    start_date = datetime(2026, 3, 29, 5, 14, 2, tzinfo=UTC)
    simulator.run_clock(start_date)
