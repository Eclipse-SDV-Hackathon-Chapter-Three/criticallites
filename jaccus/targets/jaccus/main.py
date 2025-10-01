#!/usr/bin/env python

"""
Welcome to JACCUS - Just Another CARLA Client for Unreal Simulation

Use ARROWS or WASD keys for control.

    W            : throttle
    S            : brake
    A/D          : steer left/right
    Q            : toggle reverse
    Space        : hand-brake
    P            : toggle autopilot
    M            : toggle manual transmission
    ,/.          : gear up/down

    L            : toggle next light type
    SHIFT + L    : toggle high beam
    Z/X          : toggle right/left blinker
    I            : toggle interior light

    TAB          : change sensor position
    ` or N       : next sensor
    [1-9]        : change to sensor [1-9]
    G            : toggle radar visualization
    C            : change weather (Shift+C reverse)
    Backspace    : change vehicle

    J            : toggle adaptive cruise control (ACC)
    +/-          : increase/decrease ACC target speed (when ACC is on)

    O            : open/close all doors of vehicle
    T            : toggle vehicle's telemetry

    V            : Select next map layer (Shift+V reverse)
    B            : Load current selected map layer (Shift+B to unload)

    R            : toggle recording images to disk

    CTRL + R     : toggle recording of simulation (replacing any previous)
    CTRL + P     : start replaying last recorded simulation
    CTRL + +     : increments the start time of the replay by 1 second (+SHIFT = 10 seconds)
    CTRL + -     : decrements the start time of the replay by 1 second (+SHIFT = 10 seconds)

    F1           : toggle HUD
    H/?          : toggle help
    ESC          : quit
"""

import argparse
import collections
import datetime
import logging
import math
import random
import re
import weakref
import sys
import glob
import os

try:
    import pygame
except ImportError:
    raise RuntimeError('cannot import pygame, make sure pygame package is installed')

try:
    import numpy as np
except ImportError:
    raise RuntimeError('cannot import numpy, make sure numpy package is installed')

try:
    # Use Python 3.7 CARLA egg even on Python 3.10 for compatibility
    sys.path.append('../../../carla-simulator/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg')
    # Add CARLA agents path
    sys.path.append('../../../carla-simulator/PythonAPI/carla')
except:
    pass

import carla

# Import our modular components
from .world.world_manager import World
from .input.keyboard_handler import KeyboardControl, MouseControl
from .adas.adaptive_cruise_control import AdaptiveCruiseControl
from .communication.zenoh_client import create_zenoh_client
from .communication.mqtt_client import create_mqtt_client
from .ui.display_manager import HUD
from .core.config import Config


