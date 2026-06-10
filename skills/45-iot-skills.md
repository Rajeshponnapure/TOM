# IoT Skills

## Execution mode
Tool-backed through `tools.iot_engine.IoTEngine`.

## Keywords
iot, esp32, esp8266, arduino, mqtt, sensor, sensors, firmware, micropython, nodered, node-red, smart home, pinout, wiring, cloud iot.

## Local capabilities
- Generate Arduino firmware for ESP32 and ESP8266 boards.
- Generate MicroPython firmware for ESP32 and ESP8266 boards.
- Generate MQTT, HTTP, WebSocket, CoAP, and BLE protocol examples.
- Generate sensor-specific code for supported modules.
- Generate backend integration code for supported IoT backends.
- Generate pinout and wiring diagrams.
- Generate IoT system architecture and device configuration.

## Required TOM tools
- `iot_engine`
- `file_tools` when generated code must be written to disk

## Routing rule
Use this skill when the task mentions IoT hardware, ESP32, ESP8266, Arduino firmware, MQTT devices, sensors, pin mapping, smart-home automation, device-to-cloud flows, or embedded device architecture.

## Limitations
- Physical device flashing, serial monitoring, cloud deployment, and sensor verification require connected hardware, credentials, or external tools.
- Generated firmware must be reviewed against the exact board revision, voltage levels, and wiring before upload.
