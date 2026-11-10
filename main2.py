from datetime import UTC, datetime

from src.subscriber import Subscriber

HOST = "127.0.0.1"
PORT = 1883
TOPICS = ["interval", "lap", "position"]
SESSION_KEY = 11253
START = datetime(2026, 3, 29, 5, 14, 0, tzinfo=UTC)

if __name__ == "__main__":
    subscriber = Subscriber(HOST, PORT, TOPICS)
    subscriber.get_latest_grid_state(SESSION_KEY, START)
    subscriber.run()
