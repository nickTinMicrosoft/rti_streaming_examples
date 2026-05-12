# Setting Up Azure IoT Hub

This guide walks you through creating an **Azure IoT Hub**, registering **devices**, and obtaining **device connection strings** needed by the train IoT Hub simulator (`trains/trains_iothub.py`).

---

## When to Use IoT Hub vs Event Hub

| Feature | IoT Hub | Event Hub |
|---------|---------|-----------|
| **Best for** | Per-device identity, device management, cloud-to-device messaging | High-throughput event ingestion from apps/services |
| **Authentication** | Per-device connection string or certificate | Shared Access Signature (namespace or hub level) |
| **Used by** | `trains/trains_iothub.py` | All other simulators in this repo |
| **Fabric integration** | Via built-in Event Hub–compatible endpoint | Direct Eventstream connection |

> **For this demo**, the train simulator has both an Event Hub version and an IoT Hub version. Use whichever matches the scenario you want to demonstrate.

---

## Step 1 — Create an IoT Hub

1. Go to the [Azure Portal](https://portal.azure.com).
2. Click **+ Create a resource** → search for **IoT Hub** → click **Create**.
3. Fill in the basics:

   | Field | Value |
   |-------|-------|
   | **Subscription** | Your Azure subscription |
   | **Resource Group** | Same group as your Event Hub (e.g., `rg-fabric-rti-demo`) |
   | **IoT Hub Name** | Something unique (e.g., `iothub-rti-demo-<yourname>`) |
   | **Region** | Same region as your Fabric workspace |
   | **Tier** | **Free** (8,000 messages/day — fine for demos) or **Standard S1** |

4. Click **Review + Create** → **Create**.
5. Wait for deployment, then click **Go to resource**.

---

## Step 2 — Register Devices

The IoT Hub train simulator uses 3 devices — one per train line. Register each one:

| Device ID | Used For |
|-----------|----------|
| `red-line` | Red line train |
| `blue-line` | Blue line train |
| `green-line` | Green line train |

For each device:

1. In your IoT Hub, click **Devices** in the left menu.
2. Click **+ Add Device**.
3. Enter the **Device ID** from the table above.
4. Leave **Authentication type** as **Symmetric key**.
5. Leave **Auto-generate keys** checked.
6. Click **Save**.

---

## Step 3 — Get Device Connection Strings

1. In **Devices**, click on the device (e.g., `red-line`).
2. Copy the **Primary connection string**. It looks like:

   ```
   HostName=iothub-rti-demo-yourname.azure-devices.net;DeviceId=red-line;SharedAccessKey=YOUR_KEY_HERE
   ```

3. Repeat for all 3 devices.

---

## Step 4 — Configure Your `.env` File

Add the device connection strings to your `.env` file:

```
IOT_RED_LINE_CONN_STR=HostName=iothub-rti-demo-yourname.azure-devices.net;DeviceId=red-line;SharedAccessKey=YOUR_KEY_HERE
IOT_BLUE_LINE_CONN_STR=HostName=iothub-rti-demo-yourname.azure-devices.net;DeviceId=blue-line;SharedAccessKey=YOUR_KEY_HERE
IOT_GREEN_LINE_CONN_STR=HostName=iothub-rti-demo-yourname.azure-devices.net;DeviceId=green-line;SharedAccessKey=YOUR_KEY_HERE
```

---

## Step 5 — Connect IoT Hub to Fabric Eventstream

IoT Hub has a **built-in Event Hub–compatible endpoint** that Fabric Eventstream can consume from.

### Get the Built-In Endpoint

1. In your IoT Hub, click **Built-in endpoints** in the left menu.
2. Under **Event Hub-compatible endpoint**, copy:
   - **Event Hub-compatible name** (e.g., `iothub-ehub-iothub-rt-12345-abcdef`)
   - **Event Hub-compatible endpoint** (starts with `sb://...`)
3. You'll also need the **Shared access policy** — by default, use the `service` policy:
   - Go to **Shared access policies** → click **service** → copy the **Primary connection string**.

### Create the Eventstream in Fabric

1. In your Fabric workspace, click **+ New item** → **Eventstream**.
2. Name it: `es-train-iothub`
3. Click **New source** → **Azure IoT Hub**.
4. Configure:
   - **IoT Hub connection string**: Paste the **service** policy connection string.
   - **Consumer group**: `$Default`
   - **Data format**: JSON
5. Add a **destination** (KQL Database, Lakehouse, etc.) as needed.
6. Click **Publish**.

---

## Verify

Run the IoT Hub simulator:

```bash
cd trains
pip install -r requirements.txt
python trains_iothub.py
```

You should see train telemetry printing to the console. Check the IoT Hub **Overview** page to see message counts increasing.

---

## Alternative: Create Devices with Azure CLI

If you prefer the command line:

```bash
# Create the IoT Hub
az iot hub create \
  --name iothub-rti-demo-yourname \
  --resource-group rg-fabric-rti-demo \
  --sku F1 \
  --partition-count 2

# Register devices
az iot hub device-identity create --hub-name iothub-rti-demo-yourname --device-id red-line
az iot hub device-identity create --hub-name iothub-rti-demo-yourname --device-id blue-line
az iot hub device-identity create --hub-name iothub-rti-demo-yourname --device-id green-line

# Get connection strings
az iot hub device-identity connection-string show --hub-name iothub-rti-demo-yourname --device-id red-line --output tsv
az iot hub device-identity connection-string show --hub-name iothub-rti-demo-yourname --device-id blue-line --output tsv
az iot hub device-identity connection-string show --hub-name iothub-rti-demo-yourname --device-id green-line --output tsv
```

---

## Clean Up

```bash
az group delete --name rg-fabric-rti-demo --yes --no-wait
```

---

[← Back to main README](../README.md)
