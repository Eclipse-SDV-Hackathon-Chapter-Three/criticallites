"""
Input handling and keyboard control for JACCUS.

This module provides comprehensive keyboard input handling for vehicle control,
camera management, autopilot toggle, ACC system control, and various
simulation features in the CARLA environment.

Classes:
    KeyboardControl: Main keyboard input processor and vehicle controller
    MouseControl: Mouse-based input handling (if implemented)

Key Bindings:
    WASD/Arrows: Vehicle movement control
    J: Toggle Adaptive Cruise Control (ACC)
    +/-: Adjust ACC target speed
    P: Toggle autopilot
    Q: Toggle reverse gear
    H: Show help system
"""

import pygame
import carla
from ..core.config import Config


class KeyboardControl(object):
    """
    Keyboard input handler for comprehensive vehicle control.

    Manages all keyboard inputs for vehicle operation, camera control,
    ACC system integration, autopilot management, and simulation features.

    Args:
        world: CARLA world instance
        start_in_autopilot (bool): Whether to start with autopilot enabled
        acc: Adaptive Cruise Control system instance for integration

    Attributes:
        _autopilot_enabled (bool): Current autopilot state
        _control (carla.VehicleControl): Vehicle control state
        _lights (carla.VehicleLightState): Vehicle lighting state
        acc: Reference to ACC system for speed control integration
        world: CARLA world reference for notifications and control

    Note:
        Supports both manual control and ACC system integration with
        seamless switching between control modes.
    """

    def __init__(self, world, start_in_autopilot=True, acc=None):
        self._autopilot_enabled = start_in_autopilot
        self._control = carla.VehicleControl()
        self._lights = carla.VehicleLightState.NONE
        world.player.set_autopilot(self._autopilot_enabled)
        world.player.set_light_state(self._lights)
        world.hud.notification("Press 'H' or '?' for help.", seconds=4.0)

        # ACC reference
        self.acc = acc

        # Store world reference for notifications
        self.world = world

        # Ackermann controller setup
        self._ackermann_enabled = False
        self._ackermann_reverse = 1
        self._ackermann_control = carla.VehicleAckermannControl()
        self._ackermann_max_speed_fast = 40.0
        self._ackermann_max_speed_slow = 10.0
        self._ackermann_max_speed = self._ackermann_max_speed_slow

    def parse_events(self, client, world, clock, sync_mode):
        """Parse pygame events and handle input."""
        if isinstance(self._control, carla.VehicleControl):
            current_lights = self._lights

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            elif event.type == pygame.KEYUP:
                if self._is_quit_shortcut(event.key):
                    return True
                elif event.key == pygame.K_BACKQUOTE:
                    world.camera_manager.toggle_camera()
                elif event.key == pygame.K_TAB:
                    world.camera_manager.next_sensor()
                elif event.key == pygame.K_c and pygame.key.get_pressed()[pygame.K_LSHIFT]:
                    world.next_weather(reverse=True)
                elif event.key == pygame.K_c:
                    world.next_weather()
                elif event.key == pygame.K_g:
                    world.toggle_radar()
                elif event.key == pygame.K_BACKSPACE:
                    if self._autopilot_enabled:
                        world.player.set_autopilot(False)
                        world.restart()
                        world.player.set_autopilot(True)
                    else:
                        world.restart()
                elif event.key == pygame.K_h or (event.key == pygame.K_SLASH and pygame.key.get_pressed()[pygame.K_LSHIFT]):
                    world.hud.help.toggle()
                elif event.key == pygame.K_i:
                    world.hud.toggle_info()
                elif event.key == pygame.K_l and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    current_lights ^= carla.VehicleLightState.Special1
                elif event.key == pygame.K_l and pygame.key.get_pressed()[pygame.K_LSHIFT]:
                    current_lights ^= carla.VehicleLightState.HighBeam
                elif event.key == pygame.K_l:
                    # Use 'L' key to toggle between lights:
                    # closed -> position -> low beam -> fog
                    if not self._lights & carla.VehicleLightState.Position:
                        world.hud.notification("Position lights")
                        current_lights |= carla.VehicleLightState.Position
                    elif not self._lights & carla.VehicleLightState.LowBeam:
                        world.hud.notification("Low beam lights")
                        current_lights |= carla.VehicleLightState.LowBeam
                    elif not self._lights & carla.VehicleLightState.Fog:
                        world.hud.notification("Fog lights")
                        current_lights |= carla.VehicleLightState.Fog
                    else:
                        world.hud.notification("Lights off")
                        current_lights ^= carla.VehicleLightState.Position
                        current_lights ^= carla.VehicleLightState.LowBeam
                        current_lights ^= carla.VehicleLightState.Fog
                elif event.key == pygame.K_p and not pygame.key.get_pressed()[pygame.K_LCTRL]:
                    if not self._autopilot_enabled and not sync_mode:
                        print("WARNING: You are currently in asynchronous mode and could "
                              "experience some issues with the traffic simulation")
                    self._autopilot_enabled = not self._autopilot_enabled
                    world.player.set_autopilot(self._autopilot_enabled)
                    world.hud.notification(
                        'Autopilot %s' % ('On' if self._autopilot_enabled else 'Off'))
                elif event.key == pygame.K_o:
                    try:
                        if world.map.name.endswith('01'):
                            world.load_world('Town02')
                        elif world.map.name.endswith('02'):
                            world.load_world('Town01')
                        else:
                            world.load_world('Town01')
                    except Exception as error:
                        print('load_world() failed: %s' % error)
                elif event.key == pygame.K_b:
                    self.toggle_ackermann()
                    world.hud.show_ackermann_info(self._ackermann_enabled)
                    world.hud.notification(
                        'Ackermann Controller %s' % ('On' if self._ackermann_enabled else 'Off'))

                # ACC Controls
                elif event.key == pygame.K_j:
                    if self.acc:
                        self.acc.toggle()
                        status = "ON" if self.acc.enabled else "OFF"
                        world.hud.notification(f'ACC {status}')

                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    if self.acc and self.acc.enabled:
                        self.acc.increase_target_speed()
                        world.hud.notification(f'ACC Target: {self.acc.target_speed:.1f} km/h')

                elif event.key == pygame.K_MINUS:
                    if self.acc and self.acc.enabled:
                        self.acc.decrease_target_speed()
                        world.hud.notification(f'ACC Target: {self.acc.target_speed:.1f} km/h')

                elif event.key == pygame.K_r and not (pygame.key.get_pressed()[pygame.K_LCTRL] or pygame.key.get_pressed()[pygame.K_LSHIFT]):
                    world.camera_manager.toggle_recording()
                elif event.key == pygame.K_r and pygame.key.get_pressed()[pygame.K_LSHIFT]:
                    world.camera_manager.toggle_recording(sensor='lidar')
                elif event.key == pygame.K_r and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    if world.recording_enabled:
                        client.stop_recorder()
                        world.recording_enabled = False
                        world.hud.notification("Recorder is OFF")
                    else:
                        client.start_recorder("manual_recording.rec")
                        world.recording_enabled = True
                        world.hud.notification("Recorder is ON")
                elif event.key == pygame.K_p and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    # stop recorder
                    client.stop_recorder()
                    world.recording_enabled = False
                    # work around to fix camera at start of replaying
                    current_index = world.camera_manager.index
                    world.destroy_sensors()
                    # disable autopilot
                    self._autopilot_enabled = False
                    world.player.set_autopilot(self._autopilot_enabled)
                    world.hud.notification("Replaying file 'manual_recording.rec'")
                    # replayer
                    client.replay_file("manual_recording.rec", world.recording_start, 0, 0)
                    world.camera_manager.set_sensor(current_index)
                elif event.key == pygame.K_MINUS and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    if pygame.key.get_pressed()[pygame.K_LSHIFT]:
                        world.recording_start -= 10
                    else:
                        world.recording_start -= 1
                    world.hud.notification("Recording start time is %d" % world.recording_start)
                elif event.key == pygame.K_EQUALS and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    if pygame.key.get_pressed()[pygame.K_LSHIFT]:
                        world.recording_start += 10
                    else:
                        world.recording_start += 1
                    world.hud.notification("Recording start time is %d" % world.recording_start)

        if not self._autopilot_enabled:
            if isinstance(self._control, carla.VehicleControl):
                self._parse_vehicle_keys(pygame.key.get_pressed(), clock.get_time())
                self._control.reverse = self._control.gear < 0
                # Set automatic control-related vehicle lights
                if self._control.brake:
                    current_lights |= carla.VehicleLightState.Brake
                else: # Remove the Brake flag
                    current_lights &= ~carla.VehicleLightState.Brake
                if self._control.reverse:
                    current_lights |= carla.VehicleLightState.Reverse
                else: # Remove the Reverse flag
                    current_lights &= ~carla.VehicleLightState.Reverse
                if current_lights != self._lights: # Change the light state only if necessary
                    self._lights = current_lights
                    world.player.set_light_state(carla.VehicleLightState(self._lights))

                # Apply control
                if not self._ackermann_enabled:
                    # Check if ACC should control braking/throttle
                    if self.acc and self.acc.enabled:
                        control = self.acc.update_control(self._control, world)
                        world.player.apply_control(control)
                    else:
                        world.player.apply_control(self._control)

        if self._ackermann_enabled:
            self._parse_ackermann_keys(pygame.key.get_pressed(), clock.get_time())
            world.hud.update_ackermann_control(self._ackermann_control)
            world.player.apply_ackermann_control(self._ackermann_control)

    def toggle_ackermann(self):
        """Toggle Ackermann controller mode."""
        self._ackermann_enabled = not self._ackermann_enabled

    def _parse_vehicle_keys(self, keys, milliseconds):
        """Parse vehicle control keys."""
        # Allow manual throttle override, especially during emergency brake
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self._control.throttle = min(self._control.throttle + 0.01, 1.00)
            # Override emergency brake if user wants to accelerate
            if self.acc and self.acc.enabled and hasattr(self.acc, 'emergency_brake_active'):
                if self.acc.emergency_brake_active:
                    self._control.brake = 0.0  # Release emergency brake
                    if hasattr(self, 'world') and hasattr(self.world, 'hud'):
                        self.world.hud.notification('Manual override - Emergency brake released')
        else:
            self._control.throttle = 0.0

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            # Allow reverse during emergency brake
            if (self.acc and self.acc.enabled and
                hasattr(self.acc, 'emergency_brake_active') and
                self.acc.emergency_brake_active):
                # Enable reverse gear to back away from obstacle
                self._control.gear = -1
                self._control.brake = 0.0
                self._control.throttle = 0.3  # Gentle reverse
                if hasattr(self, 'world') and hasattr(self.world, 'hud'):
                    self.world.hud.notification('Reversing to escape obstacle')
            else:
                # Normal brake behavior
                self._control.brake = min(self._control.brake + 0.2, 1)
                # Disable ACC if manual brake is applied
                if self.acc and self.acc.enabled:
                    self.acc.enabled = False
                    # Use stored world reference for notifications
                    if hasattr(self, 'world') and hasattr(self.world, 'hud'):
                        self.world.hud.notification('ACC disabled - Manual brake applied')
        else:
            # Only reset brake if ACC is not controlling it
            if not (self.acc and self.acc.enabled):
                self._control.brake = 0
            # Reset gear to forward
            self._control.gear = 1

        # Manual steering - overrides lane keeping assistance
        manual_steer = False
        steer_increment = 5e-4 * milliseconds
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if self._control.steer > -1.0:
                self._control.steer = max(-1., min(self._control.steer - steer_increment, 0))
            manual_steer = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if self._control.steer < 1.0:
                self._control.steer = min(1., max(self._control.steer + steer_increment, 0))
            manual_steer = True
        else:
            if not manual_steer:  # Only reset if no manual input
                self._control.steer = 0.0

        # Set manual override flag for ACC lane keeping
        if self.acc and hasattr(self.acc, 'manual_steer_override'):
            self.acc.manual_steer_override = manual_steer
            if manual_steer:
                self.acc.lane_correction_steer = 0.0  # Clear any lane correction

        self._control.hand_brake = keys[pygame.K_SPACE]

    def _parse_ackermann_keys(self, keys, milliseconds):
        """Parse Ackermann controller keys."""
        second_per_simulation_step = milliseconds / 1000
        speed_increment = 5.0 * second_per_simulation_step  # 5.0 m/s^2

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self._ackermann_control.speed = min(
                self._ackermann_control.speed + speed_increment,
                self._ackermann_max_speed
            )
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self._ackermann_control.speed = max(
                self._ackermann_control.speed - speed_increment,
                -self._ackermann_max_speed
            )

        steer_increment = 1e-2 * milliseconds
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if self._ackermann_control.steer > -1.0:
                self._ackermann_control.steer = max(-1., min(
                    self._ackermann_control.steer - steer_increment, 0))
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if self._ackermann_control.steer < 1.0:
                self._ackermann_control.steer = min(1., max(
                    self._ackermann_control.steer + steer_increment, 0))
        else:
            self._ackermann_control.steer = 0.0

        # toggle fast/slow max speed
        if keys[pygame.K_LSHIFT]:
            self._ackermann_max_speed = self._ackermann_max_speed_fast
        else:
            self._ackermann_max_speed = self._ackermann_max_speed_slow

    @staticmethod
    def _is_quit_shortcut(key):
        """Check if key combination is quit shortcut."""
        return (key == pygame.K_ESCAPE) or (key == pygame.K_q and pygame.key.get_pressed()[pygame.K_LCTRL])


class MouseControl(object):
    """Mouse input handler."""

    def __init__(self):
        self._steer_cache = 0.0

    def parse_events(self, world, clock, sync_mode):
        """Parse mouse events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    return True
                elif event.key == pygame.K_h or (event.key == pygame.K_SLASH and pygame.key.get_pressed()[pygame.K_LSHIFT]):
                    world.hud.help.toggle()
                elif event.key == pygame.K_TAB:
                    world.camera_manager.next_sensor()

        return False
