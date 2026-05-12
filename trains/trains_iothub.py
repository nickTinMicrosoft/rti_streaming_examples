# NYC Metro Train Telemetry Simulator — IoT Hub Version
# Sends 3 simulated trains (Red, Blue, Green) to Azure IoT Hub
# Each train is a registered IoT device with its own connection string

import os
import json
import random
import time
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
from azure.iot.device import IoTHubDeviceClient, Message

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ===============================
# DEVICE CONNECTION STRINGS
# ===============================
RED_CONN = os.getenv("IOT_RED_LINE_CONN_STR")
BLUE_CONN = os.getenv("IOT_BLUE_LINE_CONN_STR")
GREEN_CONN = os.getenv("IOT_GREEN_LINE_CONN_STR")


# ===============================
# NYC ROUTES
# ===============================
RED_LINE = [
    (40.7506, -73.9935),
    (40.7527, -73.9772),
    (40.7580, -73.9855),
    (40.7681, -73.9819),
]

BLUE_LINE = [
    (40.7061, -74.0086),
    (40.7128, -74.0060),
    (40.7195, -74.0019),
    (40.7282, -73.9942),
]

GREEN_LINE = [
    (40.7420, -73.9925),
    (40.7484, -73.9857),
    (40.7549, -73.9840),
    (40.7612, -73.9776),
]


def interpolate(p1, p2, step):
    lat = p1[0] + (p2[0] - p1[0]) * step
    lon = p1[1] + (p2[1] - p1[1]) * step
    return lat, lon


class TrainSimulator:
    def __init__(self, name, conn_str, route, allow_delay=False):
        self.name = name
        self.client = IoTHubDeviceClient.create_from_connection_string(conn_str)
        self.route = route
        self.allow_delay = allow_delay
        self.segment = 0
        self.progress = 0

    def run(self):
        self.client.connect()

        while True:
            start = self.route[self.segment]
            end = self.route[(self.segment + 1) % len(self.route)]

            self.progress += random.uniform(0.05, 0.15)

            if self.progress >= 1:
                self.segment = (self.segment + 1) % len(self.route)
                self.progress = 0

                # simulate station delay
                if self.allow_delay and random.random() < 0.35:
                    delay = random.randint(15, 35)

                    payload = {
                        "trainId": self.name,
                        "status": "Delayed",
                        "speed": 0,
                        "lat": start[0],
                        "lon": start[1],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    self.send(payload)

                    print(f"{self.name} delayed {delay}s")
                    time.sleep(delay)

            lat, lon = interpolate(start, end, self.progress)

            payload = {
                "trainId": self.name,
                "line": self.name.split("-")[1],
                "lat": lat,
                "lon": lon,
                "speed": random.randint(20, 55),
                "status": "OnTime",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self.send(payload)

            time.sleep(random.uniform(5, 10))

    def send(self, payload):
        msg = Message(json.dumps(payload))
        self.client.send_message(msg)
        print(payload)


# ===============================
# START TRAINS
# ===============================
if __name__ == "__main__":
    trains = [
        TrainSimulator("train-red-1", RED_CONN, RED_LINE),
        TrainSimulator("train-blue-2", BLUE_CONN, BLUE_LINE),
        TrainSimulator("train-green-3", GREEN_CONN, GREEN_LINE, True),
    ]

    print("Train Telemetry Simulator (IoT Hub) Starting...")
    print("=" * 55)

    threads = [threading.Thread(target=t.run, daemon=True) for t in trains]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
