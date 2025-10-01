#!/usr/bin/env python

"""
Motion and collision detection sensors for JACCUS.

This module provides sensor implementations for collision detection,
lane invasion monitoring, GNSS positioning, IMU data, and obstacle detection
using CARLA's sensor framework.

Classes:
    CollisionSensor: Vehicle collision detection and history tracking
    LaneInvasionSensor: Lane boundary violation detection
    GnssSensor: GPS positioning and navigation data
    IMUSensor: Inertial measurement unit for motion tracking
    ObstacleDetectionSensor: Forward obstacle detection for ACC system

Functions:
    get_actor_display_name: Utility for generating readable actor names
"""

import collections
import math
import weakref
import carla
from ..core.config import Config


def get_actor_display_name(actor, truncate=250):
    """
    Get a readable display name for a CARLA actor.

    Args:
        actor (carla.Actor): CARLA actor to generate name for
        truncate (int): Maximum name length before truncation

    Returns:
        str: Human-readable actor name with proper capitalization

    Note:
        Converts internal CARLA type IDs to user-friendly display names.
    """
    name = ' '.join(actor.type_id.replace('_', '.').title().split('.')[1:])
    return (name[:truncate - 1] + u'\u2026') if len(name) > truncate else name


class CollisionSensor(object):
    """
    Sensor for detecting and tracking vehicle collisions.

    Monitors collision events and maintains a history of collision
    intensities for analysis and safety system integration.

    Args:
        parent_actor (carla.Vehicle): Vehicle to attach sensor to
        hud: HUD instance for collision notifications
        name (str): Sensor identifier for multi-sensor setups

    Attributes:
        sensor (carla.Sensor): CARLA collision sensor instance
        history (list): Collision event history with frame and intensity
        _parent: Reference to parent vehicle
        hud: HUD interface for user notifications
    """

    def __init__(self, parent_actor, hud, name="collision_1"):
        self.sensor = None
        self.history = []
        self._parent = parent_actor
        self.hud = hud

        world = self._parent.get_world()
        bp = world.get_blueprint_library().find('sensor.other.collision')
        if bp.has_attribute('role_name'):
            bp.set_attribute('role_name', name)

        self.sensor = world.spawn_actor(bp, carla.Transform(), attach_to=self._parent)

        # We need to pass the lambda a weak reference to self to avoid circular reference
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: CollisionSensor._on_collision(weak_self, event))

    def get_collision_history(self):
        """Get collision history as a defaultdict."""
        history = collections.defaultdict(int)
        for frame, intensity in self.history:
            history[frame] += intensity
        return history

    @staticmethod
    def _on_collision(weak_self, event):
        """Handle collision events."""
        self = weak_self()
        if not self:
            return

        actor_type = get_actor_display_name(event.other_actor)
        self.hud.notification(f'Collision with {actor_type}')

        impulse = event.normal_impulse
        intensity = math.sqrt(impulse.x**2 + impulse.y**2 + impulse.z**2)
        self.history.append((event.frame, intensity))

        # Limit history size
        if len(self.history) > Config.COLLISION_HISTORY_SIZE:
            self.history.pop(0)

    def destroy(self):
        """Clean up the sensor."""
        if self.sensor is not None and self.sensor.is_alive:
            self.sensor.stop()
            self.sensor.destroy()
            self.sensor = None


class LaneInvasionSensor(object):
    """Sensor for detecting lane invasions."""

    def __init__(self, parent_actor, hud, name="lane_invasion_1"):
        self.sensor = None

        # If the spawn object is not a vehicle, we cannot use the Lane Invasion Sensor
        if parent_actor.type_id.startswith("vehicle."):
            self._parent = parent_actor
            self.hud = hud
            world = self._parent.get_world()
            bp = world.get_blueprint_library().find('sensor.other.lane_invasion')
            if bp.has_attribute('role_name'):
                bp.set_attribute('role_name', name)

            self.sensor = world.spawn_actor(bp, carla.Transform(), attach_to=self._parent)

            # We need to pass the lambda a weak reference to self to avoid circular reference
            weak_self = weakref.ref(self)
            self.sensor.listen(lambda event: LaneInvasionSensor._on_invasion(weak_self, event))

    @staticmethod
    def _on_invasion(weak_self, event):
        """Handle lane invasion events."""
        self = weak_self()
        if not self:
            return

        lane_types = set(x.type for x in event.crossed_lane_markings)
        text = ['%r' % str(x).split()[-1] for x in lane_types]
        self.hud.notification(f'Crossed line {" and ".join(text)}')

    def destroy(self):
        """Clean up the sensor."""
        if self.sensor is not None and self.sensor.is_alive:
            self.sensor.stop()
            self.sensor.destroy()
            self.sensor = None


