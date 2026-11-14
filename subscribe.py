import uvicorn

from config import SESSION_KEY, START
from src.fastapi_app import create_app
from src.initial_state import InitialState
from src.subscriber import Subscriber

HOST = "127.0.0.1"
PORT = 1883
API_PORT = 8000
TOPICS = ["interval", "lap", "position"]

if __name__ == "__main__":
    live_grid = InitialState(SESSION_KEY, START).create()
    subscriber = Subscriber(HOST, PORT, TOPICS, live_grid)
    subscriber.publish_snapshot(START.isoformat())
    uvicorn.run(create_app(subscriber), host=HOST, port=API_PORT)
