# NYC Metro Train Telemetry Simulator — Event Hub Version
# Sends 3 simulated trains (Red, Blue, Green) to Azure Event Hub
# - Staggered sends (5-10 sec)
# - Realistic NYC lat/long routes
# - Green line occasionally delayed at stations

import os
import json
import random
import time
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
from azure.eventhub import EventHubProducerClient, EventData

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============================
# CONFIG
# ============================
EVENT_HUB_CONN_STR = os.getenv("EVENTHUB_TRAIN_CONN_STR")
EVENT_HUB_NAME = os.getenv("EVENTHUB_TRAIN_NAME", "metrotrain")

SEND_MIN_SECONDS = 5
SEND_MAX_SECONDS = 10

# ============================
# NYC ROUTES (approx real lines)
# ============================

RED_LINE = [
    (40.7506, -73.9935),  # Penn Station
    (40.7527, -73.9772),  # Grand Central
    (40.7580, -73.9855),  # Times Sq
    (40.7614, -73.9817),  # 57th St
    (40.7681, -73.9819),  # Columbus Circle
]

BLUE_LINE = [
    (40.7061, -74.0086),  # Wall St
    (40.7128, -74.0060),  # WTC
    (40.7195, -74.0019),  # Canal St
    (40.7282, -73.9942),  # Astor Place
    (40.7359, -73.9911),  # Union Sq
]

GREEN_LINE = [
    (40.7420, -73.9925),  # Flatiron
    (40.7484, -73.9857),  # Empire State
    (40.7549, -73.9840),  # Bryant Park
    (40.7612, -73.9776),  # Lexington
    (40.7687, -73.9680),  # Upper East
]

# ============================
# EVENT HUB
# ============================
producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONN_STR,
    eventhub_name=EVENT_HUB_NAME
)


def interpolate(p1, p2, step=0.05):
    lat = p1[0] + (p2[0] - p1[0]) * step
    lon = p1[1] + (p2[1] - p1[1]) * step
    return lat, lon


def send_event(payload):
    event_data_batch = producer.create_batch()
    event_data_batch.add(EventData(json.dumps(payload)))
    producer.send_batch(event_data_batch)


class TrainSimulator:
    def __init__(self, train_id, line_name, route, allow_delay=False):
        self.train_id = train_id
        self.line_name = line_name
        self.route = route
        self.allow_delay = allow_delay
        self.segment = 0
        self.progress = 0.0

    def run(self):
        while True:
            start = self.route[self.segment]
            end = self.route[(self.segment + 1) % len(self.route)]

            self.progress += random.uniform(0.05, 0.15)

            if self.progress >= 1:
                self.segment = (self.segment + 1) % len(self.route)
                self.progress = 0

                # simulate station stop
                if self.allow_delay and random.random() < 0.35:
                    delay = random.randint(15, 35)
                    self.send_status(start, "Delayed", speed=0)
                    print(f"{self.train_id} delayed {delay}s at station")
                    time.sleep(delay)

            lat, lon = interpolate(start, end, self.progress)

            speed = random.randint(20, 55)
            status = "OnTime"

            payload = {
                "trainId": self.train_id,
                "line": self.line_name,
                "lat": lat,
                "lon": lon,
                "speed": speed,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            send_event(payload)
            print(payload)

            time.sleep(random.uniform(SEND_MIN_SECONDS, SEND_MAX_SECONDS))

    def send_status(self, location, status, speed=0):
        payload = {
            "trainId": self.train_id,
            "line": self.line_name,
            "lat": location[0],
            "lon": location[1],
            "speed": speed,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        send_event(payload)


# ============================
# START TRAINS
# ============================
if __name__ == "__main__":
    train1 = TrainSimulator("Train-Red-1", "Red", RED_LINE)
    train2 = TrainSimulator("Train-Blue-2", "Blue", BLUE_LINE)
    train3 = TrainSimulator("Train-Green-3", "Green", GREEN_LINE, allow_delay=True)

    print("Train Telemetry Simulator (Event Hub) Starting...")
    print("=" * 55)

    threads = [
        threading.Thread(target=train1.run, daemon=True),
        threading.Thread(target=train2.run, daemon=True),
        threading.Thread(target=train3.run, daemon=True),
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
