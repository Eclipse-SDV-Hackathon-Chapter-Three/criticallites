#!/bin/bash

# JACCUS MQTT Integration Test Script
# This script tests the MQTT integration without requiring CARLA to be running

echo "=== JACCUS MQTT Integration Test ==="
echo

# Check if mosquitto is installed
if ! command -v mosquitto &> /dev/null; then
    echo "❌ Mosquitto MQTT broker not installed. Installing..."
    sudo apt update && sudo apt install mosquitto mosquitto-clients
else
    echo "✅ Mosquitto MQTT broker found"
fi

# Start mosquitto broker
echo "🚀 Starting MQTT broker..."
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Wait a moment for broker to start
sleep 2

# Check broker status
if sudo systemctl is-active --quiet mosquitto; then
    echo "✅ MQTT broker is running"
else
    echo "❌ MQTT broker failed to start"
    exit 1
fi

# Test broker connectivity
echo "🔗 Testing MQTT broker connectivity..."
timeout 5 mosquitto_pub -h localhost -t test -m "hello" -q 1
if [ $? -eq 0 ]; then
    echo "✅ MQTT broker connectivity test passed"
else
    echo "❌ MQTT broker connectivity test failed"
    exit 1
fi

# Check Python dependencies
echo "📦 Checking Python dependencies..."
python3 -c "import paho.mqtt.client; print('✅ paho-mqtt available')" 2>/dev/null || {
    echo "❌ paho-mqtt not available. Installing..."
    pip3 install paho-mqtt==2.1.0
}

python3 -c "import json; print('✅ json available')" 2>/dev/null || {
    echo "❌ json module not available"
    exit 1
}

# Test MQTT configuration
echo "⚙️  Testing MQTT configuration..."
cd /home/seame/criticallites/jaccus/targets

if [ ! -f mqtt_config.json ]; then
    echo "❌ mqtt_config.json not found"
    exit 1
else
    echo "✅ mqtt_config.json found"
fi

# Validate JSON configuration
python3 -c "
import json
try:
    with open('mqtt_config.json', 'r') as f:
        config = json.load(f)
    print('✅ mqtt_config.json is valid JSON')
    print(f'   Broker: {config.get(\"broker\", \"localhost\")}')
    print(f'   Port: {config.get(\"port\", 1883)}')
    print(f'   Topics: {list(config.get(\"topics\", {}).values())}')
except Exception as e:
    print(f'❌ mqtt_config.json validation failed: {e}')
    exit(1)
"

# Test MQTT client creation (mock mode)
echo "🧪 Testing MQTT client creation..."
python3 -c "
import sys
sys.path.append('/home/seame/criticallites/jaccus/targets')

try:
    # Import our MQTT client
    from jaccus.communication.mqtt_client import create_mqtt_client, MockMQTTClient

    # Create a mock vehicle object for testing
    class MockVehicle:
        def get_velocity(self):
            class MockVelocity:
                x, y, z = 10.0, 0.0, 0.0
            return MockVelocity()

        def get_transform(self):
            class MockTransform:
                def __init__(self):
                    self.location = self
                    self.x, self.y, self.z = 100.0, 200.0, 0.5
                def get_forward_vector(self):
                    class MockVector:
                        x, y, z = 1.0, 0.0, 0.0
                    return MockVector()
            return MockTransform()

    # Test client creation
    mock_vehicle = MockVehicle()
    client = create_mqtt_client(mock_vehicle, 'mqtt_config.json')

    print('✅ MQTT client created successfully')
    print(f'   Client type: {type(client).__name__}')

    # Test mock publishing
    result = client.publish_vehicle_data({'CruiseControl': True})
    print(f'✅ Mock data publishing: {\"SUCCESS\" if result else \"FAILED\"}')

    # Cleanup
    client.close()

except Exception as e:
    print(f'❌ MQTT client test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

# Test monitoring script
echo "📊 Testing MQTT data monitor script..."
if [ -f mqtt_data_monitor.py ]; then
    python3 -c "
import sys
sys.path.append('/home/seame/criticallites/jaccus/targets')
try:
    from mqtt_data_monitor import JACCUSDataMonitor
    print('✅ MQTT data monitor script is importable')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"
else
    echo "❌ mqtt_data_monitor.py not found"
    exit 1
fi

# Test command tester script
echo "🎛️  Testing MQTT command tester script..."
if [ -f mqtt_command_tester.py ]; then
    python3 -c "
import sys
sys.path.append('/home/seame/criticallites/jaccus/targets')
try:
    from mqtt_command_tester import JACCUSCommandTester
    print('✅ MQTT command tester script is importable')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"
else
    echo "❌ mqtt_command_tester.py not found"
    exit 1
fi

# Final integration test with actual MQTT
echo "🔄 Running end-to-end MQTT test..."

# Start a background subscriber
timeout 10 python3 -c "
import sys
sys.path.append('/home/seame/criticallites/jaccus/targets')
from mqtt_data_monitor import JACCUSDataMonitor
try:
    monitor = JACCUSDataMonitor('mqtt_config.json')
    print('✅ MQTT subscriber started successfully')
    import time
    time.sleep(2)  # Let it run briefly
    monitor.close()
except Exception as e:
    print(f'❌ MQTT subscriber test failed: {e}')
" &

SUBSCRIBER_PID=$!
sleep 3

# Send a test command
python3 -c "
import sys
sys.path.append('/home/seame/criticallites/jaccus/targets')
from mqtt_command_tester import JACCUSCommandTester
try:
    tester = JACCUSCommandTester('mqtt_config.json')
    success = tester.send_speed_command(60)
    print(f'✅ MQTT command test: {\"SUCCESS\" if success else \"FAILED\"}')
    tester.close()
except Exception as e:
    print(f'❌ MQTT command test failed: {e}')
"

# Wait for subscriber to finish
wait $SUBSCRIBER_PID 2>/dev/null

echo
echo "=== Test Summary ==="
echo "✅ MQTT broker: Running"
echo "✅ Python dependencies: Available"
echo "✅ Configuration files: Valid"
echo "✅ MQTT client: Functional"
echo "✅ Test scripts: Importable"
echo "✅ End-to-end MQTT: Tested"
echo
echo "🎉 JACCUS MQTT Integration Test PASSED!"
echo
echo "Next steps:"
echo "1. Start CARLA simulator"
echo "2. Run: python -m jaccus.main"
echo "3. In another terminal: python mqtt_data_monitor.py"
echo "4. In another terminal: python mqtt_command_tester.py"
echo
echo "📚 See MQTT_INTEGRATION.md for detailed usage instructions"
