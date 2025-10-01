# JACCUS Enhanced Controls - Quick Reference

## J Key Enhanced Functionality

Press `J` to cycle through autonomous driving modes:

### Mode 1: Manual Control
- **Status**: "Manual Control"
- **Behavior**: Full driver control
- **HUD**: No automated systems active
- **Usage**: Normal driving, full manual input required

### Mode 2: ACC (Adaptive Cruise Control)
- **Status**: "ACC (Speed Control)"
- **Behavior**: Maintains target speed, avoids obstacles
- **HUD**: Shows target speed and distance to vehicles
- **Usage**: Highway driving with manual steering
- **Controls**:
  - `+/-` keys adjust target speed
  - Driver maintains steering control
  - Automatic braking for obstacles

### Mode 3: Full Autonomous
- **Status**: "Full Autonomous Mode"
- **Behavior**: Complete automated driving
- **HUD**: Shows BehaviorAgent status and destination
- **Usage**: Controlled environment autonomous driving
- **Features**:
  - Automatic steering and speed control
  - Traffic light and sign recognition
  - Lane keeping and path planning
  - Obstacle avoidance

## Emergency Features

### Emergency Braking
- Activates automatically in ACC and Autonomous modes
- Distance calculated dynamically based on speed
- Manual override always available
- Provides progressive braking force

### Manual Override
- Any manual input (steering, brake, throttle) overrides automation
- System provides smooth transition back to manual control
- Safety notifications displayed on HUD

## Status Indicators

### HUD Notifications
- Mode changes shown with clear text
- BehaviorAgent status when available
- Emergency braking alerts
- Target speed and distance information

### Console Logging
- Detailed mode transition logs
- BehaviorAgent initialization status
- Emergency braking activation logs
- Fallback mode notifications

## Quick Start

1. **Launch JACCUS**: `just run-jaccus`
2. **Start in Manual**: System always starts in manual mode
3. **Enable ACC**: Press `J` once for speed control
4. **Full Autonomous**: Press `J` again for complete automation
5. **Return to Manual**: Press `J` third time to cycle back

## Troubleshooting

### If Autonomous Mode Not Working
- Check CARLA simulator connection
- Verify BehaviorAgent availability in console
- System will show "Fallback mode" if agents unavailable
- ACC speed control still functions without BehaviorAgent

### If Emergency Braking Too Sensitive
- Adjust `EMERGENCY_BRAKE_BASE_DISTANCE` in config
- Modify `EMERGENCY_BRAKE_SPEED_FACTOR` for speed sensitivity
- Check collision sensor placement and range

### If Mode Switching Not Working
- Verify J key binding in keyboard handler
- Check HUD notifications for error messages
- Review console output for initialization errors
- Ensure proper world and vehicle initialization

## Advanced Configuration

Edit `/home/seame/criticallites/jaccus/targets/jaccus/core/config.py`:

```python
# Autonomous behavior
AUTONOMOUS_DEFAULT_BEHAVIOR = "normal"  # "cautious", "normal", "aggressive"
AUTONOMOUS_TARGET_SPEED = 50.0         # Default autonomous speed

# Emergency braking sensitivity
EMERGENCY_BRAKE_BASE_DISTANCE = 5.0    # Minimum stopping distance
EMERGENCY_BRAKE_SPEED_FACTOR = 0.3     # Speed-based distance factor

# ACC parameters
ACC_DEFAULT_TARGET_SPEED = 60.0        # Default ACC speed
ACC_SAFE_DISTANCE = 20.0              # Following distance
```

## Integration with MQTT

Send commands via MQTT for remote control:

```bash
# Set cruise control speed
mosquitto_pub -t "vehicle/commands" -m '{"command":"speed","value":55}'

# Toggle cruise control
mosquitto_pub -t "vehicle/commands" -m '{"command":"cruise_control","value":true}'

# Emergency stop
mosquitto_pub -t "vehicle/commands" -m '{"command":"emergency_stop","value":true}'
```

## Safety Notes

- Always monitor autonomous systems
- Keep hands near steering wheel in autonomous mode
- Manual input always overrides automation
- Test in safe, controlled environments first
- Emergency braking may activate suddenly - be prepared
