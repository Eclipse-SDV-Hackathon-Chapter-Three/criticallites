import json
import paho.mqtt.client as mqtt

# Load configuration
with open("mqtt_config.json") as f:
    config = json.load(f)

broker = config["broker"]
port = config["port"]
keepalive = config.get("keepalive", 60)
topic = config["topics"]["vehicle_parameters"]

# Track previous CruiseControl state
previous_cruise_control = None

# Callback when a message is received
def on_message(client, userdata, message):
    global previous_cruise_control
    
    try:
        data = json.loads(message.payload.decode())
        print(f"Received message on {message.topic}: {json.dumps(data, indent=2)}")
        
        # Check CruiseControl status
        current_cruise_control = data.get("CruiseControl", False)
        speed = data.get("Speed", 0)
        
        # Print specific messages based on CruiseControl state changes
        if current_cruise_control and previous_cruise_control != current_cruise_control:
            print(f"Cruise Control active. Speed: {speed}")
        elif not current_cruise_control and previous_cruise_control == True:
            print("Cruise Control deactivated.")
        
        # Update previous state
        previous_cruise_control = current_cruise_control
        
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
