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

# Load payload from data.json file
with open("data.json") as f:
    payload = json.load(f)
print("Loaded payload from data.json")

# Create MQTT client
client = mqtt.Client()
client.connect(broker, port, keepalive)
client.loop_start()  # Start network loop

# Variables for speed control
speed = payload.get("Speed", 0)
direction = 1  # 1 = increasing, -1 = decreasing

try:
    while True:
        # Update speed
        speed += 5 * direction

        # Reverse direction if limits reached
        if speed >= 100:
            direction = -1
        elif speed <= 0:
            direction = 1

        # Update payload
        payload["Speed"] = speed

        # Publish updated payload
        client.publish(topic, json.dumps(payload))
        print(f"Published Speed={speed} to {topic}")

        time.sleep(1)  # Wait 1 second

except KeyboardInterrupt:
    print("\nStopped by user")

finally:
    client.loop_stop()
    client.disconnect()