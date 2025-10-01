"""
Zenoh communication client for vehicle data publishing.

This module implements Zenoh-based distributed communication for real-time
vehicle telemetry and status data sharing across JACCUS instances and
external systems in a robotics network.

Classes:
    ZenohClient: Main Zenoh communication interface for vehicle data

Functions:
    create_zenoh_client: Factory function for ZenohClient instantiation

Note:
    Zenoh provides efficient pub/sub communication with automatic discovery
    and routing for distributed autonomous vehicle systems.
"""

import json
from ..vehicle.control import VehicleTelemetry
from ..core.config import Config


class ZenohClient:
    """
    Zenoh client for publishing vehicle telemetry and status data.

    Provides real-time vehicle data publishing using Zenoh's distributed
    communication framework for inter-system coordination and monitoring.

    Args:
        vehicle (carla.Vehicle): CARLA vehicle to monitor
        config_data (str|dict, optional): Zenoh configuration file path or dict

    Attributes:
        vehicle: Reference to CARLA vehicle actor
        telemetry (VehicleTelemetry): Vehicle telemetry collection system
        session: Zenoh session for communication
        publisher: Zenoh publisher for vehicle status topic

    Note:
        Automatically handles Zenoh session management and graceful fallback
        if Zenoh is unavailable or configuration fails.
    """

    def __init__(self, vehicle, config_data=None):
        """Initialize Zenoh client."""
        self.vehicle = vehicle
        self.telemetry = VehicleTelemetry(vehicle)
        self.session = None
        self.publisher = None

        # Initialize Zenoh session
        try:
            import zenoh
            conf = zenoh.Config()
            if config_data:
                if isinstance(config_data, str):
                    conf = zenoh.Config.from_file(config_data)
                elif isinstance(config_data, dict):
                    conf = zenoh.Config.from_json5(json.dumps(config_data))
            self.session = zenoh.open(conf)            # Create publisher for vehicle status
            self.publisher = self.session.declare_publisher("vehicle/status")
            print("Zenoh client initialized successfully")

        except Exception as e:
            print(f"Failed to initialize Zenoh client: {e}")
            self.session = None
            self.publisher = None

    def publish_vehicle_status(self, acc_status=None):
        """Publish current vehicle status via Zenoh."""
        if not self.publisher:
            return

        try:
            # Get vehicle telemetry data
            location = self.telemetry.get_location()
            speed_kmh = self.telemetry.get_speed_kmh()
            speed_ms = self.telemetry.get_speed_ms()
            forward_vector = self.telemetry.get_forward_vector()

            # Prepare status data
            status_data = {
                "timestamp": self._get_timestamp(),
                "location": {
                    "x": location.x,
                    "y": location.y,
                    "z": location.z
                },
                "speed": {
                    "kmh": speed_kmh,
                    "ms": speed_ms
                },
                "forward_vector": {
                    "x": forward_vector.x,
                    "y": forward_vector.y,
                    "z": forward_vector.z
                },
                "moving_forward": self.telemetry.is_moving_forward()
            }

            # Add ACC status if available
            if acc_status:
                status_data["acc"] = acc_status

            # Publish data
            json_data = json.dumps(status_data)
            self.publisher.put(json_data)

        except Exception as e:
            print(f"Failed to publish vehicle status: {e}")

    def close(self):
        """Close Zenoh session."""
        if self.session:
            try:
                self.session.close()
                print("Zenoh client closed")
            except Exception as e:
                print(f"Error closing Zenoh client: {e}")

    def _get_timestamp(self):
        """Get current timestamp."""
        import time
        return int(time.time() * 1000)  # Milliseconds since epoch


class MockZenohClient:
    """Mock Zenoh client for testing when Zenoh is not available."""

    def __init__(self, vehicle, config_data=None):
        """Initialize mock client."""
        self.vehicle = vehicle
        self.telemetry = VehicleTelemetry(vehicle)
        print("Using mock Zenoh client (Zenoh not available)")

    def publish_vehicle_status(self, acc_status=None):
        """Mock publish - just print status."""
        try:
            location = self.telemetry.get_location()
            speed_kmh = self.telemetry.get_speed_kmh()

            status_msg = f"Vehicle Status - Speed: {speed_kmh:.1f} km/h, "
            status_msg += f"Location: ({location.x:.1f}, {location.y:.1f}, {location.z:.1f})"

            if acc_status:
                status_msg += f", ACC: {'ON' if acc_status.get('enabled') else 'OFF'}"
                if acc_status.get('enabled'):
                    status_msg += f" (Target: {acc_status.get('target_speed', 0):.1f} km/h)"

            # Only print occasionally to avoid spam
            import time
            if not hasattr(self, '_last_print') or time.time() - self._last_print > 2.0:
                print(status_msg)
                self._last_print = time.time()

        except Exception as e:
            pass  # Silently ignore errors in mock mode

    def close(self):
        """Mock close."""
        pass


def create_zenoh_client(vehicle, config_data=None):
    """Factory function to create Zenoh client with fallback to mock."""
    try:
        import zenoh
        return ZenohClient(vehicle, config_data)
    except ImportError:
        return MockZenohClient(vehicle, config_data)
