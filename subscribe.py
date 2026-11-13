from config import SESSION_KEY, START
from src.subscriber import Subscriber

HOST = "127.0.0.1"
PORT = 1883
TOPICS = ["interval", "lap", "position"]

if __name__ == "__main__":
    subscriber = Subscriber(HOST, PORT, TOPICS)
    subscriber.get_latest_grid_state(SESSION_KEY, START)
    subscriber.run()
