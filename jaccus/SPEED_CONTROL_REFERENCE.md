# JACCUS Speed Control System Reference

## Overview
This document provides complete documentation for the JACCUS (Just Another CARLA Client for Unreal Simulation) speed control system, including PID parameters, emergency braking, reverse gear functionality, and maintenance procedures.

## System Architecture

### 1. Adaptive Cruise Control (ACC) System
- **Primary File**: `jaccus/adas/adaptive_cruise_control.py`
- **Config File**: `jaccus/core/config.py`
- **Dependencies**: CARLA 0.9.15 PythonAPI, BehaviorAgent (optional)

### 2. Input Handling System
- **Primary File**: `jaccus/input/keyboard_handler.py`
- **Dependencies**: pygame, vehicle control state management

### 3. World Management & Logging
- **Primary File**: `jaccus/world/world_manager.py`
- **Log Output**: `jaccus_run.log` (comprehensive logging)

## Speed Control Parameters

### PID Controller Constants (config.py Lines 25-32)
```python
# Enhanced PID Controller Parameters
PID_KP = 1.2                      # Proportional gain (increased for better response)
PID_KI = 0.15                     # Integral gain (prevents steady-state error)
PID_KD = 0.3                      # Derivative gain (reduces overshoot)
PID_INTEGRAL_LIMIT = 20.0         # Prevent integral windup
PID_THROTTLE_SCALE_NORMAL = 8.0   # Normal throttle scaling factor
PID_THROTTLE_SCALE_AGGRESSIVE = 15.0  # Aggressive scaling for large errors
PID_LARGE_ERROR_THRESHOLD = 4.0   # km/h error threshold for aggressive scaling
```

### Speed Control Behavior (adaptive_cruise_control.py Lines 270-295)
```python
# Dynamic throttle scaling for large speed errors
if speed_error > 4.0:  # Large speed deficit - boost throttle
    throttle_scale = 15.0  # More aggressive scaling
    base_control.throttle = min(0.9, pid_output / throttle_scale)
else:
    throttle_scale = 8.0   # Normal scaling
    base_control.throttle = min(0.7, pid_output / throttle_scale)
```

## Emergency Brake System

### Configuration Parameters (config.py Lines 34-39)
```python
# Emergency Brake System Parameters
EMERGENCY_BRAKE_DISTANCE = 5.0    # meters - immediate emergency brake
EMERGENCY_BRAKE_WARNING_DISTANCE = 15.0  # meters - warning zone
SIDEWALK_DETECTION_DISTANCES = [3.0, 6.0, 10.0, 15.0]  # meters - lookahead distances
MIN_LANE_WIDTH = 2.5              # meters - minimum acceptable lane width
REVERSE_GEAR_MAX_SPEED = 5.0      # km/h - maximum speed to engage reverse
```

### Road Boundary Detection (adaptive_cruise_control.py Lines 183-220)
The `_check_road_boundaries()` method detects:
- Sidewalk crossings using CARLA waypoint analysis
- Road boundary violations through forward projection
- Lane width restrictions (< 2.5m triggers emergency brake)
- Multiple lookahead distances (3m, 6m, 10m, 15m) for early detection

### Emergency Brake Triggers
1. **Obstacle Detection**: Distance ≤ 5.0 meters
2. **Sidewalk Crossing**: Waypoint analysis shows sidewalk ahead
3. **Road Boundary**: No valid waypoint found in forward projection
4. **Narrow Lane**: Current lane width < 2.5 meters

## Reverse Gear System (Q Key)

### Implementation (keyboard_handler.py Lines 123-140)
```python
# Q Key Reverse Gear Control
elif event.key == pygame.K_q:
    if not self._autopilot_enabled:  # Only allow in manual mode
        if self._gear_state == "Forward":
            self._gear_state = "Reverse"
            self._reverse_enabled = True
            world.hud.notification('Gear: REVERSE (Q key activated)')
        elif self._gear_state == "Reverse":
            self._gear_state = "Forward"
            self._reverse_enabled = False
            world.hud.notification('Gear: FORWARD (Q key deactivated)')
```

### Safety Interlocks (keyboard_handler.py Lines 215-235)
- **Speed Limit**: Reverse only engaged if speed ≤ 5.0 km/h
- **Throttle Limiting**: Maximum 0.4 throttle in reverse
- **Autopilot Protection**: Cannot change gear when autopilot active
- **Emergency Override**: Allows reverse during emergency brake situations

## Comprehensive Logging System

### Log File Location
- **File**: `jaccus_run.log` (created in current working directory)
- **Format**: `[YYYY-MM-DD HH:MM:SS.mmm] CATEGORY: Message`

