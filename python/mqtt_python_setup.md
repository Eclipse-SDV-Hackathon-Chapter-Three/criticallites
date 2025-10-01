# MQTT Python Publisher & Subscriber Setup

This document details the setup and implementation of a Python-based MQTT publisher and subscriber using a configuration file. The goal is to have a **publisher send JSON data** to a topic and a **subscriber continuously listen** to that topic.

---

## 1. Prerequisites

1. **Python 3.x** installed on your system.
2. **Paho MQTT library** for Python:
   ```bash
   pip install paho-mqtt
   ```
3. **A running MQTT broker**, e.g., [Mosquitto](https://mosquitto.org/):
   ```bash
   sudo apt install mosquitto
   sudo systemctl enable mosquitto
   sudo systemctl start mosquitto
   ```
4. A text editor or IDE to create Python and JSON files.

---

## 2. Create MQTT Configuration File

Create a file named `mqtt_config.json` with the following content:

```json
{
  "broker": "localhost",
  "port": 1883,
  "keepalive": 60,
  "topics": {
    "vehicle_parameters": "vehicle/parameters"
  }
}
```

**Explanation of fields:**

| Field       | Description                                     |
|-------------|-------------------------------------------------|
| broker      | Address of the MQTT broker (localhost if local)|
| port        | Broker port (default 1883)                     |
| keepalive   | Keepalive interval in seconds                  |
| topics      | Dictionary of topic names used in scripts      |

---

## 3. Create Publisher Script (`publisher.py`)

This script sends a JSON payload to the `vehicle/parameters` topic.

```python
import json
import time
import paho.mqtt.client as mqtt

# Load configuration
with open("mqtt_config.json") as f:
    config = json.load(f)

broker = config["broker"]
port = config["port"]
keepalive = config.get("keepalive", 60)
topic = config["topics"]["vehicle_parameters"]

# Sample JSON payload
payload = {
    "AmbientTemperature": 22,
    "Battery": 80,
    "CruiseControl": False,
    "Economy": "Normal",
    "EngineTemperature": 90
}

# Create MQTT client
client = mqtt.Client()

# Connect to broker
client.connect(broker, port, keepalive)

# Publish the payload
client.loop_start()  # Start network loop
client.publish(topic, json.dumps(payload))
print(f"Published to topic {topic}: {json.dumps(payload)}")
time.sleep(1)  # Wait to ensure message is sent
client.loop_stop()
client.disconnect()
```

---

## 4. Create Subscriber Script (`subscriber.py`)

This script listens continuously on the `vehicle/parameters` topic.

```python
import json
import paho.mqtt.client as mqtt

# Load configuration
with open("mqtt_config.json") as f:
    config = json.load(f)

broker = config["broker"]
port = config["port"]
keepalive = config.get("keepalive", 60)
topic = config["topics"]["vehicle_parameters"]

# Callback when a message is received
def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        print(f"Received message on {message.topic}: {json.dumps(data, indent=2)}")
    except json.JSONDecodeError:
        print(f"Received non-JSON message: {message.payload}")

# Create MQTT client
client = mqtt.Client()
client.on_message = on_message

# Connect and subscribe
client.connect(broker, port, keepalive)
client.subscribe(topic)
print(f"Subscribed to topic: {topic}")

# Keep listening
client.loop_forever()
```

---

## 5. Execution Steps

1. **Start the MQTT broker** (if not already running):
   ```bash
   sudo systemctl start mosquitto
   ```
2. **Run the subscriber**:
   ```bash
   python subscriber.py
   ```
3. **Run the publisher** in a separate terminal:
   ```bash
   python publisher.py
   ```
4. **Observe the subscriber output**:
   ```
   Received message on vehicle/parameters: {
     "AmbientTemperature": 22,
     "Battery": 80,
     "CruiseControl": false,
     "Economy": "Normal",
     "EngineTemperature": 90
   }
   ```

---

## 6. Optional Enhancements

1. Continuous publishing at regular intervals:

```python
while True:
    client.publish(topic, json.dumps(payload))
    time.sleep(5)  # publish every 5 seconds
```

2. Add multiple topics to `mqtt_config.json` for expanded vehicle data.
3. Implement QoS (`client.publish(topic, payload, qos=1)`) for guaranteed delivery.

---

This setup is **fully modular**, allowing easy expansion by adding topics or modifying JSON payloads via the configuration file.

