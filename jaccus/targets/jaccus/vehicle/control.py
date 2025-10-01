"""
Vehicle control and telemetry systems for JACCUS.

This module provides vehicle control interfaces, telemetry collection,
and physics calculations for the JACCUS CARLA client.

Classes:
    VehicleController: Primary vehicle control interface
    VehicleTelemetry: Vehicle status and telemetry monitoring
    PhysicsHelper: Physics calculation utilities
"""

import pygame
import carla
from ..core.config import Config
from ..sensors.motion_sensors import get_actor_display_name


class VehicleController(object):
    """
    Controller for vehicle operations and control management.

    Provides a high-level interface for vehicle control operations,
    managing throttle, brake, and steering inputs.

    Args:
        world: CARLA world instance containing the vehicle

    Attributes:
        world: Reference to CARLA world
        _control (carla.VehicleControl): Internal control state
    """

    def __init__(self, world):
        self.world = world
        self._control = carla.VehicleControl()

    def get_current_control(self):
        """
        Get current vehicle control state.

        Returns:
            carla.VehicleControl: Current control configuration
        """
        return self._control

    def update_control(self, throttle=None, brake=None, steer=None):
        """
        Update vehicle control values selectively.

        Args:
            throttle (float, optional): Throttle value [0.0, 1.0]
            brake (float, optional): Brake value [0.0, 1.0]
            steer (float, optional): Steering value [-1.0, 1.0]

        Note:
            Only provided parameters are updated, others remain unchanged.
        """
        if throttle is not None:
            self._control.throttle = throttle
        if brake is not None:
            self._control.brake = brake
        if steer is not None:
            self._control.steer = steer

    def apply_control(self, control=None):
        """
        Apply control commands to the vehicle.

        Args:
            control (carla.VehicleControl, optional): Control to apply.
                If None, uses internal control state.

        Note:
            Directly interfaces with CARLA vehicle actor for control application.
        """
        if control is None:
            control = self._control
        self.world.player.apply_control(control)


class VehicleTelemetry(object):
    """
    Vehicle telemetry and status monitoring system.

    Provides real-time access to vehicle state information including
    speed, location, orientation, and motion analysis.

    Args:
        vehicle (carla.Vehicle): CARLA vehicle actor to monitor

    Attributes:
        vehicle: Reference to CARLA vehicle actor
    """

    def __init__(self, vehicle):
        self.vehicle = vehicle

    def get_speed_kmh(self):
        """
        Get current vehicle speed in kilometers per hour.

        Returns:
            float: Vehicle speed in km/h

        Note:
            Calculated from 3D velocity vector magnitude.
        """
        v = self.vehicle.get_velocity()
        return 3.6 * (v.x**2 + v.y**2 + v.z**2)**0.5

    def get_speed_ms(self):
        """
        Get current vehicle speed in meters per second.

        Returns:
            float: Vehicle speed in m/s

        Note:
            Direct 3D velocity vector magnitude calculation.
        """
        v = self.vehicle.get_velocity()
        return (v.x**2 + v.y**2 + v.z**2)**0.5

    def get_location(self):
        """
        Get current vehicle location in world coordinates.

        Returns:
            carla.Location: 3D position in CARLA world coordinate system
        """
        return self.vehicle.get_transform().location

    def get_forward_vector(self):
        """
        Get normalized forward direction vector of vehicle.

        Returns:
            carla.Vector3D: Unit vector pointing in vehicle's forward direction

        Note:
            Based on vehicle's current orientation/rotation.
        """
        return self.vehicle.get_transform().get_forward_vector()

    def is_moving_forward(self, threshold=0.1):
        """
        Check if vehicle is moving in forward direction.

        Args:
            threshold (float): Minimum forward velocity component (m/s)

        Returns:
            bool: True if moving forward above threshold

        Note:
            Uses dot product of velocity and forward vectors for determination.
        """
        velocity = self.vehicle.get_velocity()
        forward = self.get_forward_vector()
        dot_product = velocity.x * forward.x + velocity.y * forward.y
        return dot_product > threshold


class PhysicsHelper(object):
    """
    Physics calculation utilities for vehicle dynamics.

    Provides static methods for common physics calculations used in
    vehicle control and motion planning systems.

    Note:
        All methods are static and can be used without instantiation.
    """

    @staticmethod
    def calculate_distance(loc1, loc2):
        """
        Calculate Euclidean distance between two 3D locations.

        Args:
            loc1 (carla.Location): First location point
            loc2 (carla.Location): Second location point

        Returns:
            float: Distance in meters

        Note:
            Uses 3D distance calculation including Z-axis component.
        """
        return ((loc1.x - loc2.x)**2 + (loc1.y - loc2.y)**2 + (loc1.z - loc2.z)**2)**0.5

    @staticmethod
    def calculate_stopping_distance(speed_ms, deceleration=Config.ACC_MAX_DECELERATION):
        """
        Calculate required stopping distance for given speed and deceleration.

        Args:
            speed_ms (float): Current speed in m/s
            deceleration (float): Available deceleration in m/s²

        Returns:
            float: Stopping distance in meters

        Note:
            Uses kinematic equation: d = v²/(2a) for uniform deceleration.
        """
        return (speed_ms**2) / (2 * deceleration)

    @staticmethod
    def normalize_angle(angle):
        """
        Normalize angle to [-π, π] range.

        Args:
            angle (float): Angle in radians

        Returns:
            float: Normalized angle in [-π, π] range

        Note:
            Ensures angular values are in standard mathematical range.
        """
        import math
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
