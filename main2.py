from src.subscriber import Subscriber

HOST = "127.0.0.1"
PORT = 1883
TOPICS = ["interval", "lap", "position"]

if __name__ == "__main__":
    Subscriber(HOST, PORT, TOPICS).run()
