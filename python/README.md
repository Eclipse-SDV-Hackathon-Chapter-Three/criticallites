# MQTT Python Publisher & Subscriber

A Python-based MQTT implementation for publishing and subscribing to vehicle parameter data with intelligent CruiseControl status monitoring.

## 🚀 Features

- **JSON Data Exchange**: Publisher sends structured vehicle data, subscriber parses and displays it
- **CruiseControl Monitoring**: Smart detection and notification of CruiseControl state changes
- **Modular Configuration**: All settings centralized in the Ankaios manifest [mqtt-python.yaml](./mqtt-python.yaml)
- **Error Handling**: Robust JSON parsing with graceful error handling
- **Real-time Communication**: Continuous listening and publishing capabilities

## 📋 Prerequisites

- [Eclipse Ankaios v0.6.0](https://eclipse-ankaios.github.io/ankaios/0.6/usage/installation/) installed like described [here](../../README.md#install-eclipse-ankaios)
- [Podman](https://podman.io/docs/installation) installed like described [here](../../README.md#install-podman)
- Shared notebook hosting the eclipse mosquitto mqtt broker

## 📁 Project Structure

```
PythonMQTT/
├── mqtt_config.json      # Configuration file
├── publisher.py          # MQTT publisher script
├── subscriber.py         # MQTT subscriber script
├── requirements.txt      # Python dependencies
├── mqtt_python_setup.md  # Detailed setup documentation
└── README.md            # This file
```

## ⚙️ Configuration

The mqtt settings are included in the Ankaios manifest [mqtt-python.yaml](./mqtt-python.yaml).

```json
{
  "broker": "localhost",
  "port": 1883,
  "keepalive": 60,
  "topics": {
    "vehicle_parameters": "vehicle/parameters"
  }
}
```

The mqtt broker used by the subsciber and publisher is running on the shared notebook. You must find out the external IP address of the shared notebook and replace `localhost` with its ip address.

### Configuration Fields

| Field     | Description                           | Default |
|-----------|---------------------------------------|---------|
| broker    | MQTT broker address                   | localhost |
| port      | Broker port number                    | 1883 |
| keepalive | Keepalive interval in seconds         | 60 |
| topics    | Dictionary of topic names             | vehicle/parameters |

## 🚗 Vehicle Data Format

The publisher sends JSON data with the following structure:

```json
{
  "AmbientTemperature": 22,
  "Battery": 80,
  "CruiseControl": false,
  "Economy": "Normal",
  "Engine Temperature": 90,
  "Gear": "P",
  "RPM": 0.0,
  "Range": 320,
  "ShareLocation": false,
  "Speed": 0,
  "SpeedUnit": "km/h",
  "TemperatureUnit": 0,
  "TypeOfVehicle": 0
}
```

The data format is included in the Ankaios manifest [mqtt-python.yaml](./mqtt-python.yaml) and used by the MQTT publisher and subscriber.

## 🎯 Run

1. Make sure your MQTT broker is running on the shared notebook (`ank get workloads` on the shared notebook) and your notebook has connection to the shared notebook.
2. Replace the `localhost` in the MQTT config with the ip address of the shared notebook.
3. Apply the Ankaios manifest to start the demo applications:
```shell
ank apply mqtt-python.yaml
```
4. Verify the logs of the publisher:
```shell
ank logs -f mqtt-publisher
```
**Expected Output**:
```
Published to topic vehicle/parameters: {"AmbientTemperature": 22, "Battery": 80, ...}
```

5. Verify the logs of the subscriber:
```shell
ank logs -f mqtt-subscriber
```
**Expected Output**:
```
Subscribed to topic: vehicle/parameters
Received message on vehicle/parameters: {
  "AmbientTemperature": 22,
  "Battery": 80,
  "CruiseControl": false,
  ...
}
```
6. Delete the example workloads
```shell
ank apply -d mqtt-python.yaml
```

## Change and build example code

The applications are a good starting point. You can enhance the existing code or create new workloads.
All applications managed by Eclipse Ankaios must be containerized. If you change a line of code you must rebuild the container image for that app with:

```shell
sudo podman build -t custom_mqtt_publisher -f Dockerfile.publisher .
```

Afterwards you need to replace the public demo container image (e.g. `ghcr.io/eclipse-sdv-hackathon-chapter-three/sdv-lab/mqtt-publisher:latest`) with your custom one (e.g. `custom_mqtt_publisher`) in the Ankaios manifest [mqtt-python.yaml](./mqtt-python.yaml) for the specific workload. You can use the existing `Dockerfile` for building.

For a final demo and container image, consider uploading to `ghcr.io/eclipse-sdv-hackathon-chapter-three/sdv-lab/mqtt-subscriber:<team_name>-<version>`, so that someone who want to try out your final setup does not need to build container images. Replace the `team_name` with your hack team's name and append a version (`0.1`). Replace the existing images with your final ones in the Ankaios manifest [mqtt-python.yaml](./mqtt-python.yaml).

## 🎛️ CruiseControl Monitoring

The subscriber includes intelligent CruiseControl monitoring:

- **When CruiseControl activates**: `Cruise Control active. Speed: {speed}`
- **When CruiseControl deactivates**: `Cruise Control deactivated.`
- **No spam**: Only prints messages when state actually changes

### Example CruiseControl Output

```
Received message on vehicle/parameters: { ... "CruiseControl": true, "Speed": 65 ... }
Cruise Control active. Speed: 65

Received message on vehicle/parameters: { ... "CruiseControl": false, "Speed": 0 ... }
Cruise Control deactivated.
```

## 🔧 Customization

### Adding More Topics

Edit MQTT JSON config in the Ankaios manifest [mqtt-python.yaml](./mqtt-python.yaml) to add additional topics:

```json
{
  "broker": "localhost",
  "port": 1883,
  "keepalive": 60,
  "topics": {
    "vehicle_parameters": "vehicle/parameters",
    "engine_status": "vehicle/engine",
    "location_data": "vehicle/location"
  }
}
```

### Modifying Vehicle Data

Edit the `payload` dictionary in `publisher.py`:

```python
payload = {
    "AmbientTemperature": 25,
    "Battery": 85,
    "CruiseControl": True,
    "Speed": 70,
    # Add your custom fields here
}
```

### Continuous Publishing

For continuous data publishing, modify `publisher.py`:

```python
while True:
    client.publish(topic, json.dumps(payload))
    time.sleep(5)  # Publish every 5 seconds
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Ensure MQTT broker is running on the shared notebook (access the shared notebook and check with `ank get workloads`)
   - Check broker address and port in the Ankaios manifest [mqtt-python.yaml](./mqtt-python.yaml)

2. **Permission Denied (GitHub)**:
   - Create repository on GitHub first
   - Set up SSH keys or use HTTPS authentication

3. **JSON Decode Errors**:
   - Check if publisher is sending valid JSON (`ank logs -f mqtt-publisher` and `ank logs -f mqtt-subscriber`)
   - Verify topic names match between publisher and subscriber

### Debug Mode

Add debug logging to see detailed MQTT communication:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

In this case you need to rebuild the container image.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature"`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 📞 Support

For questions or issues:
- Create an issue on GitHub
- Check the detailed documentation in `mqtt_python_setup.md`

---

**Happy MQTT-ing! 🚀**
