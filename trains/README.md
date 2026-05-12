# Train Telemetry Simulators

Streams simulated NYC metro train telemetry to Azure Event Hub or Azure IoT Hub for ingestion into Microsoft Fabric Real-Time Intelligence.

## Apps

| Script | Target | Description |
|--------|--------|-------------|
| `trains_eventhub.py` | Azure Event Hub | Sends train telemetry using a shared Event Hub producer |
| `trains_iothub.py` | Azure IoT Hub | Sends telemetry using per-device IoT Hub connections |

Both simulate 3 train lines (Red, Blue, Green) along realistic NYC routes. The Green line occasionally experiences station delays.

## Setup

```bash
cd trains
pip install -r requirements.txt
```

Add the appropriate variables to your `.env` file in the project root:

**For Event Hub version:**
```
EVENTHUB_TRAIN_CONN_STR=<your-connection-string>
EVENTHUB_TRAIN_NAME=metrotrain
```

**For IoT Hub version:**
```
IOT_RED_LINE_CONN_STR=<your-iot-hub-device-connection-string>
IOT_BLUE_LINE_CONN_STR=<your-iot-hub-device-connection-string>
IOT_GREEN_LINE_CONN_STR=<your-iot-hub-device-connection-string>
```

> The IoT Hub version requires 3 registered devices in your IoT Hub. See [docs/setup-iot-hub.md](../docs/setup-iot-hub.md).

## Run

```bash
# Event Hub version
python trains_eventhub.py

# IoT Hub version
python trains_iothub.py
```

Press `Ctrl+C` to stop.

## Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `trainId` | string | Train identifier (e.g., Train-Red-1) |
| `line` | string | Line name — Red, Blue, or Green |
| `lat` / `lon` | float | GPS coordinates along the route |
| `speed` | int | Ground speed (mph) |
| `status` | string | OnTime or Delayed |
| `timestamp` | string | UTC ISO 8601 |
