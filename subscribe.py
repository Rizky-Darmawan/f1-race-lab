from config import SESSION_KEY, START
from src.initial_state import InitialState
from src.subscriber import Subscriber

HOST = "127.0.0.1"
PORT = 1883
TOPICS = ["interval", "lap", "position"]

if __name__ == "__main__":
    live_grid = InitialState(SESSION_KEY, START).create()
    print(live_grid)
    subscriber = Subscriber(HOST, PORT, TOPICS, live_grid)
    subscriber.run()
