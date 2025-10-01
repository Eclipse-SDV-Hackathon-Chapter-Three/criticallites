#!/usr/bin/env python3
"""
Test MQTT subscriber that monitors JACCUS vehicle parameters.
This script demonstrates reading vehicle data published by JACCUS.
"""

import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime


class JACCUSDataMonitor:
    """Monitor JACCUS vehicle data via MQTT."""

    def __init__(self, config_file="mqtt_config.json"):
        # Load MQTT configuration
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found, using defaults")
            self.config = {
                "broker": "localhost",
                "port": 1883,
                "topics": {
                    "vehicle_parameters": "vehicle/parameters"
                }
            }

        # Data tracking
        self.last_data = None
        self.message_count = 0
        self.start_time = time.time()

        # MQTT client setup
        self.client = mqtt.Client(client_id="jaccus_data_monitor")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Connect to broker
        print(f"Connecting to MQTT broker at {self.config['broker']}:{self.config['port']}...")
        self.client.connect(
            self.config["broker"],
            self.config["port"],
            60
        )
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker successfully")

            # Subscribe to vehicle parameters topic
            topic = self.config["topics"]["vehicle_parameters"]
            client.subscribe(topic, qos=1)
            print(f"📡 Subscribed to topic: {topic}")
            print(f"🔄 Waiting for vehicle data...\n")

        else:
            print(f"❌ Failed to connect: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        print(f"🔌 Disconnected from MQTT broker (rc: {rc})")

    def _on_message(self, client, userdata, message):
        """Handle incoming vehicle data messages."""
        try:
            # Parse JSON data
            data = json.loads(message.payload.decode('utf-8'))
            self.message_count += 1

            # Display formatted data
            self._display_vehicle_data(data)

            # Track changes
            self._track_changes(data)

            self.last_data = data

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON received: {e}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")

    def _display_vehicle_data(self, data):
        """Display vehicle data in formatted way."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"[{timestamp}] Message #{self.message_count}")
        print("=" * 50)

        # Key parameters
        speed = data.get("Speed", 0)
        cruise_control = data.get("CruiseControl", False)
        gear = data.get("Gear", "Unknown")
        battery = data.get("Battery", 0)

        print(f"🚗 Speed: {speed} {data.get('SpeedUnit', 'km/h')}")
        print(f"⚙️  Gear: {gear}")
        print(f"🎯 Cruise Control: {'ON' if cruise_control else 'OFF'}")
        print(f"🔋 Battery: {battery}%")

        # Environmental data
        temp = data.get("AmbientTemperature", 0)
        engine_temp = data.get("Engine Temperature", 0)
        print(f"🌡️  Ambient Temperature: {temp}°C")
        print(f"🔥 Engine Temperature: {engine_temp}°C")

        # Location (if available)
        if "Location" in data:
            loc = data["Location"]
            print(f"📍 Location: ({loc.get('x', 0):.2f}, {loc.get('y', 0):.2f}, {loc.get('z', 0):.2f})")

        # Additional data
        economy = data.get("Economy", "Unknown")
        range_km = data.get("Range", 0)
        rpm = data.get("RPM", 0)

        print(f"💰 Economy Mode: {economy}")
        print(f"⛽ Range: {range_km} km")
        print(f"⚡ RPM: {rpm}")

        print()

    def _track_changes(self, current_data):
        """Track and highlight significant changes."""
        if self.last_data is None:
            return

        changes = []

        # Check for significant changes
        if abs(current_data.get("Speed", 0) - self.last_data.get("Speed", 0)) > 1.0:
            changes.append(f"Speed changed: {self.last_data.get('Speed', 0)} → {current_data.get('Speed', 0)}")

        if current_data.get("CruiseControl") != self.last_data.get("CruiseControl"):
            old_state = "ON" if self.last_data.get("CruiseControl") else "OFF"
            new_state = "ON" if current_data.get("CruiseControl") else "OFF"
            changes.append(f"Cruise Control: {old_state} → {new_state}")

        if current_data.get("Gear") != self.last_data.get("Gear"):
            changes.append(f"Gear changed: {self.last_data.get('Gear')} → {current_data.get('Gear')}")

        # Display changes
        if changes:
            print("🔄 CHANGES DETECTED:")
            for change in changes:
                print(f"   • {change}")
            print()

    def get_statistics(self):
        """Get monitoring statistics."""
        elapsed = time.time() - self.start_time
        rate = self.message_count / elapsed if elapsed > 0 else 0

        return {
            "messages_received": self.message_count,
            "elapsed_time": elapsed,
            "message_rate": rate,
            "last_data_time": datetime.now().isoformat() if self.last_data else None
        }

    def print_statistics(self):
        """Print monitoring statistics."""
        stats = self.get_statistics()

        print("\n" + "=" * 50)
        print("📊 MONITORING STATISTICS")
        print("=" * 50)
        print(f"Messages Received: {stats['messages_received']}")
        print(f"Elapsed Time: {stats['elapsed_time']:.1f} seconds")
        print(f"Message Rate: {stats['message_rate']:.2f} msg/sec")
        print(f"Last Data: {stats['last_data_time']}")
        print("=" * 50)

    def monitor(self, duration=None):
        """Start monitoring vehicle data."""
        print("🚀 Starting JACCUS vehicle data monitoring...")
        print("   Press Ctrl+C to stop\n")

        try:
            if duration:
                print(f"⏱️  Monitoring for {duration} seconds...")
                time.sleep(duration)
            else:
                # Monitor indefinitely
                while True:
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")

        finally:
            self.print_statistics()
            self.close()

    def close(self):
        """Close the MQTT connection."""
        self.client.loop_stop()
        self.client.disconnect()
        print("🔌 MQTT connection closed")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="JACCUS MQTT Data Monitor")
    parser.add_argument("--config", default="mqtt_config.json",
                       help="MQTT config file path")
    parser.add_argument("--duration", type=int,
                       help="Monitoring duration in seconds (infinite if not specified)")

    args = parser.parse_args()

    try:
        monitor = JACCUSDataMonitor(args.config)
        monitor.monitor(args.duration)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'monitor' in locals():
            monitor.close()


if __name__ == "__main__":
    main()