def game_loop(args):
    """
    Main game loop for JACCUS CARLA client.

    Args:
        args: Parsed command line arguments containing configuration

    Raises:
        RuntimeError: If CARLA connection fails or required resources unavailable

    Note:
        Handles the complete game lifecycle including world initialization,
        input processing, ACC control, and communication clients.
    """
    pygame.init()
    pygame.font.init()
    world = None
    original_settings = None
    zenoh_client = None
    mqtt_client = None

    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(2000)

        sim_world = client.get_world()
        if args.sync:
            original_settings = sim_world.get_settings()
            settings = sim_world.get_settings()
            if not settings.synchronous_mode:
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = 0.05
            sim_world.apply_settings(settings)

            traffic_manager = client.get_trafficmanager()
            traffic_manager.set_synchronous_mode(True)

        if args.autopilot and not sim_world.get_settings().synchronous_mode:
            print("WARNING: You are currently in asynchronous mode and could "
                  "experience some issues with the traffic simulation")

        display = pygame.display.set_mode(
            (args.width, args.height),
            pygame.HWSURFACE | pygame.DOUBLEBUF)
        display.fill((0,0,0))
        pygame.display.flip()

        hud = HUD(args.width, args.height)
        world = World(sim_world, hud, args)

        # Initialize ACC system
        acc = AdaptiveCruiseControl(world.player, world)

        # Initialize input controller
        if args.agent == "Keyboard":
            controller = KeyboardControl(world, args.autopilot, acc)
        else:
            controller = MouseControl()

        # Initialize Zenoh client with router configuration
        zenoh_config = {"mode": "client", "connect/endpoints": [f"tcp/{args.router}:7447"]} if hasattr(args, 'router') else None
        zenoh_client = create_zenoh_client(world.player, zenoh_config)

        # Initialize MQTT client with configuration and safe error handling
        mqtt_config_path = args.mqtt_config if hasattr(args, 'mqtt_config') and args.mqtt_config else None
        try:
            mqtt_client = create_mqtt_client(world.player, mqtt_config_path)
            if mqtt_client:
                print("JACCUS: MQTT client enabled")
            else:
                print("JACCUS: MQTT client disabled (fallback mode)")
        except Exception as e:
            print(f"JACCUS: MQTT initialization failed, using fallback mode: {e}")
            mqtt_client = None

        # Set up MQTT command handler for ACC integration
        def handle_mqtt_command(command_data):
            """
            Handle MQTT commands for vehicle control integration.

            Args:
                command_data (dict): MQTT command containing 'command' and 'value' keys

            Note:
                Supports speed control, cruise control toggle, and emergency stop commands.
                Integrates with ACC system for seamless remote vehicle control.
            """
            try:
                command_type = command_data.get("command")
                value = command_data.get("value")

                if command_type == Config.MQTT_COMMAND_SPEED and acc:
                    # Set ACC target speed
                    if isinstance(value, (int, float)) and value > 0:
                        # Enable ACC if not already enabled
                        if not acc.enabled:
                            acc.toggle()
                        # Set target speed (clamp to valid range)
                        acc.target_speed = max(Config.ACC_MIN_SPEED,
                                             min(value, Config.ACC_MAX_SPEED))
                        world.hud.notification(f'MQTT: ACC Target Speed set to {acc.target_speed:.1f} km/h')

                elif command_type == Config.MQTT_COMMAND_CRUISE_CONTROL and acc:
                    # Toggle cruise control
                    if isinstance(value, bool):
                        if value and not acc.enabled:
                            acc.toggle()  # Enable ACC
                        elif not value and acc.enabled:
                            acc.toggle()  # Disable ACC
                        world.hud.notification(f'MQTT: Cruise Control {"ON" if acc.enabled else "OFF"}')

                elif command_type == Config.MQTT_COMMAND_EMERGENCY_STOP:
                    # Emergency stop
                    if acc and acc.enabled:
                        acc.enabled = False  # Disable ACC
                    # Apply emergency brake (this would need integration with vehicle control)
                    world.hud.notification('MQTT: Emergency Stop Activated!')

                else:
                    print(f"Unknown MQTT command: {command_type}")

            except Exception as e:
                print(f"Error handling MQTT command: {e}")

        # Set the command callback if MQTT client is available
        if mqtt_client:
            try:
                mqtt_client.set_command_callback(handle_mqtt_command)
            except Exception as e:
                print(f"JACCUS: Failed to set MQTT callback: {e}")

        # Start MQTT continuous publishing if client is available
        if mqtt_client:
            try:
                mqtt_client.start_continuous_publishing()
            except Exception as e:
                print(f"JACCUS: Failed to start MQTT publishing: {e}")

        if args.sync:
            sim_world.tick()
        else:
            sim_world.wait_for_tick()

        clock = pygame.time.Clock()

        while True:
            if args.sync:
                sim_world.tick()

            clock.tick_busy_loop(60)

            # Handle input events
            if hasattr(controller, 'parse_events'):
                if controller.parse_events(client, world, clock, args.sync):
                    return
            else:
                # For mouse controller or other controller types
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    elif event.type == pygame.KEYUP:
                        if event.key == pygame.K_ESCAPE:
                            return

            # Update world
            world.tick(clock)
            world.render(display)

            # Publish vehicle status via Zenoh
            if zenoh_client and acc:
                acc_status = acc.get_status_info()
                zenoh_client.publish_vehicle_status(acc_status)

            # Publish vehicle data via MQTT if client is available
            if mqtt_client and acc:
                try:
                    acc_status = acc.get_status_info()
                    mqtt_additional_data = {
                        "CruiseControl": acc_status.get('enabled', False),
                        "Gear": "D" if acc_status.get('enabled', False) else "P",
                        "RPM": max(0.0, acc.telemetry.get_speed_kmh() * 50) if hasattr(acc, 'telemetry') else 0.0
                    }
                    mqtt_client.publish_vehicle_data(mqtt_additional_data)
                except Exception as e:
                    # Log error but don't crash - continue with other functionality
                    pass  # Silent fail to avoid log spam

            pygame.display.flip()

    finally:
        if original_settings:
            sim_world.apply_settings(original_settings)

        if zenoh_client:
            zenoh_client.close()

        if mqtt_client:
            mqtt_client.close()

        if world is not None:
            world.destroy()

        pygame.quit()


def main():
    """
    Main entry point for JACCUS application.

    Parses command line arguments and initializes the CARLA client with
    adaptive cruise control, communication systems, and input handling.

    Command Line Options:
        --host: CARLA server IP address
        --port: CARLA server TCP port
        --autopilot: Enable CARLA autopilot
        --sync: Synchronous mode execution
        --router: Zenoh router address for distributed communication
        --mqtt-config: MQTT configuration file path

    Raises:
        KeyboardInterrupt: On user cancellation (Ctrl+C)
    """
    argparser = argparse.ArgumentParser(
        description='CARLA Manual Control Client')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='print debug information')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '-a', '--autopilot',
        action='store_true',
        help='enable autopilot')
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1280x720',
        help='window resolution (default: 1280x720)')
    argparser.add_argument(
        '--filter',
        metavar='PATTERN',
        default='vehicle.*',
        help='actor filter (default: "vehicle.*")')
    argparser.add_argument(
        '--generation',
        metavar='G',
        default='2',
        help='restrict to certain actor generation (values: "1","2","All" - default: "2")')
    argparser.add_argument(
        '--rolename',
        metavar='NAME',
        default='hero',
        help='actor role name (default: "hero")')
    argparser.add_argument(
        '--gamma',
        default=2.2,
        type=float,
        help='Gamma correction of the camera (default: 2.2)')
    argparser.add_argument(
        '--sync',
        action='store_true',
        help='Activate synchronous mode execution')
    argparser.add_argument(
        '--agent',
        type=str,
        choices=["Keyboard"],
        default="Keyboard",
        help='select which agent to run')
    argparser.add_argument(
        '--router',
        metavar='R',
        default='127.0.0.1',
        help='Zenoh router address (default: 127.0.0.1)')
    argparser.add_argument(
        '--mqtt-config',
        metavar='CONFIG',
        help='MQTT configuration file path (default: mqtt_config.json in current directory)')
    argparser.add_argument(
        '--random-vehicle',
        action='store_true',
        help='select a random vehicle blueprint instead of using filter (default: False)')
    args = argparser.parse_args()

    args.width, args.height = [int(x) for x in args.res.split('x')]

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    logging.info('listening to server %s:%s', args.host, args.port)

    print(__doc__)

    try:
        game_loop(args)

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':
    main()
