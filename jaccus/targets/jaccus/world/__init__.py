#!/usr/bin/env python

"""
World management module for CARLA environment control.

This module provides world management capabilities including:
- CARLA world initialization and configuration
- Vehicle spawning and physics management
- Weather and environmental control
- Sensor management and attachment
- Thread-safe logging system with comprehensive telemetry

Classes:
    World: Main CARLA world manager with integrated logging
    RadarSensor: Radar sensor implementation for obstacle detection

Functions:
    get_actor_display_name: Utility for readable actor identification
    get_actor_blueprints: Vehicle blueprint filtering and selection
    find_weather_presets: Available weather configuration discovery

Key Features:
    - Synchronous/asynchronous world operation modes
    - Comprehensive sensor suite management
    - Real-time logging with timestamp precision
    - Vehicle physics modification and control
    - Map layer management and navigation
"""

from .world_manager import World

__all__ = ['World']
