#!/usr/bin/env python

"""
Adaptive Cruise Control (ACC) system implementation.
Enhanced version using CARLA's BehaviorAgent for autonomous driving.
"""

import math
import random
import sys
import os
import glob

# ==============================================================================
# -- Find CARLA module ---------------------------------------------------------
# ==============================================================================
try:
    # Use Python 3.7 CARLA egg even on Python 3.10 for compatibility
    sys.path.append('../../../carla-simulator/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg')
    # Add CARLA agents path
    sys.path.append('../../../carla-simulator/PythonAPI/carla')
except:
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
    """Adaptive Cruise Control system using CARLA's BehaviorAgent."""

    def __init__(self, vehicle, world):
        """Initialize ACC system with BehaviorAgent."""
        self.vehicle = vehicle
        self.world = world
        self.enabled = False
        self.target_speed = Config.ACC_DEFAULT_TARGET_SPEED

        # Check if CARLA agents are available
        if not CARLA_AGENTS_AVAILABLE:
            print("WARNING: CARLA agents not available. ACC will use fallback mode.")
            print("To use BehaviorAgent, ensure CARLA PythonAPI is properly installed.")

        # BehaviorAgent setup (same as automatic_control_zenoh.py)
        self.agent = None
        self.agent_type = "Behavior"  # Default to BehaviorAgent
        self.behavior = "normal"      # Default behavior

        # ACC-specific overrides
        self.manual_override_active = False
        self.emergency_brake_active = False
        self.obstacle_detected = False

        # Speed control for manual override
        self.brake_factor = 0.0
        self.manual_steer_override = False

        # Lane keeping (handled by BehaviorAgent or fallback)
        self.lane_keeping_enabled = True

        # Enhanced PID controller parameters for better speed control
        self.pid_kp = 1.2          # Increased proportional gain
        self.pid_ki = 0.15         # Slightly increased integral gain
        self.pid_kd = 0.3          # Increased derivative gain
        self.pid_integral = 0.0
        self.pid_previous_error = 0.0
        self.pid_integral_limit = 20.0  # Prevent integral windup

    def toggle(self):
        """Toggle ACC on/off."""
        self.enabled = not self.enabled
        if self.enabled:
            if CARLA_AGENTS_AVAILABLE:
                # Initialize BehaviorAgent when ACC is enabled
                self._initialize_agent()
                # Set a destination for the agent
                self._set_random_destination()
            else:
                # Reset PID controller for fallback mode
                self.pid_integral = 0.0
                self.pid_previous_error = 0.0

            # Set initial target speed
            current_speed = self._get_current_speed_kmh()
            self.target_speed = max(Config.ACC_MIN_SPEED, current_speed)

            mode = "BehaviorAgent" if CARLA_AGENTS_AVAILABLE else "Fallback PID"
            self.world.hud.notification(
                f'ACC ON ({mode}) - Target: {self.target_speed:.1f} km/h')
        else:
            # Clean up agent when disabled
            self.agent = None
            self.brake_factor = 0.0
            self.manual_override_active = False
            self.emergency_brake_active = False
            self.world.hud.notification('Adaptive Cruise Control OFF')

    def _initialize_agent(self):
        """Initialize the BehaviorAgent (same logic as automatic_control_zenoh.py)."""
        if not CARLA_AGENTS_AVAILABLE:
            return

        try:
            if self.agent_type == "Basic":
                self.agent = BasicAgent(self.vehicle, 30)
                self.agent.follow_speed_limits(True)
            elif self.agent_type == "Constant":
                self.agent = ConstantVelocityAgent(self.vehicle, 30)
                ground_loc = self.world.world.ground_projection(self.vehicle.get_location(), 5)
                if ground_loc:
                    self.vehicle.set_location(ground_loc.location + carla.Location(z=0.01))
                self.agent.follow_speed_limits(True)
            elif self.agent_type == "Behavior":
                self.agent = BehaviorAgent(self.vehicle, behavior=self.behavior)

            # Set target speed for the agent
            if hasattr(self.agent, 'set_target_speed'):
                self.agent.set_target_speed(self.target_speed / 3.6)  # Convert km/h to m/s

        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            self.agent = None

    def _set_random_destination(self):
        """Set random destination for the agent (same as automatic_control_zenoh.py)."""
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
            # Update agent's target speed
            if CARLA_AGENTS_AVAILABLE and self.agent and hasattr(self.agent, 'set_target_speed'):
                self.agent.set_target_speed(self.target_speed / 3.6)

    def decrease_target_speed(self):
        """Decrease target speed by increment."""
        if self.enabled:
            new_speed = self.target_speed - Config.ACC_SPEED_INCREMENT
            self.target_speed = self._clamp(new_speed, Config.ACC_MIN_SPEED, Config.ACC_MAX_SPEED)
            # Update agent's target speed
            if CARLA_AGENTS_AVAILABLE and self.agent and hasattr(self.agent, 'set_target_speed'):
                self.agent.set_target_speed(self.target_speed / 3.6)

    def get_status_info(self):
        """Get ACC status information for display."""
        return {
            'enabled': self.enabled,
            'target_speed': self.target_speed,
            'brake_factor': self.brake_factor,
            'lane_keeping': self.lane_keeping_enabled,
            'emergency_brake': self.emergency_brake_active,
            'agent_type': self.agent_type if (CARLA_AGENTS_AVAILABLE and self.agent) else "Fallback",
            'has_destination': (CARLA_AGENTS_AVAILABLE and self.agent and
                              hasattr(self.agent, 'done') and not self.agent.done()),
        }

    def update_control(self, base_control, world):
        """
        Update vehicle control using BehaviorAgent or fallback PID controller.

        Args:
            base_control: Base vehicle control from manual input
            world: CARLA world instance

        Returns:
            carla.VehicleControl: Modified control with ACC and emergency brake

        Note:
            Emergency brake takes absolute priority over all other control inputs.
        """
        if not self.enabled:
            return base_control

        # Check for obstacles and emergency conditions
        obstacle_distance, emergency_brake_detected, brake_reason = self._get_closest_obstacle_distance(world)

        # IMMEDIATE EMERGENCY BRAKE OVERRIDE - highest priority
        if emergency_brake_detected:
            self.emergency_brake_active = True
            self.manual_override_active = True
            base_control.throttle = 0.0
            base_control.brake = 1.0
            self.brake_factor = 1.0

            # Force logging and notification
            if hasattr(world, 'log_message'):
                world.log_message(f"EMERGENCY_BRAKE_TRIGGERED: {brake_reason}", "EMERGENCY")

            world.hud.notification(f'🚨 EMERGENCY BRAKE! {brake_reason}')
            return base_control

        # Secondary check: Distance-based emergency brake for obstacles
        elif obstacle_distance <= Config.EMERGENCY_BRAKE_DISTANCE:
            self.emergency_brake_active = True
            self.manual_override_active = True
            base_control.throttle = 0.0
            base_control.brake = 1.0
            self.brake_factor = 1.0

            # Log emergency brake event
            reason = f"Obstacle at {obstacle_distance:.1f}m"
            if hasattr(world, 'log_emergency_brake_event'):
                world.log_emergency_brake_event(obstacle_distance, reason)

            world.hud.notification(f'🚨 EMERGENCY BRAKE! {reason}')
            return base_control

        # Warning zone monitoring
        elif obstacle_distance <= Config.EMERGENCY_BRAKE_WARNING_DISTANCE:
            self.obstacle_detected = True
            self.emergency_brake_active = False

            # Log warning zone detection
            if hasattr(world, 'log_message'):
                world.log_message(f"WARNING_ZONE: Obstacle detected at {obstacle_distance:.1f}m (warning threshold)", "ACC")
        else:
            self.obstacle_detected = False
            self.emergency_brake_active = False
            self.manual_override_active = False

        # Use BehaviorAgent if available, otherwise fallback to PID
        if CARLA_AGENTS_AVAILABLE and self.agent:
            return self._update_control_with_agent(base_control, world)
        else:
            return self._update_control_fallback(base_control, world)

    def _update_control_with_agent(self, base_control, world):
        """Update control using BehaviorAgent."""
        # Check if agent needs new destination (same as automatic_control_zenoh.py)
        if self.agent.done():
            self._set_random_destination()
            world.hud.notification("ACC: New destination set")

        # Get control from BehaviorAgent (main logic from automatic_control_zenoh.py)
        try:
            agent_control = self.agent.run_step()

            # Apply agent control if no manual override
            if not self.manual_override_active:
                # Use agent's control directly
                base_control.throttle = agent_control.throttle
                base_control.steer = agent_control.steer
                base_control.brake = agent_control.brake
                base_control.hand_brake = agent_control.hand_brake
                base_control.reverse = agent_control.reverse
                base_control.manual_gear_shift = agent_control.manual_gear_shift
                base_control.gear = agent_control.gear

                # Store brake factor for display
                self.brake_factor = agent_control.brake

        except Exception as e:
            print(f"Agent control error: {e}")
            # Fallback to safe stop
            base_control.throttle = 0.0
            base_control.brake = 0.3
            self.brake_factor = 0.3

        return base_control

    def _update_control_fallback(self, base_control, world):
        """Enhanced fallback PID controller with dynamic scaling and logging."""
        if self.manual_override_active:
            return base_control

        current_speed = self._get_current_speed_kmh()
        speed_error = self.target_speed - current_speed

        # PID controller with integral windup prevention
        self.pid_integral += speed_error
        self.pid_integral = max(-self.pid_integral_limit, min(self.pid_integral_limit, self.pid_integral))
        derivative = speed_error - self.pid_previous_error

        # Calculate PID output
        pid_output = (self.pid_kp * speed_error +
                     self.pid_ki * self.pid_integral +
                     self.pid_kd * derivative)

        # Dynamic throttle scaling for large speed errors
        if pid_output > 0:  # Need to accelerate
            if speed_error > 4.0:  # Large speed deficit - boost throttle
                throttle_scale = 15.0  # More aggressive scaling
                base_control.throttle = min(0.9, pid_output / throttle_scale)
            else:
                throttle_scale = 8.0   # Normal scaling
                base_control.throttle = min(0.7, pid_output / throttle_scale)

            base_control.brake = 0.0
            self.brake_factor = 0.0

            # Log speed control decisions
            if hasattr(world, 'log_message'):
                world.log_message(f"SPEED_CONTROL: Target={self.target_speed:.1f}, Current={current_speed:.1f}, Error={speed_error:.1f}, PID={pid_output:.2f}, Throttle={base_control.throttle:.3f}")

        else:  # Need to brake
            base_control.throttle = 0.0
            brake_scale = 10.0
            base_control.brake = min(0.8, abs(pid_output) / brake_scale)
            self.brake_factor = base_control.brake

            if hasattr(world, 'log_message'):
                world.log_message(f"SPEED_CONTROL: Braking - Target={self.target_speed:.1f}, Current={current_speed:.1f}, Error={speed_error:.1f}, Brake={base_control.brake:.3f}")

        # Keep current steering (no lane keeping in fallback mode)
        # base_control.steer remains unchanged

        self.pid_previous_error = speed_error

        return base_control

    def _get_current_speed_kmh(self):
        """Get current vehicle speed in km/h."""
        velocity = self.vehicle.get_velocity()
        speed_ms = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        return 3.6 * speed_ms

    def _check_road_boundaries(self, world):
        """
        Check if vehicle is approaching road boundaries or sidewalks.

        Args:
            world: CARLA world instance containing map and vehicle information

        Returns:
            tuple: (is_violation_detected, distance_to_violation)

        Note:
            This method uses CARLA waypoint analysis to detect potential sidewalk
            crossings by projecting vehicle trajectory forward at multiple distances.
        """
        try:
            vehicle_location = self.vehicle.get_location()
            vehicle_transform = self.vehicle.get_transform()

            # Get current waypoint with project_to_road=True for better accuracy
            current_waypoint = world.map.get_waypoint(vehicle_location, project_to_road=True)
            if not current_waypoint:
                return False, float('inf')

            # Check for sidewalk crossing by examining waypoints ahead
            forward_vector = vehicle_transform.get_forward_vector()

            # Enhanced look ahead distances for better detection
            check_distances = [2.0, 4.0, 6.0, 8.0, 12.0]

            for distance in check_distances:
                # Calculate future position with higher precision
                future_location = carla.Location(
                    vehicle_location.x + forward_vector.x * distance,
                    vehicle_location.y + forward_vector.y * distance,
                    vehicle_location.z + 0.1  # Slight elevation for better waypoint detection
                )

                # Get waypoint at future position
                future_waypoint = world.map.get_waypoint(future_location, project_to_road=False)

                # Check if no waypoint exists (off-road/sidewalk area)
                if not future_waypoint:
                    # Additional check: try to get nearest waypoint
                    nearest_waypoint = world.map.get_waypoint(future_location, project_to_road=True)
                    if nearest_waypoint:
                        # Calculate distance from projected position to road
                        road_distance = future_location.distance(nearest_waypoint.transform.location)
                        if road_distance > 3.0:  # Vehicle going too far from road
                            if hasattr(world, 'log_message'):
                                world.log_message(f"BOUNDARY_VIOLATION: Off-road detection at {distance:.1f}m, road distance {road_distance:.1f}m", "EMERGENCY")
                            world.hud.notification(f'🚨 OFF-ROAD DETECTED at {distance:.1f}m!')
                            return True, distance
                    else:
                        # No waypoint at all - definitely off road
                        if hasattr(world, 'log_message'):
                            world.log_message(f"BOUNDARY_VIOLATION: No waypoint found at {distance:.1f}m", "EMERGENCY")
                        world.hud.notification(f'🚨 SIDEWALK CROSSING DETECTED at {distance:.1f}m!')
                        return True, distance

                # Check waypoint type for sidewalks or restricted areas
                if future_waypoint and hasattr(future_waypoint, 'lane_type'):
                    if future_waypoint.lane_type == carla.LaneType.Sidewalk:
                        if hasattr(world, 'log_message'):
                            world.log_message(f"BOUNDARY_VIOLATION: Sidewalk lane type detected at {distance:.1f}m", "EMERGENCY")
                        world.hud.notification(f'🚨 SIDEWALK LANE DETECTED at {distance:.1f}m!')
                        return True, distance

                    # Also check for other prohibited lane types
                    prohibited_types = [carla.LaneType.Shoulder, carla.LaneType.Border, carla.LaneType.Restricted]
                    if future_waypoint.lane_type in prohibited_types:
                        if hasattr(world, 'log_message'):
                            world.log_message(f"BOUNDARY_VIOLATION: Prohibited lane type {future_waypoint.lane_type} at {distance:.1f}m", "EMERGENCY")
                        world.hud.notification(f'🚨 PROHIBITED AREA at {distance:.1f}m!')
                        return True, distance

                # Check for lane width changes indicating road ending
                if future_waypoint and current_waypoint.lane_width > 0:
                    if future_waypoint.lane_width < current_waypoint.lane_width * 0.5:  # Lane width reduced by 50%
                        if hasattr(world, 'log_message'):
                            world.log_message(f"BOUNDARY_VIOLATION: Lane width reduction at {distance:.1f}m", "EMERGENCY")
                        world.hud.notification(f'🚨 LANE ENDING at {distance:.1f}m!')
                        return True, distance

            return False, float('inf')

        except Exception as e:
            if hasattr(world, 'log_message'):
                world.log_message(f"BOUNDARY_CHECK_ERROR: {str(e)}", "ERROR")
            print(f"Road boundary check error: {e}")
            return False, float('inf')

    def _get_closest_obstacle_distance(self, world):
        """
        Get distance to closest obstacle and check emergency conditions.

        Args:
            world: CARLA world instance

        Returns:
            tuple: (min_distance, emergency_brake, brake_reason)

        Note:
            Prioritizes road boundary violations over obstacle detection.
        """
        min_distance = float('inf')
        emergency_brake = False
        brake_reason = ""

        try:
            # PRIORITY 1: Check road boundaries first - this is critical for sidewalk crossing
            road_violation, road_distance = self._check_road_boundaries(world)
            if road_violation:
                emergency_brake = True
                brake_reason = f"Road boundary violation at {road_distance:.1f}m"
                min_distance = min(min_distance, road_distance)

                # Force immediate emergency brake for road violations
                if hasattr(world, 'log_emergency_brake_event'):
                    world.log_emergency_brake_event(road_distance, brake_reason)

                world.hud.notification(f'🚨 EMERGENCY BRAKE: {brake_reason}')
                return min_distance, True, brake_reason  # Return immediately for road violations

            # PRIORITY 2: Check obstacle detection sensor
            if world.obstacle_detection and hasattr(world.obstacle_detection, 'obstacles'):
                for obstacle in world.obstacle_detection.obstacles:
                    distance = obstacle.distance
                    min_distance = min(min_distance, distance)

                    # Emergency brake for very close obstacles
                    if distance < Config.emergency_brake_distance:
                        emergency_brake = True
                        if not brake_reason:
                            brake_reason = f"Obstacle at {distance:.1f}m"

            # Log emergency brake event for obstacles
            if emergency_brake and "boundary" not in brake_reason:
                world.hud.notification(f'🚨 EMERGENCY BRAKE: {brake_reason}')
                if hasattr(world, 'log_emergency_brake_event'):
                    world.log_emergency_brake_event(min_distance, brake_reason)

            return min_distance, emergency_brake, brake_reason

        except Exception as e:
            if hasattr(world, 'log_message'):
                world.log_message(f"OBSTACLE_DETECTION_ERROR: {str(e)}", "ERROR")
            print(f"Error getting obstacle distance: {e}")
            return float('inf'), False, ""

    def is_emergency_brake_active(self):
        """Check if emergency brake is currently active."""
        return self.emergency_brake_active

    def set_agent_type(self, agent_type, behavior="normal"):
        """Change the agent type (Basic, Behavior, Constant)."""
        if not CARLA_AGENTS_AVAILABLE:
            print("WARNING: Cannot change agent type - CARLA agents not available")
            return

        self.agent_type = agent_type
        self.behavior = behavior
        if self.enabled:
            self._initialize_agent()
            self._set_random_destination()

    def _clamp(self, value, min_value, max_value):
        """Clamp value between min and max."""
        return max(min_value, min(value, max_value))
