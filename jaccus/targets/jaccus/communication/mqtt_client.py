"""
MQTT5 communication client for vehicle data publishing and command subscription.
"""

import json
import time
import threading
from typing import Optional, Callable, Dict, Any

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("WARNING: paho-mqtt not available. Install with: pip install paho-mqtt")

from ..vehicle.control import VehicleTelemetry
from ..core.config import Config


class MQTTClient:
    """MQTT5 client for publishing vehicle telemetry and receiving commands."""

    def __init__(self, vehicle, config_data=None):
        """Initialize MQTT client."""
        self.vehicle = vehicle
        self.telemetry = VehicleTelemetry(vehicle)
        self.client = None
        self.connected = False

        # Command callback for vehicle commands
        self.command_callback: Optional[Callable[[Dict[str, Any]], None]] = None

        # Configuration
        self.config = self._load_config(config_data)

        # Threading for async publishing
        self._publish_thread = None
        self._stop_publishing = threading.Event()
        self._publish_interval = self.config.get('publish_interval', 1.0)  # seconds

        # Last published data for avoiding redundant publishes
        self._last_published_data = {}

        # Initialize MQTT client if available
        if MQTT_AVAILABLE:
            self._initialize_client()
        else:
            print("MQTT client not available - using mock mode")

    def _load_config(self, config_data):
        """Load MQTT configuration."""
        default_config = {
            "broker": "localhost",
            "port": 1883,
            "keepalive": 60,
            "qos": 1,
            "topics": {
                "vehicle_parameters": "vehicle/parameters",
                "vehicle_commands": "vehicle/commands"
            },
            "publish_interval": 1.0,
            "client_id": f"jaccus_vehicle_{int(time.time())}"
        }

        if config_data:
            if isinstance(config_data, str):
                try:
                    with open(config_data, 'r') as f:
                        file_config = json.load(f)
                    default_config.update(file_config)
                except Exception as e:
                    print(f"Failed to load MQTT config file {config_data}: {e}")
            elif isinstance(config_data, dict):
                default_config.update(config_data)

        return default_config

    def _initialize_client(self):
        """Initialize MQTT client connection."""
        try:
            # Create MQTT client with protocol version 5
            self.client = mqtt.Client(
                client_id=self.config["client_id"],
                protocol=mqtt.MQTTv5
            )

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish

            # Connect to broker
            self.client.connect(
                self.config["broker"],
                self.config["port"],
                self.config["keepalive"]
            )

            # Start network loop
            self.client.loop_start()

            print(f"MQTT client initialized - connecting to {self.config['broker']}:{self.config['port']}")

        except Exception as e:
            print(f"Failed to initialize MQTT client: {e}")
            self.client = None

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for when client connects to broker."""
        if rc == 0:
            self.connected = True
            print("MQTT client connected successfully")

            # Subscribe to vehicle commands topic
            commands_topic = self.config["topics"]["vehicle_commands"]
            client.subscribe(commands_topic, qos=self.config["qos"])
            print(f"Subscribed to topic: {commands_topic}")

        else:
            print(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback for when client disconnects."""
        self.connected = False
        print("MQTT client disconnected")

    def _on_message(self, client, userdata, message):
        """Callback for received messages."""
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')

            print(f"Received MQTT message on {topic}: {payload}")

            # Handle vehicle commands
            if topic == self.config["topics"]["vehicle_commands"]:
                self._handle_vehicle_command(payload)

        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def _on_publish(self, client, userdata, mid):
        """Callback for when message is published."""
        # Optionally log successful publishes
        pass

    def _handle_vehicle_command(self, payload):
        """Handle incoming vehicle commands."""
        try:
            command_data = json.loads(payload)

            # Validate command structure
            if "command" not in command_data:
                print("Invalid command: missing 'command' field")
                return

            # Call registered command callback if available
            if self.command_callback:
                self.command_callback(command_data)
            else:
                print(f"No command callback registered for: {command_data}")

        except json.JSONDecodeError as e:
            print(f"Invalid JSON in vehicle command: {e}")
        except Exception as e:
            print(f"Error handling vehicle command: {e}")

    def set_command_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for handling vehicle commands."""
        self.command_callback = callback

    def publish_vehicle_data(self, additional_data=None):
        """Publish current vehicle telemetry data."""
        if not self.client or not self.connected:
            return False

        try:
            # Get current vehicle data
            location = self.telemetry.get_location()
            speed_kmh = self.telemetry.get_speed_kmh()
            speed_ms = self.telemetry.get_speed_ms()

            # Create vehicle parameters payload (matching the requested format)
            vehicle_data = {
                "AmbientTemperature": 22,  # Mock data - could be enhanced with actual sensors
                "Battery": 80,  # Mock data - could be enhanced with actual vehicle state
                "CruiseControl": False,  # Will be updated with actual ACC status
                "Economy": "Normal",  # Mock data
                "Engine Temperature": 90,  # Mock data
                "Gear": "D",  # Could be enhanced with actual gear state
                "RPM": 0.0,  # Mock data - could be calculated from speed
                "Range": 320,  # Mock data
                "ShareLocation": True,  # Mock data
                "Speed": round(speed_kmh, 1),
                "SpeedUnit": "km/h",
                "TemperatureUnit": 0,  # 0 = Celsius
                "TypeOfVehicle": 0,  # 0 = Car
                "Location": {
                    "x": round(location.x, 2),
                    "y": round(location.y, 2),
                    "z": round(location.z, 2)
                },
                "Timestamp": int(time.time() * 1000)  # Milliseconds
            }

            # Add additional data if provided (e.g., ACC status)
            if additional_data:
                vehicle_data.update(additional_data)

            # Only publish if data has changed significantly
            if self._should_publish(vehicle_data):
                topic = self.config["topics"]["vehicle_parameters"]
                payload = json.dumps(vehicle_data)

                result = self.client.publish(
                    topic,
                    payload,
                    qos=self.config["qos"]
                )

                # Update last published data
                self._last_published_data = vehicle_data.copy()

                return result.rc == mqtt.MQTT_ERR_SUCCESS

            return True  # No need to publish, but not an error

        except Exception as e:
            print(f"Failed to publish vehicle data: {e}")
            return False

    def _should_publish(self, current_data):
        """Check if data has changed enough to warrant publishing."""
        if not self._last_published_data:
            return True

        # Check for significant changes in key parameters
        speed_changed = abs(
            current_data.get("Speed", 0) -
            self._last_published_data.get("Speed", 0)
        ) > 0.5  # 0.5 km/h threshold

        cruise_changed = (
            current_data.get("CruiseControl") !=
            self._last_published_data.get("CruiseControl")
        )

        # Publish if key parameters changed or enough time passed
        time_threshold = 5.0  # Publish at least every 5 seconds
        time_passed = (
            current_data.get("Timestamp", 0) -
            self._last_published_data.get("Timestamp", 0)
        ) > (time_threshold * 1000)

        return speed_changed or cruise_changed or time_passed

    def start_continuous_publishing(self):
        """Start continuous publishing of vehicle data in background thread."""
        if self._publish_thread and self._publish_thread.is_alive():
            return  # Already running

        self._stop_publishing.clear()
        self._publish_thread = threading.Thread(
            target=self._publish_loop,
            daemon=True
        )
        self._publish_thread.start()
        print("Started MQTT continuous publishing")

    def stop_continuous_publishing(self):
        """Stop continuous publishing."""
        if self._publish_thread:
            self._stop_publishing.set()
            self._publish_thread.join(timeout=2.0)
            print("Stopped MQTT continuous publishing")

    def _publish_loop(self):
        """Background thread loop for continuous publishing."""
        while not self._stop_publishing.is_set():
            try:
                self.publish_vehicle_data()
                time.sleep(self._publish_interval)
            except Exception as e:
                print(f"Error in MQTT publish loop: {e}")
                time.sleep(self._publish_interval)

    def close(self):
        """Close MQTT client and cleanup resources."""
        try:
            self.stop_continuous_publishing()

            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                print("MQTT client closed")

        except Exception as e:
            print(f"Error closing MQTT client: {e}")


class MockMQTTClient:
    """Mock MQTT client for testing when MQTT is not available."""

    def __init__(self, vehicle, config_data=None):
        """Initialize mock client."""
        self.vehicle = vehicle
        self.telemetry = VehicleTelemetry(vehicle)
        self.command_callback = None
        print("Using mock MQTT client (paho-mqtt not available)")

    def set_command_callback(self, callback):
        """Mock set callback."""
        self.command_callback = callback

    def publish_vehicle_data(self, additional_data=None):
        """Mock publish - just print data occasionally."""
        try:
            speed_kmh = self.telemetry.get_speed_kmh()
            location = self.telemetry.get_location()

            # Only print occasionally to avoid spam
            if not hasattr(self, '_last_print') or time.time() - self._last_print > 3.0:
                print(f"MQTT Mock: Speed={speed_kmh:.1f} km/h, Location=({location.x:.1f}, {location.y:.1f})")
                if additional_data and additional_data.get('CruiseControl'):
                    print(f"MQTT Mock: ACC={additional_data.get('CruiseControl')}")
                self._last_print = time.time()

            return True
        except Exception:
            return False

    def start_continuous_publishing(self):
        """Mock start publishing."""
        print("MQTT Mock: Started continuous publishing")

    def stop_continuous_publishing(self):
        """Mock stop publishing."""
        print("MQTT Mock: Stopped continuous publishing")

    def close(self):
        """Mock close."""
        print("MQTT Mock: Client closed")


def create_mqtt_client(vehicle, config_data=None):
    """Factory function to create MQTT client with fallback to mock."""
    if MQTT_AVAILABLE:
        return MQTTClient(vehicle, config_data)
    else:
        return MockMQTTClient(vehicle, config_data)
