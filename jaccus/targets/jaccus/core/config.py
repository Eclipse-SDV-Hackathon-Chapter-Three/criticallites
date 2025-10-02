#!/usr/bin/env python

"""
Configuration constants and settings for JACCUS.

This module contains all configuration parameters for the JACCUS CARLA client,
including ACC system parameters, emergency brake settings, PID controller
tuning, sensor configurations, and communication settings.

Classes:
    Config: Central configuration class containing all system parameters
"""


class Config:
    """
    Configuration constants for JACCUS application.

    This class contains all configurable parameters for the JACCUS system,
    organized by functional area (ACC, Emergency Brake, PID, Sensors, etc.).

    Attributes:
        ACC_*: Adaptive Cruise Control parameters
        EMERGENCY_BRAKE_*: Emergency braking system parameters
        PID_*: PID controller tuning parameters
        MQTT_*: MQTT communication settings
        HUD_*: Head-up display configuration

    Note:
        All speed values in km/h, distances in meters, angles in degrees.
    """

    # Application metadata
    APP_NAME = "JACCUS"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "CARLA Manual Control with Adaptive Cruise Control"

    # Default window settings
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720

    # Vehicle settings
    DEFAULT_ACTOR_FILTER = 'vehicle.*'
    DEFAULT_ACTOR_GENERATION = '2'
    DEFAULT_ROLE_NAME = 'hero'

    # Network settings
    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 2000
    DEFAULT_ROUTER = '127.0.0.1'

    # Physics settings
    DEFAULT_GAMMA = 2.2
    FIXED_DELTA_SECONDS = 0.05

    # ACC (Adaptive Cruise Control) settings
    ACC_DEFAULT_TARGET_SPEED = 60.0   # km/h
    ACC_MIN_SPEED = 20.0              # km/h
    ACC_MAX_SPEED = 120.0             # km/h
    ACC_SPEED_INCREMENT = 2.0         # km/h
    ACC_MIN_DISTANCE = 10.0           # meters
    ACC_SAFE_DISTANCE = 20.0          # meters
    ACC_SAFE_DISTANCE_FACTOR = 2.0
    ACC_MAX_DECELERATION = 4.0        # m/s²
    ACC_BRAKE_SMOOTHING = 0.1
    ACC_EMERGENCY_BRAKE_FACTOR = 3.0

    # Enhanced PID Controller Parameters
    PID_KP = 1.2                      # Proportional gain (increased for better response)
    PID_KI = 0.15                     # Integral gain (prevents steady-state error)
    PID_KD = 0.3                      # Derivative gain (reduces overshoot)
    PID_INTEGRAL_LIMIT = 20.0         # Prevent integral windup
    PID_THROTTLE_SCALE_NORMAL = 8.0   # Normal throttle scaling factor
    PID_THROTTLE_SCALE_AGGRESSIVE = 15.0  # Aggressive scaling for large errors
    PID_LARGE_ERROR_THRESHOLD = 4.0   # km/h error threshold for aggressive scaling

    # Emergency Brake System Parameters
    EMERGENCY_BRAKE_DISTANCE = 5.0    # meters - immediate emergency brake
    EMERGENCY_BRAKE_WARNING_DISTANCE = 15.0  # meters - warning zone
    SIDEWALK_DETECTION_DISTANCES = [3.0, 6.0, 10.0, 15.0]  # meters - lookahead distances
    MIN_LANE_WIDTH = 2.5              # meters - minimum acceptable lane width
    REVERSE_GEAR_MAX_SPEED = 5.0      # km/h - maximum speed to engage reverse

    # Sensor settings
    LIDAR_RANGE = 50.0                # meters
    RADAR_FOV_HORIZONTAL = 35         # degrees
    RADAR_FOV_VERTICAL = 20           # degrees

    # Sensor blueprints
    COLLISION_BP = 'sensor.other.collision'
    LANE_INVASION_BP = 'sensor.other.lane_invasion'
    GNSS_BP = 'sensor.other.gnss'
    IMU_BP = 'sensor.other.imu'

    # Obstacle detection settings
    OBSTACLE_DETECTION_RANGE = 50.0      # meters
    OBSTACLE_DETECTION_RADIUS = 0.6      # meters
    OBSTACLE_DETECTION_CONE_ANGLE = 0.7  # dot product threshold (~ 45 degrees)

    # Lane keeping assistance settings
    LANE_KEEPING_MAX_STEER = 0.15        # Maximum steering correction (reduced for smoothness)
    LANE_KEEPING_SPEED_THRESHOLD = 8.0   # Minimum speed for lane keeping (km/h)
    LANE_KEEPING_CORRECTION_FACTOR = 0.4 # Steering correction strength
    LANE_KEEPING_LOOKAHEAD = 12.0        # Distance to look ahead for lane center (meters)

    # Vehicle physics limits
    MAX_STEER_CACHE = 0.7
    STEER_INCREMENT_FACTOR = 5e-4

    # HUD settings
    HUD_FONT_SIZE = 14
    HUD_FONT_SIZE_SMALL = 12
    HUD_ALPHA = 100
    HUD_BAR_WIDTH = 106
    HUD_BAR_HEIGHT_OFFSET = 100
    HUD_FADE_DURATION = 2.0           # seconds

    # Notification settings
    NOTIFICATION_DEFAULT_DURATION = 2.0  # seconds
    NOTIFICATION_FADE_RATE = 500.0

    # History settings
    COLLISION_HISTORY_SIZE = 4000
    OBSTACLE_HISTORY_SIZE = 4000
    OBSTACLE_FRAME_THRESHOLD = 10     # frames

    # Speed limits
    PLAYER_MAX_SPEED = 1.589
    PLAYER_MAX_SPEED_FAST = 3.713

    # MQTT settings
    MQTT_DEFAULT_BROKER = 'localhost'
    MQTT_DEFAULT_PORT = 1883
    MQTT_DEFAULT_KEEPALIVE = 60
    MQTT_DEFAULT_QOS = 1
    MQTT_PUBLISH_INTERVAL = 1.0        # seconds
    MQTT_TOPIC_VEHICLE_PARAMS = "vehicle/parameters"
    MQTT_TOPIC_VEHICLE_COMMANDS = "vehicle/commands"

    # MQTT command types
    MQTT_COMMAND_SPEED = "speed"
    MQTT_COMMAND_CRUISE_CONTROL = "cruise_control"
    MQTT_COMMAND_EMERGENCY_STOP = "emergency_stop"