class ObstacleDetectionSensor(object):
    """
    A lightweight obstacle detector helper for ACC systems.
    Spawns `sensor.other.obstacle`, listens for ObstacleDetectionEvent, updates HUD,
    and keeps a rolling history of detections.

    History items are tuples: (frame, distance_m, other_actor_id, other_actor_type)
    """

    def __init__(self, parent_actor, hud, name="obstacle_detection_1",
                 distance=12.0, hit_radius=0.6, only_dynamics=False,
                 debug_linetrace=False, attach_transform=None,
                 history_len=4000):

        self.sensor = None
        self.history = []
        self._parent = parent_actor
        self.hud = hud
        self.history_len = max(1, int(history_len))
        self.total_detections = 0

        # Expose a simple counter on the HUD object so it can be rendered if desired
        if not hasattr(self.hud, "obstacles_detected"):
            self.hud.obstacles_detected = 0

        world = self._parent.get_world()
        bp = world.get_blueprint_library().find('sensor.other.obstacle')
        if bp.has_attribute('role_name'):
            bp.set_attribute('role_name', name)

        # Configure the obstacle sensor according to CARLA 0.9.15 docs
        if bp.has_attribute('distance'):
            bp.set_attribute('distance', str(float(distance)))
        if bp.has_attribute('hit_radius'):
            bp.set_attribute('hit_radius', str(float(hit_radius)))
        if bp.has_attribute('only_dynamics'):
            bp.set_attribute('only_dynamics', 'true' if only_dynamics else 'false')
        if bp.has_attribute('debug_linetrace'):
            bp.set_attribute('debug_linetrace', 'true' if debug_linetrace else 'false')

        # Mount slightly forward by default so the capsule starts at the bumper
        if attach_transform is None:
            attach_transform = carla.Transform(carla.Location(x=2.0, z=1.0))

        self.sensor = world.spawn_actor(bp, attach_transform, attach_to=self._parent)

        # Avoid circular reference by using a weakref in the callback
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: ObstacleDetectionSensor._on_obstacle(weak_self, event))

    def destroy(self):
        """Clean up the sensor."""
        if self.sensor is not None and self.sensor.is_alive:
            self.sensor.stop()
            self.sensor.destroy()
            self.sensor = None

    def get_obstacle_history(self):
        """Returns a list of (frame, distance_m, other_actor_id, other_actor_type)."""
        return list(self.history)

    def get_total_detections(self):
        """Get total number of detections."""
        return int(self.total_detections)

    @staticmethod
    def _on_obstacle(weak_self, event):
        """Handle obstacle detection events."""
        self = weak_self()
        if not self:
            return

        # event.other_actor and event.distance exist per CARLA docs
        other = event.other_actor
        dist = float(getattr(event, "distance", float("nan")))
        actor_type = get_actor_display_name(other) if other else "Unknown"

        # Update HUD
        self.total_detections += 1
        # Keep a mirror on hud for easy rendering in overlays
        self.hud.obstacles_detected = self.total_detections

        # Notify (short, actionable)
        if not math.isnan(dist):
            self.hud.notification(f'Obstacle: {actor_type} at {dist:.1f} m (total: {self.total_detections})')
        else:
            self.hud.notification(f'Obstacle: {actor_type} (total: {self.total_detections})')

        # Store compact history record
        other_id = other.id if other else -1
        self.history.append((event.frame, dist, other_id, actor_type))
        if len(self.history) > self.history_len:
            self.history.pop(0)


class GnssSensor(object):
    """GNSS sensor for GPS coordinates."""

    def __init__(self, parent_actor):
        """Initialize GNSS sensor."""
        self.sensor = None
        self._parent = parent_actor
        self.lat = 0.0
        self.lon = 0.0
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find(Config.GNSS_BP)
        self.sensor = world.spawn_actor(bp, carla.Transform(carla.Location(x=1.0, z=2.8)), attach_to=self._parent)
        # We need to pass the lambda a weak reference to self to avoid circular
        # reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: GnssSensor._on_gnss_event(weak_self, event))

    @staticmethod
    def _on_gnss_event(weak_self, event):
        """Handle GNSS events."""
        self = weak_self()
        if not self:
            return
        self.lat = event.latitude
        self.lon = event.longitude


class IMUSensor(object):
    """IMU sensor for vehicle dynamics."""

    def __init__(self, parent_actor):
        """Initialize IMU sensor."""
        self.sensor = None
        self._parent = parent_actor
        self.accelerometer = (0.0, 0.0, 0.0)
        self.gyroscope = (0.0, 0.0, 0.0)
        self.compass = 0.0
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find(Config.IMU_BP)
        self.sensor = world.spawn_actor(bp, carla.Transform(carla.Location(x=-0.5, z=0.0)), attach_to=self._parent)
        # We need to pass the lambda a weak reference to self to avoid circular
        # reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda sensor_data: IMUSensor._IMU_callback(weak_self, sensor_data))

    @staticmethod
    def _IMU_callback(weak_self, sensor_data):
        """Handle IMU sensor data."""
        self = weak_self()
        if not self:
            return
        limits = (-99.9, 99.9)
        self.accelerometer = (
            max(limits[0], min(limits[1], sensor_data.accelerometer.x)),
            max(limits[0], min(limits[1], sensor_data.accelerometer.y)),
            max(limits[0], min(limits[1], sensor_data.accelerometer.z)))
        self.gyroscope = (
            max(limits[0], min(limits[1], math.degrees(sensor_data.gyroscope.x))),
            max(limits[0], min(limits[1], math.degrees(sensor_data.gyroscope.y))),
            max(limits[0], min(limits[1], math.degrees(sensor_data.gyroscope.z))))
        self.compass = math.degrees(sensor_data.compass)
