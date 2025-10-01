#!/usr/bin/env python

"""
Minimal Adaptive Cruise Control (ACC) system implementation.
Based on automatic_control_zenoh.py import strategy.
"""

import math
import random
import sys
import os
import glob

# ==============================================================================
# -- Find CARLA module (EXACT copy from automatic_control_zenoh.py) -----------
# ==============================================================================
try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

# ==============================================================================
# -- Add PythonAPI for release mode --------------------------------------------
# ==============================================================================
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/carla')
except IndexError:
    pass

# Try to import CARLA and its agents (EXACT copy from automatic_control_zenoh.py)
try:
    import carla

    from agents.navigation.behavior_agent import BehaviorAgent
    from agents.navigation.basic_agent import BasicAgent
    from agents.navigation.constant_velocity_agent import ConstantVelocityAgent
    CARLA_AGENTS_AVAILABLE = True

except ImportError:
    print("ERROR: CARLA not found. Please install CARLA Python API.")
    CARLA_AGENTS_AVAILABLE = False

from ..core.config import Config


class AdaptiveCruiseControl:
    """Simplified Adaptive Cruise Control system using CARLA's BehaviorAgent."""

    def __init__(self, vehicle, world):
        """Initialize ACC system with BehaviorAgent."""
        self.vehicle = vehicle
        self.world = world
        self.enabled = False
        self.target_speed = Config.ACC_DEFAULT_TARGET_SPEED

        # Check if CARLA agents are available
        if not CARLA_AGENTS_AVAILABLE:
            print("WARNING: CARLA agents not available. ACC will use fallback mode.")

        # BehaviorAgent setup
        self.agent = None
        self.agent_type = "Behavior"
        self.behavior = "normal"

        # ACC-specific state
        self.manual_override_active = False
        self.emergency_brake_active = False
        self.brake_factor = 0.0

        # Fallback PID controller when BehaviorAgent not available
        self.pid_kp = 0.8
        self.pid_ki = 0.1
        self.pid_kd = 0.2
        self.pid_integral = 0.0
        self.pid_previous_error = 0.0

    def toggle(self):
        """Toggle ACC on/off."""
        self.enabled = not self.enabled
        if self.enabled:
            if CARLA_AGENTS_AVAILABLE:
                self._initialize_agent()
                self._set_random_destination()
            else:
                self.pid_integral = 0.0
                self.pid_previous_error = 0.0

            current_speed = self._get_current_speed_kmh()
            self.target_speed = max(Config.ACC_MIN_SPEED, current_speed)

            mode = "BehaviorAgent" if CARLA_AGENTS_AVAILABLE else "Fallback PID"
            self.world.hud.notification(
                f'ACC ON ({mode}) - Target: {self.target_speed:.1f} km/h')
        else:
            self.agent = None
            self.brake_factor = 0.0
            self.manual_override_active = False
            self.emergency_brake_active = False
            self.world.hud.notification('Adaptive Cruise Control OFF')

    def _initialize_agent(self):
        """Initialize the BehaviorAgent."""
        if not CARLA_AGENTS_AVAILABLE:
            return

        try:
            self.agent = BehaviorAgent(self.vehicle, behavior=self.behavior)

            if hasattr(self.agent, 'set_target_speed'):
                self.agent.set_target_speed(self.target_speed / 3.6)

        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            self.agent = None

    def _set_random_destination(self):
        """Set random destination for the agent."""
        if not CARLA_AGENTS_AVAILABLE or not self.agent:
            return

        if hasattr(self.world, 'map'):
            try:
                spawn_points = self.world.map.get_spawn_points()
                if spawn_points:
                    destination = random.choice(spawn_points).location
                    self.agent.set_destination(destination)
            except Exception as e:
                print(f"Failed to set destination: {e}")

    def increase_target_speed(self):
        """Increase target speed by increment."""
        if self.enabled:
            new_speed = self.target_speed + Config.ACC_SPEED_INCREMENT
            self.target_speed = self._clamp(new_speed, Config.ACC_MIN_SPEED, Config.ACC_MAX_SPEED)
            if CARLA_AGENTS_AVAILABLE and self.agent and hasattr(self.agent, 'set_target_speed'):
                self.agent.set_target_speed(self.target_speed / 3.6)

    def decrease_target_speed(self):
        """Decrease target speed by increment."""
        if self.enabled:
            new_speed = self.target_speed - Config.ACC_SPEED_INCREMENT
            self.target_speed = self._clamp(new_speed, Config.ACC_MIN_SPEED, Config.ACC_MAX_SPEED)
            if CARLA_AGENTS_AVAILABLE and self.agent and hasattr(self.agent, 'set_target_speed'):
                self.agent.set_target_speed(self.target_speed / 3.6)

    def get_status_info(self):
        """Get ACC status information for display."""
        return {
            'enabled': self.enabled,
            'target_speed': self.target_speed,
            'brake_factor': self.brake_factor,
            'lane_keeping': True,
            'emergency_brake': self.emergency_brake_active,
            'agent_type': self.agent_type if (CARLA_AGENTS_AVAILABLE and self.agent) else "Fallback",
            'has_destination': (CARLA_AGENTS_AVAILABLE and self.agent and
                              hasattr(self.agent, 'done') and not self.agent.done()),
        }

    def update_control(self, base_control, world):
        """Update vehicle control using BehaviorAgent or fallback PID controller."""
        if not self.enabled:
            return base_control

        # Use BehaviorAgent if available
        if CARLA_AGENTS_AVAILABLE and self.agent:
            return self._update_control_with_agent(base_control, world)
        else:
            return self._update_control_fallback(base_control, world)

    def _update_control_with_agent(self, base_control, world):
        """Update control using BehaviorAgent."""
        try:
            if self.agent.done():
                self._set_random_destination()
                world.hud.notification("ACC: New destination set")

            agent_control = self.agent.run_step()

            if not self.manual_override_active:
                base_control.throttle = agent_control.throttle
                base_control.steer = agent_control.steer
                base_control.brake = agent_control.brake
                base_control.hand_brake = agent_control.hand_brake
                base_control.reverse = agent_control.reverse
                base_control.manual_gear_shift = agent_control.manual_gear_shift
                base_control.gear = agent_control.gear
                self.brake_factor = agent_control.brake

        except Exception as e:
            print(f"Agent control error: {e}")
            base_control.throttle = 0.0
            base_control.brake = 0.3
            self.brake_factor = 0.3

        return base_control

    def _update_control_fallback(self, base_control, world):
        """Fallback PID controller."""
        if self.manual_override_active:
            return base_control

        current_speed = self._get_current_speed_kmh()
        speed_error = self.target_speed - current_speed

        self.pid_integral += speed_error
        derivative = speed_error - self.pid_previous_error

        pid_output = (self.pid_kp * speed_error +
                     self.pid_ki * self.pid_integral +
                     self.pid_kd * derivative)

        if pid_output > 0:
            base_control.throttle = min(0.8, pid_output / 10.0)
            base_control.brake = 0.0
            self.brake_factor = 0.0
        else:
            base_control.throttle = 0.0
            base_control.brake = min(0.8, abs(pid_output) / 10.0)
            self.brake_factor = base_control.brake

        self.pid_previous_error = speed_error
        return base_control

    def _get_current_speed_kmh(self):
        """Get current vehicle speed in km/h."""
        velocity = self.vehicle.get_velocity()
        speed_ms = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        return 3.6 * speed_ms

    def is_emergency_brake_active(self):
        """Check if emergency brake is currently active."""
        return self.emergency_brake_active

    def _clamp(self, value, min_value, max_value):
        """Clamp value between min and max."""
        return max(min_value, min(value, max_value))
