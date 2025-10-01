#!/usr/bin/env python3
"""
Test MQTT publisher that simulates external commands to JACCUS vehicle.
This script demonstrates sending commands to control the ACC system.
"""

import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime


class JACCUSCommandTester:
    """Test client to send commands to JACCUS via MQTT."""

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
                    "vehicle_commands": "vehicle/commands"
                }
            }

        # MQTT client setup
        self.client = mqtt.Client(client_id="jaccus_command_tester")
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish

        # Connect to broker
        self.client.connect(
            self.config["broker"],
            self.config["port"],
            60
        )
        self.client.loop_start()

        # Wait for connection
        time.sleep(1)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker at {self.config['broker']}:{self.config['port']}")
        else:
            print(f"Failed to connect: {rc}")

    def _on_publish(self, client, userdata, mid):
        print(f"Command published successfully (mid: {mid})")

    def send_speed_command(self, target_speed):
        """Send speed command to set ACC target speed."""
        command = {
            "command": "speed",
            "value": target_speed,
            "timestamp": datetime.now().isoformat()
        }

        topic = self.config["topics"]["vehicle_commands"]
        payload = json.dumps(command)

        print(f"Sending speed command: {payload}")
        result = self.client.publish(topic, payload, qos=1)

        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def send_cruise_control_command(self, enable):
        """Send cruise control enable/disable command."""
        command = {
            "command": "cruise_control",
            "value": enable,
            "timestamp": datetime.now().isoformat()
        }

        topic = self.config["topics"]["vehicle_commands"]
        payload = json.dumps(command)

        print(f"Sending cruise control command: {payload}")
        result = self.client.publish(topic, payload, qos=1)

        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def send_emergency_stop_command(self):
        """Send emergency stop command."""
        command = {
            "command": "emergency_stop",
            "value": True,
            "timestamp": datetime.now().isoformat()
        }

        topic = self.config["topics"]["vehicle_commands"]
        payload = json.dumps(command)

        print(f"Sending emergency stop command: {payload}")
        result = self.client.publish(topic, payload, qos=1)

        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def interactive_test(self):
        """Run interactive test session."""
        print("\n=== JACCUS MQTT Command Tester ===")
        print("Commands:")
        print("1. Set target speed")
        print("2. Enable cruise control")
        print("3. Disable cruise control")
        print("4. Emergency stop")
        print("5. Quit")

        while True:
            try:
                choice = input("\nEnter command (1-5): ").strip()

                if choice == "1":
                    speed = float(input("Enter target speed (km/h): "))
                    if 20 <= speed <= 120:
                        self.send_speed_command(speed)
                    else:
                        print("Speed must be between 20 and 120 km/h")

                elif choice == "2":
                    self.send_cruise_control_command(True)

                elif choice == "3":
                    self.send_cruise_control_command(False)

                elif choice == "4":
                    self.send_emergency_stop_command()

                elif choice == "5":
                    print("Exiting...")
                    break

                else:
                    print("Invalid choice")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except ValueError:
                print("Invalid input")

    def automated_test(self):
        """Run automated test sequence."""
        print("\n=== Running Automated Test Sequence ===")

        tests = [
            ("Enable Cruise Control", lambda: self.send_cruise_control_command(True)),
            ("Set Speed to 60 km/h", lambda: self.send_speed_command(60)),
            ("Set Speed to 80 km/h", lambda: self.send_speed_command(80)),
            ("Set Speed to 40 km/h", lambda: self.send_speed_command(40)),
            ("Emergency Stop", lambda: self.send_emergency_stop_command()),
            ("Disable Cruise Control", lambda: self.send_cruise_control_command(False)),
        ]

        for i, (description, test_func) in enumerate(tests, 1):
            print(f"\nTest {i}/6: {description}")
            success = test_func()
            print(f"Result: {'SUCCESS' if success else 'FAILED'}")
            time.sleep(2)  # Wait between tests

        print("\nAutomated test sequence completed!")

    def close(self):
        """Close the MQTT connection."""
        self.client.loop_stop()
        self.client.disconnect()
        print("MQTT connection closed")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="JACCUS MQTT Command Tester")
    parser.add_argument("--config", default="mqtt_config.json",
                       help="MQTT config file path")
    parser.add_argument("--auto", action="store_true",
                       help="Run automated test sequence")

    args = parser.parse_args()

    try:
        tester = JACCUSCommandTester(args.config)

        if args.auto:
            tester.automated_test()
        else:
            tester.interactive_test()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'tester' in locals():
            tester.close()


if __name__ == "__main__":
    main()