### Logged Events
1. **Speed Control**: Target speed, current speed, PID output, throttle/brake values
2. **Emergency Brake**: Distance, reason, activation/deactivation
3. **Gear Changes**: Old gear, new gear, method (Q key, emergency, etc.)
4. **System Events**: ACC on/off, agent initialization, warnings
5. **Road Boundaries**: Sidewalk detection, waypoint analysis results

### Example Log Entries
```
[2024-01-15 14:32:15.123] SPEED_CONTROL: Target=20.0km/h, Current=15.4km/h, Error=4.6km/h, Action=Throttle, Value=0.307
[2024-01-15 14:32:16.456] EMERGENCY: EMERGENCY_BRAKE_ACTIVATED: Distance=3.2m, Reason=Sidewalk/Road boundary detected
[2024-01-15 14:32:17.789] VEHICLE: GEAR_CHANGE: Forward -> Reverse, Method=Q key manual
```

## Troubleshooting & Maintenance

### Common Issues and Solutions

#### 1. Speed Control Plateau (Stuck at 15.4 km/h)
**Symptoms**: Vehicle cannot reach target speed, throttle limited to 0.23-0.24
**Solution**:
- Check PID parameters in `config.py`
- Verify aggressive scaling triggers for errors > 4.0 km/h
- Review log file for PID output values
- Ensure fallback controller is active when BehaviorAgent unavailable

#### 2. Emergency Brake Not Triggering
**Symptoms**: Vehicle continues toward sidewalk without braking
**Solution**:
- Verify `_check_road_boundaries()` method implementation
- Check CARLA waypoint system functionality
- Review sidewalk detection distances in config
- Test with different CARLA map configurations

#### 3. Q Key Reverse Not Working
**Symptoms**: Q key press has no effect on gear state
**Solution**:
- Ensure autopilot is disabled (P key)
- Check vehicle speed (must be ≤ 5.0 km/h)
- Verify keyboard handler initialization
- Review gear state management in parse_events

### Performance Tuning

#### PID Parameter Optimization
1. **Proportional Gain (KP)**: Increase for faster response, decrease for stability
2. **Integral Gain (KI)**: Increase to eliminate steady-state error
3. **Derivative Gain (KD)**: Increase to reduce overshoot

#### Throttle Scaling Adjustment
- **Normal Scale**: Adjust `PID_THROTTLE_SCALE_NORMAL` (default: 8.0)
- **Aggressive Scale**: Adjust `PID_THROTTLE_SCALE_AGGRESSIVE` (default: 15.0)
- **Error Threshold**: Modify `PID_LARGE_ERROR_THRESHOLD` (default: 4.0 km/h)

### Testing Procedures

#### 1. Speed Control Verification
```bash
# Run JACCUS with ACC enabled
python jaccus/main.py --sync
# Press J to enable ACC
# Press + to set target speed to 20+ km/h
# Monitor jaccus_run.log for speed control decisions
tail -f jaccus_run.log | grep SPEED_CONTROL
```

#### 2. Emergency Brake Testing
```bash
# Position vehicle near sidewalk crossing
# Enable ACC and observe emergency brake activation
# Check log for emergency brake events
grep EMERGENCY_BRAKE jaccus_run.log
```

#### 3. Reverse Gear Testing
```bash
# Ensure autopilot disabled and speed < 5 km/h
# Press Q key and verify gear state change
# Test throttle limitation in reverse
grep GEAR_CHANGE jaccus_run.log
```

## Code Maintenance Strategy

### Monthly Tasks
1. Review PID parameter effectiveness
2. Analyze emergency brake logs for false positives
3. Update sidewalk detection distances based on usage patterns
4. Optimize throttle scaling factors

### Quarterly Tasks
1. Update CARLA compatibility (currently 0.9.15)
2. Review BehaviorAgent integration status
3. Enhance logging categories and detail levels
4. Performance optimization based on usage metrics

### Annual Tasks
1. Major PID controller algorithm updates
2. Emergency brake system enhancement
3. Comprehensive testing across all CARLA maps
4. Documentation updates and training materials

## Version History

### v1.0.0 (Current)
- Initial implementation with enhanced PID controller
- Road boundary detection using CARLA waypoints
- Q key reverse gear functionality with safety interlocks
- Comprehensive logging system to jaccus_run.log
- Dynamic throttle scaling for improved speed control
- Emergency brake system with sidewalk detection

## Support and Contact

For technical support or questions about the JACCUS speed control system:
- Review this documentation first
- Check `jaccus_run.log` for detailed system behavior
- Test configuration changes in safe CARLA environment
- Document any modifications for future reference

---
*Last Updated: January 2024*
*JACCUS Version: 1.0.0*
*CARLA Version: 0.9.15*
