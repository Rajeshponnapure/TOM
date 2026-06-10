"""
TOM Autonomous Agent -- Universal IoT Engine
Generates working firmware/device code for IoT devices.
"""

import json
import base64
from typing import Any, Dict, List, Optional, Tuple, Union

_RESPONSE = Dict[str, Any]

def _ok(result=None, message='OK'):
    return {'status': 'success', 'result': result, 'message': message}

def _err(message):
    return {'status': 'error', 'result': None, 'message': message}

# Component registries
_TEMP_HUMIDITY = {
    "DHT11", "DHT22", "BME280", "SHT30", "DS18B20", "LM35",
}
_MOTION = {
    "HC-SR501", "PIR", "RCWL-0516", "HC-SR04", "Ultrasonic",
}
_GAS_AIR = {
    "MQ-2", "MQ-3", "MQ-4", "MQ-5", "MQ-6", "MQ-7", "MQ-8", "MQ-9",
    "MQ-135", "CCS811", "PMS5003",
}
_PRESSURE = {
    "BMP180", "BMP280", "BME280", "MPU6050",
}
_LIGHT = {
    "LDR", "BH1750", "TSL2561", "MAX44009",
}
_SOIL = {
    "SoilMoisture", "Soil_pH", "Soil_NPK",
}
_WATER = {
    "WaterLevel", "RainSensor", "FlowSensor", "TDS_Sensor",
}
_DISPLAY = {
    "OLED_SSD1306", "LCD_1602", "LCD_2004", "LED_Matrix", "SevenSegment",
}
_MOTORS = {
    "DC_Motor", "Stepper_28BYJ", "Servo_SG90",
}
_GPS = {
    "NEO-6M", "NEO-7M", "NEO-8M",
}
_RFID = {
    "RC522", "PN532",
}
_CAMERA = {
    "ESP32-CAM", "OV2640", "OV7670",
}
_AUDIO = {
    "MAX9814", "I2S_MEMS", "Speaker", "DFPlayer_Mini",
}
_ACTUATORS = {
    "LED", "Relay", "Buzzer", "RGB_LED", "Vibration",
}
_ALL_SENSORS = _TEMP_HUMIDITY | _MOTION | _GAS_AIR | _PRESSURE | _LIGHT | _SOIL | _WATER | _GPS | _RFID
_ALL_COMPONENTS = _ALL_SENSORS | _DISPLAY | _MOTORS | _CAMERA | _AUDIO | _ACTUATORS

_ESP32_DEFAULT_PINS: Dict[str, int] = {
    "BH1750": 21,
    "BME280": 21,
    "BMP180": 21,
    "BMP280": 21,
    "Buzzer": 15,
    "CCS811": 21,
    "DC_Motor_ENA": 14,
    "DC_Motor_IN1": 26,
    "DC_Motor_IN2": 27,
    "DFPlayer_RX": 16,
    "DFPlayer_TX": 17,
    "DHT": 4,
    "DHT22": 4,
    "DS18B20": 4,
    "FlowSensor": 34,
    "HC-SR04_ECHO": 17,
    "HC-SR04_TRIG": 16,
    "I2S_MEMS": 26,
    "LCD_1602": 21,
    "LCD_2004": 21,
    "LDR": 34,
    "LED": 2,
    "LED_Matrix": 21,
    "LM35": 34,
    "MAX44009": 21,
    "MAX9814": 34,
    "MPU6050": 21,
    "MQ135": 34,
    "MQ2": 34,
    "MQ3": 34,
    "MQ4": 34,
    "MQ5": 34,
    "MQ6": 34,
    "MQ7": 34,
    "MQ8": 34,
    "MQ9": 34,
    "NEO6M_RX": 16,
    "NEO6M_TX": 17,
    "OLED_SSD1306": 21,
    "PIR": 5,
    "PMS5003": 16,
    "RC522_RST": 22,
    "RC522_SS": 5,
    "RCWL": 18,
    "RGB_LED_B": 14,
    "RGB_LED_G": 12,
    "RGB_LED_R": 13,
    "RainSensor": 34,
    "Relay": 23,
    "SHT30": 21,
    "Servo_SG90": 13,
    "SevenSegment": 21,
    "SoilMoisture": 34,
    "Soil_NPK": 34,
    "Soil_pH": 34,
    "Speaker_DAC": 25,
    "Stepper": 14,
    "TDS_Sensor": 34,
    "TSL2561": 21,
    "Vibration": 18,
    "WaterLevel": 34,
}

_ESP8266_DEFAULT_PINS: Dict[str, int] = {
    "BH1750": 4,
    "BME280": 4,
    "BMP180": 4,
    "BMP280": 4,
    "Buzzer": 12,
    "CCS811": 4,
    "DC_Motor_ENA": 14,
    "DC_Motor_IN1": 12,
    "DC_Motor_IN2": 13,
    "DFPlayer_RX": 4,
    "DFPlayer_TX": 5,
    "DHT": 2,
    "DHT22": 2,
    "DS18B20": 4,
    "FlowSensor": 0,
    "HC-SR04_ECHO": 14,
    "HC-SR04_TRIG": 13,
    "I2S_MEMS": 14,
    "LCD_1602": 4,
    "LCD_2004": 4,
    "LDR": 0,
    "LED": 2,
    "LED_Matrix": 4,
    "LM35": 0,
    "MAX44009": 4,
    "MAX9814": 0,
    "MPU6050": 4,
    "MQ135": 0,
    "MQ2": 0,
    "MQ3": 0,
    "MQ4": 0,
    "MQ5": 0,
    "MQ6": 0,
    "MQ7": 0,
    "MQ8": 0,
    "MQ9": 0,
    "NEO6M_RX": 5,
    "NEO6M_TX": 4,
    "OLED_SSD1306": 4,
    "PIR": 5,
    "PMS5003": 13,
    "RC522_RST": 2,
    "RC522_SS": 15,
    "RCWL": 12,
    "RGB_LED_B": 14,
    "RGB_LED_G": 12,
    "RGB_LED_R": 13,
    "RainSensor": 0,
    "Relay": 4,
    "SHT30": 4,
    "Servo_SG90": 15,
    "SevenSegment": 4,
    "SoilMoisture": 0,
    "Soil_NPK": 0,
    "Soil_pH": 0,
    "Speaker_DAC": 13,
    "Stepper": 14,
    "TDS_Sensor": 0,
    "TSL2561": 4,
    "Vibration": 5,
    "WaterLevel": 0,
}
_I2C_COMPONENTS = {
    "BME280", "BMP180", "BMP280", "SHT30", "MPU6050", "BH1750",
    "TSL2561", "MAX44009", "CCS811", "OLED_SSD1306", "LCD_1602",
    "LCD_2004", "SCD30", "ADS1115", "MCP9808", "SSD1306",
}

def _pin(component, board, custom=None):
    pins = _ESP32_DEFAULT_PINS if board == 'esp32' else _ESP8266_DEFAULT_PINS
    if custom and component in custom:
        return custom[component]
    if component in pins:
        return pins[component]
    return 4 if component in _I2C_COMPONENTS else (34 if board == 'esp32' else 0)

def _has_i2c(components):
    return bool(set(components) & _I2C_COMPONENTS)

# ===================================================================
# INTERNAL CODE BUILDERS -- ESP32/ESP8266 Arduino
# ===================================================================

DQ = chr(34)

def _build_includes(components, has_protocols):
    lines = []
    lines.append("#include <Arduino.h>")
    if _has_i2c(components):
        lines.append("#include <Wire.h>")
    if any(c in ("DHT11", "DHT22", "DHT") for c in components):
        lines.append("#include <DHT.h>")
        lines.append("#include <DHT_U.h>")
    if "DS18B20" in components:
        lines.append("#include <OneWire.h>")
        lines.append("#include <DallasTemperature.h>")
    if "BME280" in components:
        lines.append("#include <Adafruit_BME280.h>")
    if "BMP180" in components or "BMP280" in components:
        lines.append("#include <Adafruit_BMP280.h>")
    if "SHT30" in components:
        lines.append("#include <Adafruit_SHT31.h>")
    if "BH1750" in components:
        lines.append("#include <BH1750.h>")
    if "TSL2561" in components:
        lines.append("#include <Adafruit_TSL2561_U.h>")
    if "MAX44009" in components:
        lines.append("#include <Adafruit_MAX44009.h>")
    if "CCS811" in components:
        lines.append("#include <Adafruit_CCS811.h>")
    if "PMS5003" in components:
        lines.append("#include <SoftwareSerial.h>")
    if "MPU6050" in components:
        lines.append("#include <Adafruit_MPU6050.h>")
    if "Servo_SG90" in components or "Servo" in components:
        lines.append("#include <Servo.h>")
    if "OLED_SSD1306" in components:
        lines.append("#include <Adafruit_GFX.h>")
        lines.append("#include <Adafruit_SSD1306.h>")
    if "LCD_1602" in components or "LCD_2004" in components:
        lines.append("#include <LiquidCrystal_I2C.h>")
    if "RC522" in components:
        lines.append("#include <MFRC522.h>")
    if "PN532" in components:
        lines.append("#include <Adafruit_PN532.h>")
    if "DFPlayer_Mini" in components:
        lines.append("#include <SoftwareSerial.h>")
        lines.append("#include <DFRobotDFPlayerMini.h>")
    if any(c in _GPS for c in components):
        lines.append("#include <SoftwareSerial.h>")
        lines.append("#include <TinyGPS++.h>")
    if "MAX9814" in components or "I2S_MEMS" in components:
        lines.append("#include <driver/i2s.h>")
    proto_set = set(has_protocols)
    if "mqtt" in proto_set:
        lines.append("#include <WiFi.h>" if "esp32" in str(proto_set) else "#include <ESP8266WiFi.h>")
        lines.append("#include <PubSubClient.h>")
    if "wifi" in proto_set:
        lines.append("#include <WiFi.h>" if "esp32" in str(proto_set) else "#include <ESP8266WiFi.h>")
    if "websocket" in proto_set:
        lines.append("#include <WebSocketsClient.h>")
    if "http" in proto_set or "rest" in proto_set:
        lines.append("#include <WiFiClient.h>")
        lines.append("#include <HTTPClient.h>")
    if "ble" in proto_set:
        lines.append("#include <BLEDevice.h>")
        lines.append("#include <BLEUtils.h>")
        lines.append("#include <BLEServer.h>")
    return "\\n".join(lines)

def _build_wifi_config(wifi):
    if not wifi:
        wifi = {"ssid": "YourWiFiSSID", "password": "YourWiFiPassword"}
    return 'const char* WIFI_SSID = ' + DQ + wifi.get("ssid", "YourWiFiSSID") + DQ + ';\\nconst char* WIFI_PASSWORD = ' + DQ + wifi.get("password", "YourWiFiPassword") + DQ + ';'

def _build_mqtt_config(mqtt):
    if not mqtt:
        mqtt = {}
    h = mqtt.get("broker", "broker.emqx.io")
    p = mqtt.get("port", 1883)
    u = mqtt.get("username", "")
    pw = mqtt.get("password", "")
    cid = mqtt.get("client_id", "tom_iot_device")
    t = mqtt.get("topic_prefix", "tom/device")
    return ('const char* MQTT_HOST = ' + DQ + h + DQ + ';\\n' +
            'const int MQTT_PORT = ' + str(p) + ';\\n' +
            'const char* MQTT_USER = ' + DQ + u + DQ + ';\\n' +
            'const char* MQTT_PASS = ' + DQ + pw + DQ + ';\\n' +
            'const char* MQTT_CLIENT_ID = ' + DQ + cid + DQ + ';\\n' +
            'const char* MQTT_TOPIC_PREFIX = ' + DQ + t + DQ + ';')

def _build_wifi_setup():
    s = 'void setupWiFi() {' + chr(10)
    s += '  Serial.print("Connecting to WiFi");' + chr(10)
    s += '  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);' + chr(10)
    s += '  while (WiFi.status() != WL_CONNECTED) {' + chr(10)
    s += '    delay(500);' + chr(10)
    s += '    Serial.print(".");' + chr(10)
    s += '  }' + chr(10)
    s += '  Serial.println("\\\\nWiFi connected. IP: " + WiFi.localIP().toString());' + chr(10)
    s += '}' + chr(10)
    return s

def _build_mqtt_setup():
    s = 'WiFiClient wifiClient;' + chr(10)
    s += 'PubSubClient mqttClient(wifiClient);' + chr(10)
    s += '' + chr(10)
    s += 'void callback(char* topic, byte* payload, unsigned int length) {' + chr(10)
    s += '  Serial.print("MQTT message arrived [");' + chr(10)
    s += '  Serial.print(topic);' + chr(10)
    s += '  Serial.print("] ");' + chr(10)
    s += '  char msg[length + 1];' + chr(10)
    s += '  for (unsigned int i = 0; i < length; i++) msg[i] = (char)payload[i];' + chr(10)
    s += '  msg[length] = ' + "'\\\\0'" + ';' + chr(10)
    s += '  Serial.println(msg);' + chr(10)
    s += '  handleCommand(String(topic), String(msg));' + chr(10)
    s += '}' + chr(10)
    s += '' + chr(10)
    s += 'void reconnectMQTT() {' + chr(10)
    s += '  while (!mqttClient.connected()) {' + chr(10)
    s += '    Serial.print("Connecting to MQTT...");' + chr(10)
    s += '    if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASS)) {' + chr(10)
    s += '      Serial.println("connected");' + chr(10)
    s += '      mqttClient.subscribe((String(MQTT_TOPIC_PREFIX) + "/cmd/#").c_str());' + chr(10)
    s += '    } else {' + chr(10)
    s += '      Serial.print("failed, rc=");' + chr(10)
    s += '      Serial.print(mqttClient.state());' + chr(10)
    s += '      Serial.println(" retrying in 5s");' + chr(10)
    s += '      delay(5000);' + chr(10)
    s += '    }' + chr(10)
    s += '  }' + chr(10)
    s += '}' + chr(10)
    s += '' + chr(10)
    s += 'void setupMQTT() {' + chr(10)
    s += '  mqttClient.setServer(MQTT_HOST, MQTT_PORT);' + chr(10)
    s += '  mqttClient.setCallback(callback);' + chr(10)
    s += '}' + chr(10)
    s += '' + chr(10)
    s += 'bool publishTelemetry(const char* topic, const char* payload, bool retained = false) {' + chr(10)
    s += '  if (!mqttClient.connected()) return false;' + chr(10)
    s += '  char fullTopic[128];' + chr(10)
    s += '  snprintf(fullTopic, sizeof(fullTopic), "%s/%s", MQTT_TOPIC_PREFIX, topic);' + chr(10)
    s += '  return mqttClient.publish(fullTopic, payload, retained);' + chr(10)
    s += '}' + chr(10)
    s += '' + chr(10)
    s += 'void handleCommand(String topic, String payload) {' + chr(10)
    s += '  if (payload == "restart") {' + chr(10)
    s += '    ESP.restart();' + chr(10)
    s += '  }' + chr(10)
    s += '}' + chr(10)
    return s

def _build_sensor_readers(components, board, user_pins=None):
    if user_pins is None:
        user_pins = {}
    code = ""
    Q = chr(34)
    b = board

    if any(c in ("DHT11", "DHT22", "DHT") for c in components):
        dt = "DHT22" if "DHT22" in components else "DHT11"
        p = _pin("DHT", b, user_pins)
        code += "\\n#define DHTPIN " + str(p) + "\\n#define DHTTYPE " + dt + "\\nDHT dht(DHTPIN, DHTTYPE);\\n\\n"
        code += "void readDHT(float &t, float &h) {\\n"
        code += "  h = dht.readHumidity();\\n"
        code += "  t = dht.readTemperature();\\n"
        code += "  if (isnan(h) || isnan(t)) {\\n"
        code += "    Serial.println(" + Q + "DHT read failed" + Q + ");\\n"
        code += "    h = -1; t = -1;\\n"
        code += "  }\\n}\\n"

    if "DS18B20" in components:
        p = _pin("DS18B20", b, user_pins)
        code += "\\n#define ONE_WIRE_BUS " + str(p) + "\\n"
        code += "OneWire oneWire(ONE_WIRE_BUS);\\n"
        code += "DallasTemperature ds18b20(&oneWire);\\n\\n"
        code += "void readDS18B20(float &temp) {\\n"
        code += "  ds18b20.requestTemperatures();\\n"
        code += "  temp = ds18b20.getTempCByIndex(0);\\n"
        code += "  if (temp == DEVICE_DISCONNECTED_C) {\\n"
        code += "    Serial.println(" + Q + "DS18B20 disconnected" + Q + ");\\n"
        code += "    temp = -127;\\n"
        code += "  }\\n}\\n"

    if "BME280" in components:
        code += "\\nAdafruit_BME280 bme;\\n\\n"
        code += "bool initBME280() { return bme.begin(0x76); }\\n\\n"
        code += "void readBME280(float &t, float &h, float &p) {\\n"
        code += "  t = bme.readTemperature();\\n"
        code += "  h = bme.readHumidity();\\n"
        code += "  p = bme.readPressure() / 100.0F;\\n}\\n"

    if "BMP180" in components or "BMP280" in components:
        code += "\\nAdafruit_BMP280 bmp;\\n\\n"
        code += "bool initBMP280() { return bmp.begin(0x76); }\\n\\n"
        code += "void readBMP280(float &t, float &p) {\\n"
        code += "  t = bmp.readTemperature();\\n"
        code += "  p = bmp.readPressure() / 100.0F;\\n}\\n"

    if "SHT30" in components:
        code += "\\nAdafruit_SHT31 sht30 = Adafruit_SHT31();\\n\\n"
        code += "bool initSHT30() { return sht30.begin(0x44); }\\n\\n"
        code += "void readSHT30(float &t, float &h) {\\n"
        code += "  t = sht30.readTemperature();\\n"
        code += "  h = sht30.readHumidity();\\n"
        code += "  if (isnan(t) || isnan(h)) { t = -1; h = -1; }\\n}\\n"

    if "LM35" in components:
        p = _pin("LM35", b, user_pins)
        code += "\\n#define LM35_PIN " + str(p) + "\\n\\n"
        code += "float readLM35() {\\n"
        code += "  int raw = analogRead(LM35_PIN);\\n"
        code += "  float mv = (raw / 4095.0) * 3300.0;\\n"
        code += "  return mv / 10.0;\\n}\\n"

    if any(c in ("HC-SR501", "PIR") for c in components):
        p = _pin("PIR", b, user_pins)
        code += "\\n#define PIR_PIN " + str(p) + "\\n\\n"
        code += "bool readPIR() { return digitalRead(PIR_PIN) == HIGH; }\\n"

    if "RCWL-0516" in components:
        p = _pin("RCWL", b, user_pins)
        code += "\\n#define RCWL_PIN " + str(p) + "\\n\\n"
        code += "bool readRCWL() { return digitalRead(RCWL_PIN) == HIGH; }\\n"

    if any(c in ("HC-SR04", "Ultrasonic") for c in components):
        tp = _pin("HC-SR04_TRIG", b, user_pins)
        ep = _pin("HC-SR04_ECHO", b, user_pins)
        code += "\\n#define TRIG_PIN " + str(tp) + "\\n#define ECHO_PIN " + str(ep) + "\\n\\n"
        code += "void initUltrasonic() {\\n"
        code += "  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);\\n}\\n\\n"
        code += "float readUltrasonic() {\\n"
        code += "  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);\\n"
        code += "  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10); digitalWrite(TRIG_PIN, LOW);\\n"
        code += "  long duration = pulseIn(ECHO_PIN, HIGH, 30000);\\n"
        code += "  if (duration == 0) return -1;\\n"
        code += "  return duration * 0.034 / 2;\\n}\\n"

    for mq in ("MQ-2", "MQ-3", "MQ-4", "MQ-5", "MQ-6", "MQ-7", "MQ-8", "MQ-9", "MQ-135"):
        if mq in components:
            p = _pin(mq, b, user_pins)
            sane = mq.replace("-", "")
            code += "\\n#define " + sane + "_PIN " + str(p) + "\\n\\n"
            code += "float read" + sane + "() {\\n"
            code += "  int raw = analogRead(" + sane + "_PIN);\\n"
            code += "  float voltage = raw * (3.3 / 4095.0);\\n"
            code += "  return (3.3 - voltage) / voltage;\\n}\\n"
            break

    if "CCS811" in components:
        code += "\\nAdafruit_CCS811 ccs;\\n\\n"
        code += "bool initCCS811() { return ccs.begin(); }\\n\\n"
        code += "bool readCCS811(uint16_t &co2, uint16_t &tvoc) {\\n"
        code += "  if (ccs.available()) {\\n"
        code += "    if (!ccs.readData()) {\\n"
        code += "      co2 = ccs.geteCO2(); tvoc = ccs.getTVOC(); return true;\\n"
        code += "    }\\n"
        code += "  }\\n  return false;\\n}\\n"

    if "PMS5003" in components:
        p = _pin("PMS5003", b, user_pins)
        txp = _pin("NEO6M_TX", b, user_pins)
        code += "\\n#define PMS_RX_PIN " + str(p) + "\\n#define PMS_TX_PIN " + str(txp) + "\\n"
        code += "SoftwareSerial pmsSerial(PMS_RX_PIN, PMS_TX_PIN);\\n"
        code += "struct PMSData { uint16_t pm10, pm25, pm100; };\\n\\n"
        code += "bool readPMS5003(PMSData &d) {\\n"
        code += "  uint8_t buf[32];\\n"
        code += "  if (pmsSerial.available() >= 32) {\\n"
        code += "    if (pmsSerial.read() == 0x42) {\\n"
        code += "      pmsSerial.read();\\n"
        code += "      for (int i = 0; i < 30; i++) buf[i] = pmsSerial.read();\\n"
        code += "      d.pm10 = (buf[6] << 8) | buf[7];\\n"
        code += "      d.pm25 = (buf[8] << 8) | buf[9];\\n"
        code += "      d.pm100 = (buf[10] << 8) | buf[11];\\n"
        code += "      return true;\\n"
        code += "    }\\n"
        code += "  }\\n  return false;\\n}\\n"

    if "MPU6050" in components:
        code += "\\nAdafruit_MPU6050 mpu;\\n\\n"
        code += "bool initMPU6050() { return mpu.begin(); }\\n\\n"
        code += "bool readMPU6050(float &ax, float &ay, float &az, float &gx, float &gy, float &gz, float &temp) {\\n"
        code += "  sensors_event_t a, g, t;\\n"
        code += "  mpu.getEvent(&a, &g, &t);\\n"
        code += "  ax = a.acceleration.x; ay = a.acceleration.y; az = a.acceleration.z;\\n"
        code += "  gx = g.gyro.x; gy = g.gyro.y; gz = g.gyro.z;\\n"
        code += "  temp = t.temperature;\\n  return true;\\n}\\n"

    if "BH1750" in components:
        code += "\\nBH1750 lightMeter;\\n\\n"
        code += "bool initBH1750() { return lightMeter.begin(); }\\n\\n"
        code += "float readBH1750() { return lightMeter.readLightLevel(); }\\n"

    if "TSL2561" in components:
        code += "\\nAdafruit_TSL2561_Unified tsl = Adafruit_TSL2561_Unified(TSL2561_ADDR_FLOAT, 12345);\\n\\n"
        code += "bool initTSL2561() { return tsl.begin(); }\\n\\n"
        code += "float readTSL2561() { sensors_event_t event; tsl.getEvent(&event); return event.light; }\\n"

    if "MAX44009" in components:
        code += "\\nAdafruit_MAX44009 max44009;\\n\\n"
        code += "bool initMAX44009() { return max44009.begin(); }\\n\\n"
        code += "float readMAX44009() { return max44009.readLux(); }\\n"

    if "SoilMoisture" in components:
        p = _pin("SoilMoisture", b, user_pins)
        code += "\\n#define SOIL_MOISTURE_PIN " + str(p) + "\\n\\n"
        code += "int readSoilMoisture() {\\n"
        code += "  int raw = analogRead(SOIL_MOISTURE_PIN);\\n"
        code += "  return map(raw, 0, 4095, 100, 0);\\n}\\n"

    if "WaterLevel" in components:
        p = _pin("WaterLevel", b, user_pins)
        code += "\\n#define WATER_LEVEL_PIN " + str(p) + "\\n\\n"
        code += "int readWaterLevel() {\\n"
        code += "  int raw = analogRead(WATER_LEVEL_PIN);\\n"
        code += "  return map(raw, 0, 4095, 0, 100);\\n}\\n"

    if "RainSensor" in components:
        p = _pin("RainSensor", b, user_pins)
        code += "\\n#define RAIN_SENSOR_PIN " + str(p) + "\\n\\n"
        code += "int readRainSensor() { return map(analogRead(RAIN_SENSOR_PIN), 0, 4095, 0, 100); }\\n"

    if "FlowSensor" in components:
        p = _pin("FlowSensor", b, user_pins)
        code += "\\n#define FLOW_SENSOR_PIN " + str(p) + "\\n"
        code += "volatile int flowPulseCount = 0;\\n\\n"
        code += "void IRAM_ATTR flowPulse() { flowPulseCount++; }\\n\\n"
        code += "float readFlowRate(float &totalLiters) {\\n"
        code += "  float rate = (flowPulseCount / 7.5);\\n"
        code += "  totalLiters += rate / 60.0;\\n"
        code += "  flowPulseCount = 0;\\n  return rate;\\n}\\n"

    if "TDS_Sensor" in components:
        p = _pin("TDS_Sensor", b, user_pins)
        code += "\\n#define TDS_PIN " + str(p) + "\\n\\n"
        code += "float readTDS() {\\n"
        code += "  int raw = analogRead(TDS_PIN);\\n"
        code += "  float voltage = raw * (3.3 / 4095.0);\\n"
        code += "  return (133.42*voltage*voltage*voltage - 255.86*voltage*voltage + 857.39*voltage) * 0.5;\\n}\\n"

    if "LDR" in components:
        p = _pin("LDR", b, user_pins)
        code += "\\n#define LDR_PIN " + str(p) + "\\n\\n"
        code += "int readLDR() { return analogRead(LDR_PIN); }\\n"

    if any(c in _GPS for c in components):
        txp = _pin("NEO6M_TX", b, user_pins)
        rxp = _pin("NEO6M_RX", b, user_pins)
        code += "\\n#define GPS_TX_PIN " + str(txp) + "\\n#define GPS_RX_PIN " + str(rxp) + "\\n"
        code += "TinyGPSPlus gps;\\nSoftwareSerial gpsSerial(GPS_TX_PIN, GPS_RX_PIN);\\n"
        code += "struct GPSData { double lat, lng; float speed, alt; int satellites; };\\n\\n"
        code += "bool readGPS(GPSData &d) {\\n"
        code += "  while (gpsSerial.available() > 0) gps.encode(gpsSerial.read());\\n"
        code += "  if (gps.location.isValid()) {\\n"
        code += "    d.lat = gps.location.lat(); d.lng = gps.location.lng();\\n"
        code += "    d.speed = gps.speed.kmph(); d.alt = gps.altitude.meters();\\n"
        code += "    d.satellites = gps.satellites.value();\\n    return true;\\n"
        code += "  }\\n  return false;\\n}\\n"
        code += "void initGPS() { gpsSerial.begin(9600); }\\n"

    if "RC522" in components:
        ss = _pin("RC522_SS", b, user_pins)
        rst = _pin("RC522_RST", b, user_pins)
        code += "\\n#define RST_PIN " + str(rst) + "\\n#define SS_PIN " + str(ss) + "\\n"
        code += "MFRC522 rfid(SS_PIN, RST_PIN);\\nMFRC522::MIFARE_Key key;\\n\\n"
        code += "void initRC522() { SPI.begin(); rfid.PCD_Init(); }\\n\\n"
        code += "String readRFID() {\\n"
        code += "  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return " + Q + Q + ";\\n"
        code += "  String uid = " + Q + Q + ";\\n"
        code += "  for (byte i = 0; i < rfid.uid.size; i++) uid += String(rfid.uid.uidByte[i], HEX);\\n"
        code += "  rfid.PICC_HaltA();\\n  return uid;\\n}\\n"

    if "PN532" in components:
        code += "\\nAdafruit_PN532 nfc;\\n\\n"
        code += "void initPN532() {\\n"
        code += "  nfc.begin();\\n"
        code += "  uint32_t ver = nfc.getFirmwareVersion();\\n"
        code += "  if (!ver) { Serial.println(" + Q + "PN532 not found" + Q + "); while (1); }\\n"
        code += "  nfc.SAMConfig();\\n}\\n\\n"
        code += "uint32_t readPN532() {\\n"
        code += "  uint8_t uid[7]; uint8_t len;\\n"
        code += "  if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &len)) {\\n"
        code += "    uint32_t id = 0;\\n"
        code += "    for (uint8_t i = 0; i < len; i++) { id = (id << 8) | uid[i]; }\\n"
        code += "    return id;\\n"
        code += "  }\\n  return 0;\\n}\\n"

    return code


def _build_setup(components, board, user_pins=None):
    lines = []
    lines.append("Serial.begin(115200);")
    lines.append('Serial.println("\\\\nTOM IoT Device Booting...");')
    lines.append("setupWiFi();")
    lines.append("setupMQTT();")
    if any(c in ("DHT11", "DHT22", "DHT") for c in components):
        lines.append("dht.begin();")
    if "DS18B20" in components:
        lines.append("ds18b20.begin();")
    if "BME280" in components:
        lines.append("initBME280();")
    if "BMP180" in components or "BMP280" in components:
        lines.append("initBMP280();")
    if "SHT30" in components:
        lines.append("initSHT30();")
    if any(c in ("HC-SR04", "Ultrasonic") for c in components):
        lines.append("initUltrasonic();")
    if "CCS811" in components:
        lines.append("initCCS811();")
    if "MPU6050" in components:
        lines.append("initMPU6050();")
    if "BH1750" in components:
        lines.append("initBH1750();")
    if "TSL2561" in components:
        lines.append("initTSL2561();")
    if "MAX44009" in components:
        lines.append("initMAX44009();")
    if "RC522" in components:
        lines.append("initRC522();")
    if "PN532" in components:
        lines.append("initPN532();")
    if any(c in _GPS for c in components):
        lines.append("initGPS();")
    if "FlowSensor" in components:
        fp = _pin("FlowSensor", board, user_pins)
        lines.append("pinMode(" + str(fp) + ", INPUT_PULLUP);")
        lines.append("attachInterrupt(digitalPinToInterrupt(" + str(fp) + "), flowPulse, RISING);")
    if "OLED_SSD1306" in components or "LCD_1602" in components or "LCD_2004" in components:
        lines.append("initDisplay();")
    if "Servo_SG90" in components or "Servo" in components:
        sp = _pin("Servo_SG90", board, user_pins)
        lines.append("servo.attach(" + str(sp) + ");")
    if "DFPlayer_Mini" in components:
        lines.append("initDFPlayer();")
    for c, v in zip(["LED", "Relay", "Buzzer", "Vibration"],
                     ["LED_PIN", "RELAY_PIN", "BUZZER_PIN", "VIB_PIN"]):
        if c in components:
            lines.append("pinMode(" + v + ", OUTPUT);")
    body = "\\\\n  ".join(lines)
    return "\\\\nvoid setup() {\\\\n  " + body + "\\\\n}\\\\n"


def _build_loop(components, deep_sleep=False):
    lines = []
    lines.append("if (!mqttClient.connected()) reconnectMQTT();")
    lines.append("mqttClient.loop();")
    lines.append("")
    Q = chr(34)
    payload_bits = []
    payload_bits.append(Q + "\\\\" + Q + "device_id" + Q + "\\\\" + Q + ": " + Q + "\\\\" + Q + Q + " + String(WiFi.macAddress()) + " + Q + "\\\\" + Q + Q)

    if any(c in ("DHT11", "DHT22", "DHT") for c in components):
        lines.append("float dht_t, dht_h; readDHT(dht_t, dht_h);")
        payload_bits.append(Q + "\\\\" + Q + "dht_temperature" + Q + "\\\\" + Q + ": " + Q + " + String(dht_t)")
        payload_bits.append(Q + "\\\\" + Q + "dht_humidity" + Q + "\\\\" + Q + ": " + Q + " + String(dht_h)")
    if "DS18B20" in components:
        lines.append("float ds18b20_t; readDS18B20(ds18b20_t);")
        payload_bits.append(Q + "\\\\" + Q + "ds18b20_temp" + Q + "\\\\" + Q + ": " + Q + " + String(ds18b20_t)")
    if "BME280" in components:
        lines.append("float bme_t, bme_h, bme_p; readBME280(bme_t, bme_h, bme_p);")
        for n in ["bme_temperature", "bme_humidity", "bme_pressure"]:
            payload_bits.append(Q + "\\\\" + Q + n + Q + "\\\\" + Q + ": " + Q + " + String(bme_" + n.split("_")[1] + ")")
    if "BMP180" in components or "BMP280" in components:
        lines.append("float bmp_t, bmp_p; readBMP280(bmp_t, bmp_p);")
        payload_bits.append(Q + "\\\\" + Q + "bmp_temperature" + Q + "\\\\" + Q + ": " + Q + " + String(bmp_t)")
        payload_bits.append(Q + "\\\\" + Q + "bmp_pressure" + Q + "\\\\" + Q + ": " + Q + " + String(bmp_p)")
    if "SHT30" in components:
        lines.append("float sht_t, sht_h; readSHT30(sht_t, sht_h);")
        payload_bits.append(Q + "\\\\" + Q + "sht_temperature" + Q + "\\\\" + Q + ": " + Q + " + String(sht_t)")
        payload_bits.append(Q + "\\\\" + Q + "sht_humidity" + Q + "\\\\" + Q + ": " + Q + " + String(sht_h)")
    if "LM35" in components:
        lines.append("float lm35_t = readLM35();")
        payload_bits.append(Q + "\\\\" + Q + "lm35_temperature" + Q + "\\\\" + Q + ": " + Q + " + String(lm35_t)")
    if any(c in ("HC-SR501", "PIR") for c in components):
        lines.append("bool motion = readPIR();")
        payload_bits.append(Q + "\\\\" + Q + "motion" + Q + "\\\\" + Q + ": " + Q + " + String(motion)")
    if "RCWL-0516" in components:
        lines.append("bool radar = readRCWL();")
        payload_bits.append(Q + "\\\\" + Q + "radar" + Q + "\\\\" + Q + ": " + Q + " + String(radar)")
    if any(c in ("HC-SR04", "Ultrasonic") for c in components):
        lines.append("float distance = readUltrasonic();")
        payload_bits.append(Q + "\\\\" + Q + "distance_cm" + Q + "\\\\" + Q + ": " + Q + " + String(distance)")
    for mq in ("MQ-2", "MQ-3", "MQ-4", "MQ-5", "MQ-6", "MQ-7", "MQ-8", "MQ-9", "MQ-135"):
        if mq in components:
            sane = mq.replace("-", "")
            lines.append("float " + sane + "_val = read" + sane + "();")
            payload_bits.append(Q + "\\\\" + Q + sane + Q + "\\\\" + Q + ": " + Q + " + String(" + sane + "_val)")
            break
    if "CCS811" in components:
        lines.append("uint16_t ccs_co2, ccs_tvoc; bool ccs_ok = readCCS811(ccs_co2, ccs_tvoc);")
        payload_bits.append(Q + "\\\\" + Q + "co2" + Q + "\\\\" + Q + ": " + Q + " + String(ccs_co2)")
        payload_bits.append(Q + "\\\\" + Q + "tvoc" + Q + "\\\\" + Q + ": " + Q + " + String(ccs_tvoc)")
    if "PMS5003" in components:
        lines.append("PMSData pms; bool pms_ok = readPMS5003(pms);")
        for n in ["pm10", "pm25", "pm100"]:
            payload_bits.append(Q + "\\\\" + Q + n + Q + "\\\\" + Q + ": " + Q + " + String(pms." + n + ")")
    if "MPU6050" in components:
        lines.append("float ax, ay, az, gx, gy, gz, mpu_temp; readMPU6050(ax, ay, az, gx, gy, gz, mpu_temp);")
        for n in ["ax", "ay", "az", "gx", "gy", "gz"]:
            payload_bits.append(Q + "\\\\" + Q + n + Q + "\\\\" + Q + ": " + Q + " + String(" + n + ")")
    if "BH1750" in components:
        lines.append("float lux = readBH1750();")
        payload_bits.append(Q + "\\\\" + Q + "lux" + Q + "\\\\" + Q + ": " + Q + " + String(lux)")
    if "TSL2561" in components:
        lines.append("float tsl_lux = readTSL2561();")
        payload_bits.append(Q + "\\\\" + Q + "tsl_lux" + Q + "\\\\" + Q + ": " + Q + " + String(tsl_lux)")
    if "MAX44009" in components:
        lines.append("float max_lux = readMAX44009();")
        payload_bits.append(Q + "\\\\" + Q + "max_lux" + Q + "\\\\" + Q + ": " + Q + " + String(max_lux)")
    if "SoilMoisture" in components:
        lines.append("int soilMoisture = readSoilMoisture();")
        payload_bits.append(Q + "\\\\" + Q + "soil_moisture" + Q + "\\\\" + Q + ": " + Q + " + String(soilMoisture)")
    if "WaterLevel" in components:
        lines.append("int waterLevel = readWaterLevel();")
        payload_bits.append(Q + "\\\\" + Q + "water_level" + Q + "\\\\" + Q + ": " + Q + " + String(waterLevel)")
    if "RainSensor" in components:
        lines.append("int rain = readRainSensor();")
        payload_bits.append(Q + "\\\\" + Q + "rain" + Q + "\\\\" + Q + ": " + Q + " + String(rain)")
    if "FlowSensor" in components:
        lines.append("static float totalLiters = 0; float flowRate = readFlowRate(totalLiters);")
        payload_bits.append(Q + "\\\\" + Q + "flow_rate" + Q + "\\\\" + Q + ": " + Q + " + String(flowRate)")
        payload_bits.append(Q + "\\\\" + Q + "total_liters" + Q + "\\\\" + Q + ": " + Q + " + String(totalLiters)")
    if "TDS_Sensor" in components:
        lines.append("float tds = readTDS();")
        payload_bits.append(Q + "\\\\" + Q + "tds" + Q + "\\\\" + Q + ": " + Q + " + String(tds)")
    if "LDR" in components:
        lines.append("int ldr_val = readLDR();")
        payload_bits.append(Q + "\\\\" + Q + "ldr" + Q + "\\\\" + Q + ": " + Q + " + String(ldr_val)")
    if any(c in _GPS for c in components):
        lines.append("GPSData gpsData; bool gpsValid = readGPS(gpsData);")
        for n in ["lat", "lng", "speed", "alt", "satellites"]:
            payload_bits.append(Q + "\\\\" + Q + "gps_" + n + Q + "\\\\" + Q + ": " + Q + " + String(gpsData." + n + ")")
    if "RC522" in components:
        lines.append("String rfid_uid = readRFID(); if (rfid_uid.length() > 0) {")
        payload_bits.append(Q + "\\\\" + Q + "rfid_uid" + Q + "\\\\" + Q + ": " + Q + "\\\\" + Q + Q + " + rfid_uid + " + Q + "\\\\" + Q + Q)
        lines.append("}")
    if "PN532" in components:
        lines.append("uint32_t nfc_id = readPN532();")
        payload_bits.append(Q + "\\\\" + Q + "nfc_id" + Q + "\\\\" + Q + ": " + Q + " + String(nfc_id)")

    if payload_bits:
        j = " + " + Q + "," + Q + " + ".join(payload_bits)
        fully = Q + "{" + Q + " + " + j + " + " + Q + "}" + Q
        lines.append("String payload = " + fully + ";")
        lines.append('publishTelemetry("data", payload.c_str());')

    lines.append("")
    if deep_sleep:
        lines.append('publishTelemetry("status", "\\\\"sleeping\\\\"");')
        lines.append("delay(100);")
        lines.append("esp_deep_sleep_start();")
    else:
        lines.append("delay(5000);")

    body = "\\\\n  ".join(lines)
    return "\\\\nvoid loop() {\\\\n  " + body + "\\\\n}\\\\n"


def _build_display_code(components, board, user_pins=None):
    code = ""
    if "OLED_SSD1306" in components:
        code += "\\n#define SCREEN_WIDTH 128\\n#define SCREEN_HEIGHT 64\\n#define OLED_RESET -1\\n"
        code += "Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);\\n\\n"
        code += "void initDisplay() {\\n"
        code += "  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {\\n"
        code += '    Serial.println(F("SSD1306 allocation failed"));\\n'
        code += "    return;\\n"
        code += "  }\\n"
        code += "  display.clearDisplay();\\n"
        code += "  display.setTextSize(1);\\n"
        code += "  display.setTextColor(SSD1306_WHITE);\\n"
        code += "  display.display();\\n}\\n\\n"
        code += "void showDisplay(float t, float h, const char* status) {\\n"
        code += "  display.clearDisplay();\\n"
        code += "  display.setTextSize(1);\\n"
        code += "  display.setCursor(0, 0);\\n"
        code += '  display.println("TOM IoT Device");\\n'
        code += "  display.drawLine(0, 10, 128, 10, SSD1306_WHITE);\\n"
        code += "  display.setCursor(0, 16);\\n"
        code += '  display.print("Temp: "); display.print(t); display.println(" C");\\n'
        code += "  display.setCursor(0, 26);\\n"
        code += '  display.print("Hum: "); display.print(h); display.println(" %");\\n'
        code += "  display.setCursor(0, 36);\\n"
        code += '  display.print("WiFi: "); display.println(WiFi.localIP().toString());\\n'
        code += "  display.setCursor(0, 46);\\n"
        code += '  display.print("Status: "); display.println(status);\\n'
        code += "  display.display();\\n}\\n"
    if "LCD_1602" in components or "LCD_2004" in components:
        cols = "20" if "LCD_2004" in components else "16"
        rows = "4" if "LCD_2004" in components else "2"
        code += "\\nLiquidCrystal_I2C lcd(0x27, " + cols + ", " + rows + ");\\n\\n"
        code += "void initDisplay() {\\n"
        code += "  lcd.init();\\n"
        code += "  lcd.backlight();\\n"
        code += '  lcd.setCursor(0, 0);\\n'
        code += '  lcd.print("TOM IoT Device");\\n'
        code += "}\\n\\n"
        code += "void showDisplay(float t, float h, const char* status) {\\n"
        code += "  lcd.clear();\\n"
        code += "  lcd.setCursor(0, 0);\\n"
        code += '  lcd.print("Temp: "); lcd.print(t); lcd.print(" C");\\n'
        code += "  lcd.setCursor(0, 1);\\n"
        code += '  lcd.print("Hum:  "); lcd.print(h); lcd.print(" %");\\n'
        code += "}\\n"
    return code


def _build_motor_code(components, board, user_pins=None):
    code = ""
    if "Servo_SG90" in components or "Servo" in components:
        p = _pin("Servo_SG90", board, user_pins)
        code += "\\n#define SERVO_PIN " + str(p) + "\\nServo servo;\\n\\n"
        code += "void setServoAngle(int angle) { angle = constrain(angle, 0, 180); servo.write(angle); }\\n"
    if "DC_Motor" in components:
        en = _pin("DC_Motor_ENA", board, user_pins)
        i1 = _pin("DC_Motor_IN1", board, user_pins)
        i2 = _pin("DC_Motor_IN2", board, user_pins)
        code += "\\n#define MOTOR_ENA " + str(en) + "\\n#define MOTOR_IN1 " + str(i1) + "\\n#define MOTOR_IN2 " + str(i2) + "\\n\\n"
        code += "void initDCmotor() { pinMode(MOTOR_ENA, OUTPUT); pinMode(MOTOR_IN1, OUTPUT); pinMode(MOTOR_IN2, OUTPUT); }\\n\\n"
        code += "void setMotor(int speed, bool forward) {\\n"
        code += "  speed = constrain(speed, 0, 255);\\n"
        code += "  analogWrite(MOTOR_ENA, speed);\\n"
        code += "  digitalWrite(MOTOR_IN1, forward ? HIGH : LOW);\\n"
        code += "  digitalWrite(MOTOR_IN2, forward ? LOW : HIGH);\\n}\\n\\n"
        code += "void stopMotor() { digitalWrite(MOTOR_ENA, LOW); digitalWrite(MOTOR_IN1, LOW); digitalWrite(MOTOR_IN2, LOW); }\\n"
    return code


def _build_audio_code(components, board, user_pins=None):
    code = ""
    if "DFPlayer_Mini" in components:
        rx = _pin("DFPlayer_RX", board, user_pins)
        tx = _pin("DFPlayer_TX", board, user_pins)
        code += "\\n#define DFPLAYER_RX " + str(rx) + "\\n#define DFPLAYER_TX " + str(tx) + "\\n"
        code += "SoftwareSerial dfSerial(DFPLAYER_RX, DFPLAYER_TX);\\n"
        code += "DFRobotDFPlayerMini dfPlayer;\\n\\n"
        code += "void initDFPlayer() {\\n"
        code += "  dfSerial.begin(9600);\\n"
        code += '  if (!dfPlayer.begin(dfSerial)) { Serial.println("DFPlayer Mini not found!"); }\\n'
        code += "  dfPlayer.volume(20);\\n}\\n\\n"
        code += "void playTrack(int track) { dfPlayer.play(track); }\\n"
        code += "void setVolume(int vol) { dfPlayer.volume(constrain(vol, 0, 30)); }\\n"
    if "MAX9814" in components:
        p = _pin("MAX9814", board, user_pins)
        code += "\\n#define MIC_PIN " + str(p) + "\\n\\nint readMicrophone() { return analogRead(MIC_PIN); }\\n"
    if "Speaker" in components:
        p = _pin("Speaker_DAC", board, user_pins)
        code += "\\n#define SPEAKER_PIN " + str(p) + "\\n\\n"
        code += "void playTone(int freq, int duration) {\\n"
        code += "  ledcSetup(0, freq, 8);\\n"
        code += "  ledcAttachPin(SPEAKER_PIN, 0);\\n"
        code += "  ledcWriteTone(0, freq);\\n"
        code += "  delay(duration);\\n"
        code += "  ledcDetachPin(SPEAKER_PIN);\\n}\\n"
    return code


def _build_camera_code(components):
    code = ""
    if "ESP32-CAM" in components or "OV2640" in components:
        code += '\\n#include "esp_camera.h"\\n'
        code += '#include "soc/soc.h"\\n'
        code += '#include "soc/rtc_cntl_reg.h"\\n\\n'
        code += "#define PWDN_GPIO_NUM 32\\n#define RESET_GPIO_NUM -1\\n"
        code += "#define XCLK_GPIO_NUM 0\\n#define SIOD_GPIO_NUM 26\\n#define SIOC_GPIO_NUM 27\\n"
        code += "#define Y9_GPIO_NUM 35\\n#define Y8_GPIO_NUM 34\\n#define Y7_GPIO_NUM 39\\n#define Y6_GPIO_NUM 36\\n"
        code += "#define Y5_GPIO_NUM 21\\n#define Y4_GPIO_NUM 19\\n#define Y3_GPIO_NUM 18\\n#define Y2_GPIO_NUM 5\\n"
        code += "#define VSYNC_GPIO_NUM 25\\n#define HREF_GPIO_NUM 23\\n#define PCLK_GPIO_NUM 22\\n\\n"
        code += "bool initCamera() {\\n"
        code += "  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);\\n"
        code += "  camera_config_t config;\\n"
        code += "  config.ledc_channel = LEDC_CHANNEL_0;\\n"
        code += "  config.ledc_timer = LEDC_TIMER_0;\\n"
        code += "  config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM;\\n"
        code += "  config.pin_d2 = Y4_GPIO_NUM; config.pin_d3 = Y5_GPIO_NUM;\\n"
        code += "  config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;\\n"
        code += "  config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;\\n"
        code += "  config.pin_xclk = XCLK_GPIO_NUM; config.pin_pclk = PCLK_GPIO_NUM;\\n"
        code += "  config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;\\n"
        code += "  config.pin_sscb_sda = SIOD_GPIO_NUM; config.pin_sscb_scl = SIOC_GPIO_NUM;\\n"
        code += "  config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;\\n"
        code += "  config.xclk_freq_hz = 20000000;\\n"
        code += "  config.pixel_format = PIXFORMAT_JPEG;\\n"
        code += "  config.frame_size = FRAMESIZE_SVGA;\\n"
        code += "  config.jpeg_quality = 12;\\n"
        code += "  config.fb_count = 1;\\n"
        code += "  esp_err_t err = esp_camera_init(&config);\\n"
        code += "  if (err != ESP_OK) { return false; }\\n"
        code += "  return true;\\n}\\n\\n"
        code += "bool capturePhoto(uint8_t** buf, size_t* len) {\\n"
        code += "  camera_fb_t* fb = esp_camera_fb_get();\\n"
        code += "  if (!fb) return false;\\n"
        code += "  *buf = fb->buf;\\n"
        code += "  *len = fb->len;\\n"
        code += "  esp_camera_fb_return(fb);\\n"
        code += "  return true;\\n}\\n"
    return code


def _build_actuator_code(components, board, user_pins=None):
    code = ""
    if "LED" in components:
        p = _pin("LED", board, user_pins)
        code += "\\n#define LED_PIN " + str(p) + "\\n\\n"
        code += "void setLED(bool on) { digitalWrite(LED_PIN, on ? HIGH : LOW); }\\n\\n"
        code += "void blinkLED(int times, int delayMs) { for (int i=0; i<times; i++) { digitalWrite(LED_PIN, HIGH); delay(delayMs); digitalWrite(LED_PIN, LOW); delay(delayMs); } }\\n"
    if "Relay" in components:
        p = _pin("Relay", board, user_pins)
        code += "\\n#define RELAY_PIN " + str(p) + "\\n\\nvoid setRelay(bool on) { digitalWrite(RELAY_PIN, on ? HIGH : LOW); }\\n"
    if "Buzzer" in components:
        p = _pin("Buzzer", board, user_pins)
        code += "\\n#define BUZZER_PIN " + str(p) + "\\n\\n"
        code += "void buzzerBeep(int freq, int duration) {\\n"
        code += "  ledcSetup(1, freq, 8);\\n"
        code += "  ledcAttachPin(BUZZER_PIN, 1);\\n"
        code += "  ledcWriteTone(1, freq);\\n"
        code += "  delay(duration);\\n"
        code += "  ledcWriteTone(1, 0);\\n"
        code += "  ledcDetachPin(BUZZER_PIN);\\n}\\n"
    if "RGB_LED" in components:
        r = _pin("RGB_LED_R", board, user_pins)
        g = _pin("RGB_LED_G", board, user_pins)
        b = _pin("RGB_LED_B", board, user_pins)
        code += "\\n#define RGB_R " + str(r) + "\\n#define RGB_G " + str(g) + "\\n#define RGB_B " + str(b) + "\\n\\n"
        code += "void initRGB() { pinMode(RGB_R, OUTPUT); pinMode(RGB_G, OUTPUT); pinMode(RGB_B, OUTPUT); }\\n\\n"
        code += "void setRGB(int red, int green, int blue) {\\n"
        code += "  analogWrite(RGB_R, constrain(red, 0, 255));\\n"
        code += "  analogWrite(RGB_G, constrain(green, 0, 255));\\n"
        code += "  analogWrite(RGB_B, constrain(blue, 0, 255));\\n}\\n"
    if "Vibration" in components:
        p = _pin("Vibration", board, user_pins)
        code += "\\n#define VIB_PIN " + str(p) + "\\n\\nvoid setVibration(bool on) { digitalWrite(VIB_PIN, on ? HIGH : LOW); }\\n"
    return code


def _esp_code(board, components, wifi, mqtt, user_pins=None, deep_sleep=False, protocols=None):
    if protocols is None:
        protocols = ["mqtt"]
    if user_pins is None:
        user_pins = {}
    lines = []
    lines.append("// ============================================================")
    lines.append("// TOM IoT Engine -- Generated " + board.upper() + " Firmware")
    lines.append("// ============================================================")
    lines.append("")
    lines.append(_build_includes(components, protocols))
    lines.append("")
    lines.append(_build_wifi_config(wifi))
    lines.append("")
    lines.append(_build_mqtt_config(mqtt))
    lines.append("")
    lines.append(_build_wifi_setup())
    lines.append(_build_mqtt_setup())
    lines.append(_build_sensor_readers(components, board, user_pins))
    lines.append(_build_display_code(components, board, user_pins))
    lines.append(_build_motor_code(components, board, user_pins))
    lines.append(_build_audio_code(components, board, user_pins))
    lines.append(_build_camera_code(components))
    lines.append(_build_actuator_code(components, board, user_pins))
    lines.append(_build_setup(components, board, user_pins))
    lines.append(_build_loop(components, deep_sleep))
    if "OLED_SSD1306" in components or "LCD_1602" in components or "LCD_2004" in components:
        lines.append("")
        lines.append('// Uncomment: showDisplay(dht_t, dht_h, "online");')
    lines.append("")
    lines.append("// ============================================================")
    lines.append("// End of TOM Generated Firmware")
    lines.append("// ============================================================")
    return "\\n".join(lines)



# ===================================================================
# MicroPython code generation
# ===================================================================

def _micropython_code(board, components, wifi, mqtt, user_pins=None, deep_sleep=False):
    if user_pins is None:
        user_pins = {}
    code = []
    code.append("# ============================================================")
    code.append("# TOM IoT Engine -- MicroPython for " + board.upper())
    code.append("# ============================================================")
    code.append("")

    imports = []
    imports.append("import time, json, machine, network")
    if mqtt:
        imports.append("from umqtt.simple import MQTTClient")
    if any(c in _I2C_COMPONENTS for c in components):
        imports.append("from machine import I2C, Pin")
    if any(c in ("DHT11", "DHT22", "DHT") for c in components):
        imports.append("import dht")
    if "OLED_SSD1306" in components:
        imports.append("from ssd1306 import SSD1306_I2C")
    if "DS18B20" in components:
        imports.append("import onewire, ds18x20")
    if any(c in _GPS for c in components):
        imports.append("from machine import UART")
    if "Servo_SG90" in components or "Servo" in components:
        imports.append("from machine import PWM")
    if deep_sleep:
        imports.append("from machine import deepsleep")
    code.append(chr(10).join(imports))

    ssid = wifi.get("ssid", "YourWiFiSSID") if wifi else "YourWiFiSSID"
    pw = wifi.get("password", "YourWiFiPassword") if wifi else "YourWiFiPassword"
    if mqtt:
        mqtt_host = mqtt.get("broker", "broker.emqx.io")
        mqtt_port = mqtt.get("port", 1883)
        mqtt_user = mqtt.get("username", "")
        mqtt_pass = mqtt.get("password", "")
        mqtt_cid = mqtt.get("client_id", "tom_iot_mp")
        mqtt_topic = mqtt.get("topic_prefix", "tom/device")
    else:
        mqtt_host = "broker.emqx.io"
        mqtt_port = 1883
        mqtt_user = ""
        mqtt_pass = ""
        mqtt_cid = "tom_iot_mp"
        mqtt_topic = "tom/device"

    code.append("")
    code.append("# WiFi credentials")
    code.append('WIFI_SSID = ' + chr(34) + ssid + chr(34))
    code.append('WIFI_PASSWORD = ' + chr(34) + pw + chr(34))
    code.append('MQTT_HOST = ' + chr(34) + mqtt_host + chr(34))
    code.append('MQTT_PORT = ' + str(mqtt_port))
    code.append('MQTT_USER = ' + chr(34) + mqtt_user + chr(34))
    code.append('MQTT_PASS = ' + chr(34) + mqtt_pass + chr(34))
    code.append('MQTT_CLIENT_ID = ' + chr(34) + mqtt_cid + chr(34))
    code.append('MQTT_TOPIC_PREFIX = ' + chr(34) + mqtt_topic + chr(34))
    code.append("")

    b = board
    for comp in components:
        if comp in _ESP32_DEFAULT_PINS or comp in _ESP8266_DEFAULT_PINS:
            p = _pin(comp, b, user_pins)
            var = comp.replace("-", "_")
            code.append(var.upper() + "_PIN = " + str(p))
    code.append("")

    # WiFi/MQTT functions
    code.append("def connect_wifi():")
    code.append("    wlan = network.WLAN(network.STA_IF)")
    code.append("    wlan.active(True)")
    code.append("    if not wlan.isconnected():")
    code.append('        print("Connecting to WiFi...")')
    code.append("        wlan.connect(WIFI_SSID, WIFI_PASSWORD)")
    code.append("        timeout = 30")
    code.append("        while not wlan.isconnected() and timeout > 0:")
    code.append("            time.sleep(1)")
    code.append("            timeout -= 1")
    code.append("    if wlan.isconnected():")
    code.append('        print("WiFi:", wlan.ifconfig())')
    code.append("    return wlan")
    code.append("")

    code.append("def connect_mqtt():")
    code.append("    try:")
    code.append("        client = MQTTClient(MQTT_CLIENT_ID, MQTT_HOST, port=MQTT_PORT,")
    code.append("                            user=MQTT_USER, password=MQTT_PASS)")
    code.append("        client.set_callback(mqtt_callback)")
    code.append("        client.connect()")
    code.append("        client.subscribe(MQTT_TOPIC_PREFIX + '/cmd/#')")
    code.append('        print("MQTT connected")')
    code.append("        return client")
    code.append("    except Exception as e:")
    code.append('        print("MQTT failed:", e)')
    code.append("        return None")
    code.append("")

    code.append("def mqtt_callback(topic, msg):")
    code.append('    print("MQTT:", topic, msg)')
    code.append("    handle_command(topic.decode(), msg.decode())")
    code.append("")

    code.append("def publish_telemetry(client, topic_suffix, payload, retain=False):")
    code.append("    if client is None:")
    code.append("        return")
    code.append("    topic = MQTT_TOPIC_PREFIX + '/' + topic_suffix")
    code.append("    client.publish(topic, json.dumps(payload))")
    code.append("")

    code.append("def handle_command(topic, payload):")
    code.append("    if payload == 'restart':")
    code.append("        machine.reset()")
    code.append("")
    code.append("# Sensor readers")
    code.append("")

    # Sensor-specific MicroPython code
    if any(c in ("DHT11", "DHT22", "DHT") for c in components):
        dp = _pin("DHT", b, user_pins)
        dt = "dht.DHT22" if "DHT22" in components else "dht.DHT11"
        code.append("def read_dht():")
        code.append("    sensor = " + dt + "(machine.Pin(" + str(dp) + "))")
        code.append("    try:")
        code.append("        sensor.measure()")
        code.append("        return sensor.temperature(), sensor.humidity()")
        code.append("    except Exception as e:")
        code.append('        print("DHT error:", e)')
        code.append("        return None, None")
        code.append("")

    # Main loop
    code.append("async def main_loop():")
    code.append("    wlan = connect_wifi()")
    code.append("    client = connect_mqtt()")
    code.append("    while True:")
    code.append("        if client:")
    code.append("            try:")
    code.append("                client.check_msg()")
    code.append("            except:")
    code.append("                client = connect_mqtt()")
    code.append("        payload = {}")
    code.append("        payload['device_id'] = ':'.join('{:02x}'.format(b) for b in wlan.config('mac')) if wlan.config('mac') else 'unknown'")
    code.append("")

    code.append("        if client:")
    code.append('            publish_telemetry(client, "data", payload)')
    code.append("        await asyncio.sleep(5)")
    code.append("")
    code.append("import asyncio")
    code.append("asyncio.run(main_loop())")

    return "\n".join(code)


# ===================================================================
# IoT Communication Protocol Code Generation
# MQTT, HTTP, WebSocket, CoAP, BLE, LoRaWAN, Zigbee, I2C, SPI, UART, OneWire
# ===================================================================

def _protocol_mqtt(role="client", **kw):
    return '#include <WiFi.h>\n#include <PubSubClient.h>\nconst char* ssid = "WIFI_SSID";\nconst char* password = "WIFI_PASS";\nconst char* mqtt_server = "broker.emqx.io";\nconst int mqtt_port = 1883;\nWiFiClient espClient;\nPubSubClient client(espClient);\nvoid callback(char* t, byte* p, unsigned int l) { Serial.print("MQTT: "); Serial.write(p, l); Serial.println(); }\nvoid reconnect() { while (!client.connected()) { if (client.connect("tom_mqtt_client")) { client.subscribe("tom/device/cmd"); } else { delay(5000); } } }\nvoid setup() { Serial.begin(115200); WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); } client.setServer(mqtt_server, mqtt_port); client.setCallback(callback); }\nvoid loop() { if (!client.connected()) reconnect(); client.loop(); static unsigned long last=0; if (millis()-last>10000) { last=millis(); client.publish("tom/device/data","{\"temp\":25.3}"); } }'

def _protocol_http(role="client", **kw):
    if role == "client":
        return '#include <WiFi.h>\n#include <HTTPClient.h>\nconst char* ssid = "WIFI_SSID";\nconst char* password = "WIFI_PASS";\nvoid setup() { Serial.begin(115200); WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); } }\nvoid loop() { if (WiFi.status() == WL_CONNECTED) { HTTPClient http; http.begin("http://api.example.com/data"); int code = http.GET(); if (code > 0) { Serial.println(http.getString()); } http.end(); } delay(30000); }'
    else:
        return '#include <WiFi.h>\n#include <WebServer.h>\nconst char* ssid = "WIFI_SSID";\nconst char* password = "WIFI_PASS";\nWebServer server(80);\nvoid handleRoot() { server.send(200, "text/plain", "TOM IoT REST API"); }\nvoid setup() { Serial.begin(115200); WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); } server.on("/", handleRoot); server.begin(); }\nvoid loop() { server.handleClient(); }'

def _protocol_websocket(role="client", **kw):
    return '#include <WiFi.h>\n#include <WebSocketsClient.h>\nconst char* ssid = "WIFI_SSID";\nconst char* password = "WIFI_PASS";\nWebSocketsClient webSocket;\nvoid webSocketEvent(WStype_t t, uint8_t* p, size_t l) { switch(t) { case WStype_TEXT: Serial.printf("WS: %s\n", p); break; } }\nvoid setup() { Serial.begin(115200); WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); } webSocket.begin("echo.websocket.org", 443, "/"); webSocket.onEvent(webSocketEvent); }\nvoid loop() { webSocket.loop(); static unsigned long last=0; if (millis()-last>5000) { last=millis(); webSocket.sendTXT("{\"temp\":25.3}"); } }'

def _protocol_ble(role="peripheral", **kw):
    if role == "peripheral":
        return '#include <BLEDevice.h>\n#include <BLEUtils.h>\n#include <BLEServer.h>\n#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"\n#define CHAR_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"\nBLECharacteristic* pChar;\nvoid setup() { Serial.begin(115200); BLEDevice::init("TOM_BLE"); BLEServer* srv = BLEDevice::createServer(); BLEService* svc = srv->createService(SERVICE_UUID); pChar = svc->createCharacteristic(CHAR_UUID, BLECharacteristic::PROPERTY_READ|BLECharacteristic::PROPERTY_NOTIFY); svc->start(); BLEDevice::getAdvertising()->start(); }\nvoid loop() { delay(5000); pChar->setValue("25.3"); pChar->notify(); }'
    else:
        return '#include <BLEDevice.h>\n#include <BLEUtils.h>\n#include <BLEClient.h>\n#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"\n#define CHAR_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"\nbool connected=false;\nvoid setup() { Serial.begin(115200); BLEDevice::init("TOM_Central"); }\nvoid loop() { if (!connected) { BLEScan* s = BLEDevice::getScan(); s->setActiveScan(true); BLEScanResults r = s->start(5); for (int i=0; i<r.getCount(); i++) { if (r.getDevice(i).haveServiceUUID() && r.getDevice(i).getServiceUUID().equals(BLEUUID(SERVICE_UUID))) { connected=true; break; } } } delay(5000); }'

def _protocol_lorawan(role="end-device", **kw):
    return '#include <lmic.h>\n#include <hal/hal.h>\n#include <SPI.h>\nstatic const u1_t PROGMEM APPEUI[8]={0};\nvoid os_getArtEui(u1_t* b) { memcpy_P(b, APPEUI, 8); }\nstatic const u1_t PROGMEM DEVEUI[8]={0};\nvoid os_getDevEui(u1_t* b) { memcpy_P(b, DEVEUI, 8); }\nstatic const u1_t PROGMEM APPKEY[16]={0};\nvoid os_getDevKey(u1_t* b) { memcpy_P(b, APPKEY, 16); }\nconst lmic_pinmap lmic_pins = { .nss=18, .rxtx=LMIC_UNUSED_PIN, .rst=23, .dio={26,33,32} };\nvoid onEvent(ev_t ev) { switch(ev) { case EV_JOINED: Serial.println("Joined"); break; } }\nvoid setup() { Serial.begin(115200); os_init(); LMIC_reset(); LMIC_startJoining(); }\nvoid loop() { os_runloop_once(); static unsigned long last=0; if (millis()-last>60000 && !(LMIC.opmode & OP_JOINING)) { last=millis(); LMIC_setTxData2(1, (uint8_t[]){0x01,0x19,0x3C}, 3, 0); } }'

def _protocol_i2c(role="master", **kw):
    return '#include <Wire.h>\nvoid setup() { Serial.begin(115200); Wire.begin(21, 22); for (uint8_t a=1; a<127; a++) { Wire.beginTransmission(a); if (Wire.endTransmission()==0) { Serial.print("I2C: 0x"); Serial.println(a, HEX); } } }\nvoid loop() { delay(1000); }'

def _protocol_uart(role="transmit", **kw):
    return '#include <HardwareSerial.h>\nHardwareSerial uart(2);\nvoid setup() { Serial.begin(115200); uart.begin(115200, SERIAL_8N1, 16, 17); }\nvoid loop() { uart.println("TOM_PING"); if (uart.available()) { Serial.println(uart.readString()); } delay(2000); }'

def _protocol_onewire(role="master", **kw):
    return '#include <OneWire.h>\n#include <DallasTemperature.h>\n#define ONE_WIRE_BUS 4\nOneWire oneWire(ONE_WIRE_BUS);\nDallasTemperature sensors(&oneWire);\nvoid setup() { Serial.begin(115200); sensors.begin(); Serial.print("Found "); Serial.println(sensors.getDeviceCount()); }\nvoid loop() { sensors.requestTemperatures(); float t = sensors.getTempCByIndex(0); if (t != DEVICE_DISCONNECTED_C) { Serial.print("Temp: "); Serial.println(t); } delay(5000); }'

_PROTOCOL_GENERATORS = {
    "mqtt": _protocol_mqtt,
    "http": _protocol_http,
    "rest": _protocol_http,
    "websocket": _protocol_websocket,
    "ble": _protocol_ble,
    "lorawan": _protocol_lorawan,
    "i2c": _protocol_i2c,
    "uart": _protocol_uart,
    "serial": _protocol_uart,
    "onewire": _protocol_onewire,
}


# ===================================================================
# 5. Standalone Sensor Code Generators
# ===================================================================

_SENSOR_GENERATORS: Dict[str, callable] = {}


def _reg_sensor(name: str):
    def dec(f):
        _SENSOR_GENERATORS[name] = f
        return f
    return dec


@_reg_sensor("DHT11")
@_reg_sensor("DHT22")
def _gen_dht(sensor: str, board: str = "esp32", **kw) -> str:
    dt = "DHT22" if "22" in sensor else "DHT11"
    c = []
    c.append("#include <DHT.h>")
    c.append("#include <DHT_U.h>")
    c.append("")
    c.append("#define DHTPIN 4")
    c.append("#define DHTTYPE " + dt)
    c.append("")
    c.append("DHT dht(DHTPIN, DHTTYPE);")
    c.append("")
    c.append("void setup() {")
    c.append("  Serial.begin(115200);")
    c.append("  dht.begin();")
    c.append('  Serial.println("{sensor} ready");')
    c.append("}")
    c.append("")
    c.append("void loop() {")
    c.append("  float h = dht.readHumidity();")
    c.append("  float t = dht.readTemperature();")
    c.append("  if (isnan(h) || isnan(t)) {")
    c.append('    Serial.println("Read failed");')
    c.append("    return;")
    c.append("  }")
    c.append('  Serial.print("Temp: "); Serial.print(t); Serial.println(" C");')
    c.append('  Serial.print("Hum: "); Serial.print(h); Serial.println(" %");')
    c.append("  delay(2000);")
    c.append("}")
    return "\n".join(c)

@_reg_sensor("BME280")
def _gen_bme280(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_BME280.h>")
    c.append("")
    c.append("Adafruit_BME280 bme;")
    c.append("")
    c.append("void setup() {")
    c.append("  Serial.begin(115200);")
    c.append('  if (!bme.begin(0x76)) { Serial.println("BME280 not found"); while(1); }')
    c.append("}")
    c.append("")
    c.append("void loop() {")
    c.append('  Serial.print("Temp: "); Serial.print(bme.readTemperature()); Serial.println(" C");')
    c.append('  Serial.print("Hum: "); Serial.print(bme.readHumidity()); Serial.println(" %");')
    c.append('  Serial.print("Pres: "); Serial.print(bme.readPressure()/100.0); Serial.println(" hPa");')
    c.append("  delay(2000);")
    c.append("}")
    return "\n".join(c)

@_reg_sensor("SHT30")
def _gen_sht30(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_SHT31.h>")
    c.append("")
    c.append("Adafruit_SHT31 sht;")
    c.append("")
    c.append("void setup() {")
    c.append("  Serial.begin(115200);")
    c.append('  if (!sht.begin(0x44)) { Serial.println("SHT30 not found"); while(1); }')
    c.append("}")
    c.append("")
    c.append("void loop() {")
    c.append("  float t = sht.readTemperature(), h = sht.readHumidity();")
    c.append("  if (!isnan(t) && !isnan(h)) {")
    c.append('    Serial.print("Temp: "); Serial.print(t); Serial.print(" Hum: "); Serial.println(h);')
    c.append("  }")
    c.append("  delay(2000);")
    c.append("}")
    return "\n".join(c)

@_reg_sensor("DS18B20")
def _gen_ds18b20(**kw) -> str:
    c = []
    c.append("#include <OneWire.h>")
    c.append("#include <DallasTemperature.h>")
    c.append("#define ONE_WIRE_BUS 4")
    c.append("OneWire oneWire(ONE_WIRE_BUS);")
    c.append("DallasTemperature sensors(&oneWire);")
    c.append("")
    c.append("void setup() {")
    c.append("  Serial.begin(115200); sensors.begin();")
    c.append('  Serial.print("Found "); Serial.print(sensors.getDeviceCount()); Serial.println(" DS18B20");')
    c.append("}")
    c.append("")
    c.append("void loop() {")
    c.append("  sensors.requestTemperatures();")
    c.append("  float t = sensors.getTempCByIndex(0);")
    c.append('  if (t != DEVICE_DISCONNECTED_C) { Serial.print("Temp: "); Serial.println(t); }')
    c.append("  delay(3000);")
    c.append("}")
    return "\n".join(c)

@_reg_sensor("LM35")
def _gen_lm35(**kw) -> str:
    return '#define LM35_PIN 34\nvoid setup() { Serial.begin(115200); }\nvoid loop() { int r = analogRead(LM35_PIN); float t = (r/4095.0)*3300.0/10.0; Serial.println(t); delay(1000); }'

@_reg_sensor("PIR")
@_reg_sensor("HC-SR501")
def _gen_pir(**kw) -> str:
    return '#define PIR_PIN 5\nvoid setup() { Serial.begin(115200); pinMode(PIR_PIN, INPUT); }\nvoid loop() { Serial.println(digitalRead(PIR_PIN) ? "Motion" : "Clear"); delay(500); }'

@_reg_sensor("RCWL-0516")
def _gen_rcwl(**kw) -> str:
    return '#define RCWL_PIN 18\nvoid setup() { Serial.begin(115200); pinMode(RCWL_PIN, INPUT); }\nvoid loop() { Serial.println(digitalRead(RCWL_PIN) ? "Radar" : "Clear"); delay(500); }'

@_reg_sensor("HC-SR04")
@_reg_sensor("Ultrasonic")
def _gen_ultrasonic(**kw) -> str:
    c = []
    c.append("#define TRIG 16")
    c.append("#define ECHO 17")
    c.append("void setup() { Serial.begin(115200); pinMode(TRIG, OUTPUT); pinMode(ECHO, INPUT); }")
    c.append("float dist() {")
    c.append("  digitalWrite(TRIG, LOW); delayMicroseconds(2);")
    c.append("  digitalWrite(TRIG, HIGH); delayMicroseconds(10); digitalWrite(TRIG, LOW);")
    c.append("  long d = pulseIn(ECHO, HIGH, 30000);")
    c.append("  return d == 0 ? -1 : d * 0.034 / 2;")
    c.append("}")
    c.append('void loop() { float d = dist(); if (d > 0) { Serial.print(d); Serial.println(" cm"); } delay(1000); }')
    return "\n".join(c)

@_reg_sensor("MQ-2")
@_reg_sensor("MQ-3")
@_reg_sensor("MQ-4")
@_reg_sensor("MQ-5")
@_reg_sensor("MQ-6")
@_reg_sensor("MQ-7")
@_reg_sensor("MQ-8")
@_reg_sensor("MQ-9")
@_reg_sensor("MQ-135")
def _gen_mq(sensor: str, **kw) -> str:
    return '#define MQ_PIN 34\nvoid setup() { Serial.begin(115200); Serial.println("\"' + sensor + '\" warming"); }\nvoid loop() { int r = analogRead(MQ_PIN); float v = r * (3.3/4095.0); Serial.println((3.3-v)/v, 4); delay(2000); }'

@_reg_sensor("CCS811")
def _gen_ccs811(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_CCS811.h>")
    c.append("Adafruit_CCS811 ccs;")
    c.append("void setup() { Serial.begin(115200); if(!ccs.begin()){Serial.println(\"CCS811 fail\");while(1);} }")
    c.append('void loop() {')
    c.append('  if (ccs.available() && !ccs.readData()) {')
    c.append('    Serial.print("CO2:"); Serial.print(ccs.geteCO2()); Serial.print(" TVOC:"); Serial.println(ccs.getTVOC());')
    c.append('  }')
    c.append('  delay(1000);')
    c.append('}')
    return "\n".join(c)

@_reg_sensor("PMS5003")
def _gen_pms5003(**kw) -> str:
    c = []
    c.append("#include <SoftwareSerial.h>")
    c.append("#define PMS_RX 16")
    c.append("#define PMS_TX 17")
    c.append("SoftwareSerial pms(PMS_RX, PMS_TX);")
    c.append("void setup() { Serial.begin(115200); pms.begin(9600); }")
    c.append("bool readPMS(uint16_t& pm1, uint16_t& pm25, uint16_t& pm10) {")
    c.append("  uint8_t buf[32]; if (pms.available()<32) return false;")
    c.append("  if (pms.read()!=0x42) return false; pms.read();")
    c.append("  for(int i=0;i<30;i++) buf[i]=pms.read();")
    c.append("  pm1=(buf[6]<<8)|buf[7]; pm25=(buf[8]<<8)|buf[9]; pm10=(buf[10]<<8)|buf[11];")
    c.append("  return true;")
    c.append("}")
    c.append('void loop() { uint16_t a,b,c; if(readPMS(a,b,c)){Serial.print(a);Serial.print(" ");Serial.print(b);Serial.print(" ");Serial.println(c);} delay(3000); }')
    return "\n".join(c)

@_reg_sensor("BMP180")
@_reg_sensor("BMP280")
def _gen_bmp(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_BMP280.h>")
    c.append("Adafruit_BMP280 bmp;")
    c.append('void setup() { Serial.begin(115200); if (!bmp.begin(0x76)) { Serial.println("BMP not found"); while(1); } }')
    c.append('void loop() {')
    c.append('  Serial.print("T:"); Serial.print(bmp.readTemperature()); Serial.print(" P:"); Serial.println(bmp.readPressure()/100.0);')
    c.append('  delay(2000);')
    c.append('}')
    return "\n".join(c)

@_reg_sensor("MPU6050")
def _gen_mpu6050(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_MPU6050.h>")
    c.append("#include <Adafruit_Sensor.h>")
    c.append("Adafruit_MPU6050 mpu;")
    c.append('void setup() {')
    c.append('  Serial.begin(115200);')
    c.append('  if (!mpu.begin()) { Serial.println("MPU6050 not found"); while(1); }')
    c.append('  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);')
    c.append('}')
    c.append('void loop() {')
    c.append('  sensors_event_t a, g, t; mpu.getEvent(&a, &g, &t);')
    c.append('  Serial.print("AX:"); Serial.print(a.acceleration.x); Serial.print(" AY:"); Serial.print(a.acceleration.y); Serial.print(" AZ:"); Serial.println(a.acceleration.z);')
    c.append('  delay(500);')
    c.append('}')
    return "\n".join(c)

@_reg_sensor("BH1750")
def _gen_bh1750(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <BH1750.h>")
    c.append("BH1750 lightMeter;")
    c.append("void setup() { Serial.begin(115200); Wire.begin(); lightMeter.begin(); }")
    c.append('void loop() { Serial.print("Lux: "); Serial.println(lightMeter.readLightLevel()); delay(500); }')
    return "\n".join(c)

@_reg_sensor("TSL2561")
def _gen_tsl2561(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_TSL2561_U.h>")
    c.append("Adafruit_TSL2561_Unified tsl = Adafruit_TSL2561_Unified(TSL2561_ADDR_FLOAT, 12345);")
    c.append("void setup() { Serial.begin(115200); tsl.begin(); tsl.enableAutoRange(true); }")
    c.append('void loop() { sensors_event_t e; tsl.getEvent(&e); if(e.light){Serial.print("Lux: ");Serial.println(e.light);} delay(500); }')
    return "\n".join(c)

@_reg_sensor("SoilMoisture")
def _gen_soil(**kw) -> str:
    return '#define SOIL 34\nvoid setup(){Serial.begin(115200);}\nvoid loop(){int r=analogRead(SOIL);Serial.print("Moisture:");Serial.println(map(r,0,4095,100,0));delay(1000);}'

@_reg_sensor("LDR")
def _gen_ldr(**kw) -> str:
    return '#define LDR_PIN 34\nvoid setup(){Serial.begin(115200);}\nvoid loop(){Serial.println(analogRead(LDR_PIN));delay(500);}'

@_reg_sensor("NEO-6M")
@_reg_sensor("NEO-7M")
@_reg_sensor("NEO-8M")
def _gen_gps(sensor: str, **kw) -> str:
    c = []
    c.append("#include <SoftwareSerial.h>")
    c.append("#include <TinyGPS++.h>")
    c.append("#define GPS_RX 16")
    c.append("#define GPS_TX 17")
    c.append("TinyGPSPlus gps;")
    c.append("SoftwareSerial gpsSerial(GPS_RX, GPS_TX);")
    c.append('void setup() { Serial.begin(115200); gpsSerial.begin(9600); Serial.println("\"' + sensor + '\" ready"); }')
    c.append('void loop() {')
    c.append('  while (gpsSerial.available() > 0) gps.encode(gpsSerial.read());')
    c.append('  if (gps.location.isUpdated()) {')
    c.append('    Serial.print("Lat:"); Serial.print(gps.location.lat(),6);')
    c.append('    Serial.print(" Lng:"); Serial.print(gps.location.lng(),6);')
    c.append('    Serial.print(" Sats:"); Serial.println(gps.satellites.value());')
    c.append('  }')
    c.append('}')
    return "\n".join(c)

@_reg_sensor("RC522")
def _gen_rc522(**kw) -> str:
    c = []
    c.append("#include <SPI.h>")
    c.append("#include <MFRC522.h>")
    c.append("#define RST_PIN 22")
    c.append("#define SS_PIN 5")
    c.append("MFRC522 rfid(SS_PIN, RST_PIN);")
    c.append("void setup() { Serial.begin(115200); SPI.begin(); rfid.PCD_Init(); }")
    c.append("void loop() {")
    c.append("  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;")
    c.append('  Serial.print("UID: ");')
    c.append("  for (byte i = 0; i < rfid.uid.size; i++) { if (rfid.uid.uidByte[i] < 0x10) Serial.print(\"0\"); Serial.print(rfid.uid.uidByte[i], HEX); }")
    c.append("  Serial.println(); rfid.PICC_HaltA(); delay(1000);")
    c.append("}")
    return "\n".join(c)

@_reg_sensor("PN532")
def _gen_pn532(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_PN532.h>")
    c.append("#define PN532_IRQ 4")
    c.append("#define PN532_RESET 5")
    c.append("Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);")
    c.append('void setup() {')
    c.append('  Serial.begin(115200); nfc.begin();')
    c.append('  if (!nfc.getFirmwareVersion()) { Serial.println("PN532 not found"); while(1); }')
    c.append('  nfc.SAMConfig();')
    c.append('}')
    c.append('void loop() {')
    c.append('  uint8_t uid[7], len;')
    c.append('  if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &len)) {')
    c.append('    Serial.print("UID: "); for(uint8_t i=0;i<len;i++){Serial.print(uid[i],HEX);} Serial.println(); delay(1000);')
    c.append('  }')
    c.append('}')
    return "\n".join(c)

@_reg_sensor("MAX44009")
def _gen_max44009(**kw) -> str:
    c = []
    c.append("#include <Wire.h>")
    c.append("#include <Adafruit_MAX44009.h>")
    c.append("Adafruit_MAX44009 max44009;")
    c.append('void setup() { Serial.begin(115200); if (!max44009.begin()) { Serial.println("MAX44009 fail"); while(1); } }')
    c.append('void loop() { Serial.print("Lux: "); Serial.println(max44009.readLux()); delay(500); }')
    return "\n".join(c)

# ===================================================================
# 6. IoT Backend Integration Code
# ===================================================================


def _backend_aws(**kw) -> str:
    return ("#include <WiFiClientSecure.h>\n"
            "#include <PubSubClient.h>\n"
            "const char* ssid = \"WIFI_SSID\";\n"
            "const char* password = \"WIFI_PASS\";\n"
            "const char* aws_endpoint = \"YOUR.iot.us-east-1.amazonaws.com\";\n"
            "const int aws_port = 8883;\n"
            "WiFiClientSecure wifiClient;\n"
            "PubSubClient mqttClient(wifiClient);\n"
            "const char* shadow_topic = \"$aws/things/TOM_Device/shadow/update\";\n"
            "\n"
            "void setup() {\n"
            "  Serial.begin(115200);\n"
            "  WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); }\n"
            "  wifiClient.setCACert(\"-----BEGIN CERTIFICATE-----\\\n...\\\n-----END CERTIFICATE-----\");\n"
            "  wifiClient.setCertificate(\"-----BEGIN CERTIFICATE-----\\\n...\");\n"
            "  wifiClient.setPrivateKey(\"-----BEGIN RSA PRIVATE KEY-----\\\n...\");\n"
            "  mqttClient.setServer(aws_endpoint, aws_port);\n"
            "  while (!mqttClient.connected()) {\n"
            "    if (mqttClient.connect(\"TOM_Device\")) {\n"
            "      Serial.println(\"AWS IoT connected\");\n"
            "      mqttClient.subscribe(\"$aws/things/TOM_Device/shadow/update/accepted\");\n"
            "      mqttClient.publish(shadow_topic, \"{\\\"state\\\":{\\\"reported\\\":{\\\"status\\\":\\\"online\\\"}}}\");\n"
            "    } else delay(5000);\n"
            "  }\n"
            "}\n"
            "\n"
            "void loop() {\n"
            "  mqttClient.loop();\n"
            "  static unsigned long last = 0;\n"
            "  if (millis() - last > 30000) {\n"
            "    last = millis();\n"
            "    mqttClient.publish(shadow_topic, \"{\\\"state\\\":{\\\"reported\\\":{\\\"temperature\\\":25.3}}}\");\n"
            "  }\n"
            "}\n")

def _backend_azure(**kw) -> str:
    return ("#include <WiFiClientSecure.h>\n"
            "#include <PubSubClient.h>\n"
            "const char* ssid = \"WIFI_SSID\";\n"
            "const char* password = \"WIFI_PASS\";\n"
            "const char* host = \"YOUR_HUB.azure-devices.net\";\n"
            "const char* device_id = \"YOUR_DEVICE_ID\";\n"
            "const char* sas_token = \"SharedAccessSignature sr=...\";\n"
            "WiFiClientSecure wifiClient;\n"
            "PubSubClient mqttClient(wifiClient);\n"
            "\n"
            "void setup() {\n"
            "  Serial.begin(115200);\n"
            "  WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); }\n"
            "  wifiClient.setInsecure();\n"
            "  mqttClient.setServer(host, 8883);\n"
            "  while (!mqttClient.connected()) {\n"
            "    if (mqttClient.connect((String(device_id)+\"/?api-version=2021-04-12\").c_str(), \n"
            "        (String(host)+\"/\"+String(device_id)+\"/?api-version=2021-04-12\").c_str(), sas_token))\n"
            "      break;\n"
            "    delay(5000);\n"
            "  }\n"
            "  Serial.println(\"Azure connected\");\n"
            "  mqttClient.subscribe((\"devices/\"+String(device_id)+\"/messages/devicebound/#\").c_str());\n"
            "}\n"
            "\n"
            "void loop() {\n"
            "  mqttClient.loop();\n"
            "  static unsigned long last = 0;\n"
            "  if (millis() - last > 30000) {\n"
            "    last = millis();\n"
            "    mqttClient.publish((\"devices/\"+String(device_id)+\"/messages/events/\").c_str(),\n"
            "                     \"{\\\"temp\\\":25.3}\");\n"
            "  }\n"
            "}\n")

def _backend_thingsboard(**kw) -> str:
    return ("#include <WiFi.h>\n"
            "#include <PubSubClient.h>\n"
            "const char* ssid = \"WIFI_SSID\";\n"
            "const char* password = \"WIFI_PASS\";\n"
            "const char* tb_host = \"thingsboard.cloud\";\n"
            "const int tb_port = 1883;\n"
            "const char* tb_token = \"YOUR_ACCESS_TOKEN\";\n"
            "WiFiClient wifiClient;\n"
            "PubSubClient mqttClient(wifiClient);\n"
            "\n"
            "void setup() {\n"
            "  Serial.begin(115200);\n"
            "  WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); }\n"
            "  mqttClient.setServer(tb_host, tb_port);\n"
            "  while (!mqttClient.connected()) {\n"
            "    if (mqttClient.connect(\"TOM_Device\", tb_token, NULL)) {\n"
            "      Serial.println(\"ThingsBoard connected\");\n"
            "      mqttClient.subscribe(\"v1/devices/me/rpc/request/+\");\n"
            "    } else delay(5000);\n"
            "  }\n"
            "}\n"
            "\n"
            "void loop() {\n"
            "  mqttClient.loop();\n"
            "  static unsigned long last = 0;\n"
            "  if (millis() - last > 5000) {\n"
            "    last = millis();\n"
            "    mqttClient.publish(\"v1/devices/me/telemetry\",\n"
            "                     \"{\\\"temp\\\":25.3,\\\"hum\\\":60}\");\n"
            "  }\n"
            "}\n")

def _backend_homeassistant(**kw) -> str:
    return ("#include <WiFi.h>\n"
            "#include <PubSubClient.h>\n"
            "const char* ssid = \"WIFI_SSID\";\n"
            "const char* password = \"WIFI_PASS\";\n"
            "const char* mqtt_host = \"homeassistant.local\";\n"
            "const int mqtt_port = 1883;\n"
            "const char* mqtt_user = \"HA_USER\";\n"
            "const char* mqtt_pass = \"HA_PASS\";\n"
            "WiFiClient wifiClient;\n"
            "PubSubClient mqttClient(wifiClient);\n"
            "\n"
            "void setup() {\n"
            "  Serial.begin(115200);\n"
            "  WiFi.begin(ssid, password); while (WiFi.status() != WL_CONNECTED) { delay(500); }\n"
            "  mqttClient.setServer(mqtt_host, mqtt_port);\n"
            "  while (!mqttClient.connected()) {\n"
            "    if (mqttClient.connect(\"TOM_ESP32\", mqtt_user, mqtt_pass)) {\n"
            "      Serial.println(\"HA MQTT connected\");\n"
            "      mqttClient.publish(\"homeassistant/sensor/tom_temp/config\",\n"
            "        \"{\\\"name\\\":\\\"TOM Temp\\\",\\\"stat_t\\\":\\\"tom/data\\\",\\\"val_tpl\\\":\\\"{{value_json.temp}}\\\",\\\"uniq_id\\\":\\\"tom_t\\\"}\", true);\n"
            "      mqttClient.publish(\"homeassistant/sensor/tom_hum/config\",\n"
            "        \"{\\\"name\\\":\\\"TOM Hum\\\",\\\"stat_t\\\":\\\"tom/data\\\",\\\"val_tpl\\\":\\\"{{value_json.hum}}\\\",\\\"uniq_id\\\":\\\"tom_h\\\"}\", true);\n"
            "    } else delay(5000);\n"
            "  }\n"
            "}\n"
            "\n"
            "void loop() {\n"
            "  mqttClient.loop();\n"
            "  static unsigned long last = 0;\n"
            "  if (millis() - last > 10000) {\n"
            "    last = millis();\n"
            "    mqttClient.publish(\"tom/data\", \"{\\\"temp\\\":25.3,\\\"hum\\\":60}\");\n"
            "  }\n"
            "}\n")

def _backend_nodered(**kw) -> str:
    """Generate Node-RED flow JSON."""
    import json
    flow = [
        {"id": "tom_mqtt_in", "type": "mqtt in", "name": "TOM Device Data",
         "topic": "tom/device/data", "broker": "tom_broker", "x": 200, "y": 200, "wires": [["tom_func"]]},
        {"id": "tom_func", "type": "function", "name": "Parse Telemetry",
         'func': 'let d = JSON.parse(msg.payload);\nlet result = [];\nfor (let k in d) {\n  result.push({topic: \\"tom/\\" + k, payload: d[k]});\n}\nreturn [result];',
         "x": 400, "y": 200, "wires": [["tom_debug", "tom_db"]]},
        {"id": "tom_debug", "type": "debug", "name": "Debug", "x": 600, "y": 160},
        {"id": "tom_db", "type": "influxdb", "name": "Save",
         "server": "tom_influx", "x": 600, "y": 240},
        {"id": "tom_broker", "type": "mqtt-broker", "name": "MQTT",
         "broker": "broker.emqx.io", "port": "1883"},
        {"id": "tom_influx", "type": "influxdb", "name": "InfluxDB",
         "host": "localhost", "port": "8086", "db": "tom_iot"}
    ]
    return json.dumps(flow, indent=2)

def _backend_mosquitto(**kw) -> str:
    return ("# Mosquitto MQTT Broker Configuration\n"
            "pid_file /var/run/mosquitto.pid\n"
            "persistence true\n"
            "persistence_location /var/lib/mosquitto/\n"
            "log_dest file /var/log/mosquitto/mosquitto.log\n"
            "log_dest stdout\n"
            "listener 1883\n"
            "protocol mqtt\n"
            "listener 1884\n"
            "protocol websockets\n"
            "listener 8883\n"
            "certfile /etc/mosquitto/certs/server.crt\n"
            "keyfile /etc/mosquitto/certs/server.key\n"
            "tls_version tlsv1.2\n"
            "allow_anonymous false\n"
            "password_file /etc/mosquitto/passwd\n"
            "acl_file /etc/mosquitto/acl\n"
            "max_queued_messages 1000\n"
            "persistent_client_expiration 1h\n")

_BACKEND_GENERATORS = {
    "aws": _backend_aws,
    "aws_iot": _backend_aws,
    "azure": _backend_azure,
    "azure_iot": _backend_azure,
    "thingsboard": _backend_thingsboard,
    "homeassistant": _backend_homeassistant,
    "home_assistant": _backend_homeassistant,
    "nodered": _backend_nodered,
    "node_red": _backend_nodered,
    "mosquitto": _backend_mosquitto,
}

# ===================================================================
# 7. Pinout & Wiring Diagram Generator
# ===================================================================

def _generate_pinout(components: List[str], board: str) -> str:
    b = "ESP32" if board == "esp32" else "ESP8266"
    result = []
    result.append("=" * 70)
    result.append(f"  TOM IoT Engine -- Pinout & Wiring Diagram for {b}")
    result.append("=" * 70)
    result.append("")
    result.append(f"  Board: {b}")
    result.append(f"  Components: {chr(44).join(components)}")
    result.append("")
    result.append("  Power: 3.3V / 5V / GND")
    result.append("")
    level_shift = []
    i2c_devs = []
    spi_devs = []
    result.append("  Wiring Connections:")
    result.append("  " + "-" * 60)

    for comp in components:
        p = _pin(comp, board)
        if comp in ("DHT11", "DHT22", "DHT"):
            result.append(f"  {comp:20s} VCC=3.3V   DATA=GPIO{p:<3d}  GND")
        elif comp in ("HC-SR501", "PIR"):
            level_shift.append(comp)
            result.append(f"  {comp:20s} VCC=5V     OUT=GPIO{p:<3d}  GND  [LEVEL SHIFT]")
        elif comp == "RCWL-0516":
            level_shift.append(comp)
            result.append(f"  {comp:20s} VCC=5V     OUT=GPIO{p:<3d}  GND  [LEVEL SHIFT]")
        elif comp in ("HC-SR04", "Ultrasonic"):
            level_shift.append(comp)
            tp = _pin("HC-SR04_TRIG", board)
            ep = _pin("HC-SR04_ECHO", board)
            result.append(f"  {comp:20s} VCC=5V     TRIG=GPIO{tp:<3d}  ECHO=GPIO{ep:<3d}  GND  [LEVEL SHIFT]")
        elif comp in ("BME280", "BMP180", "BMP280", "SHT30", "BH1750", "TSL2561", "MAX44009", "CCS811", "MPU6050"):
            i2c_devs.append(comp)
            result.append(f"  {comp:20s} VCC=3.3V   SDA=GPIO21  SCL=GPIO22  GND")
        elif comp == "OLED_SSD1306":
            i2c_devs.append(comp)
            result.append(f"  {comp:20s} VCC=3.3V   SDA=GPIO21  SCL=GPIO22  GND")
        elif comp in ("LCD_1602", "LCD_2004"):
            i2c_devs.append(comp)
            result.append(f"  {comp:20s} VCC=5V     SDA=GPIO21  SCL=GPIO22  GND")
        elif comp == "RC522":
            spi_devs.append(comp)
            result.append(f"  {comp:20s} VCC=3.3V   SS=GPIO{p:<3d}  RST=GPIO{_pin(chr(82)+chr(67)+chr(53)+chr(50)+chr(50)+chr(95)+chr(82)+chr(83)+chr(84), board):<3d}  MOSI=GPIO23  MISO=GPIO19  SCK=GPIO18")
        elif comp == "PN532":
            i2c_devs.append(comp)
            result.append(f"  {comp:20s} VCC=3.3V   SDA=GPIO21  SCL=GPIO22  IRQ=GPIO4  RST=GPIO5")
        elif comp in _GPS:
            tx = _pin("NEO6M_TX", board)
            rx = _pin("NEO6M_RX", board)
            result.append(f"  {comp:20s} VCC=3.3V   TX=GPIO{tx:<3d}  RX=GPIO{rx:<3d}  GND")
        elif comp == "Servo_SG90":
            result.append(f"  {comp:20s} VCC=5V     SIG=GPIO{p:<3d}  GND")
        elif comp == "DC_Motor":
            en = _pin("DC_Motor_ENA", board)
            i1 = _pin("DC_Motor_IN1", board)
            i2 = _pin("DC_Motor_IN2", board)
            result.append(f"  {comp:20s} ENA=GPIO{en:<3d}  IN1=GPIO{i1:<3d}  IN2=GPIO{i2:<3d}  EXT-PWR")
        elif comp == "Stepper_28BYJ":
            result.append(f"  {comp:20s} VCC=5V     IN1=GPIO{p:<3d}  IN2=GPIO{p+2:<3d}  IN3=GPIO{p+1:<3d}  IN4=GPIO{p+3:<3d}")
        elif comp == "LED":
            result.append(f"  {comp:20s} ANODE=GPIO{p:<3d}  GND (220R)")
        elif comp == "Relay":
            result.append(f"  {comp:20s} VCC=5V     SIG=GPIO{p:<3d}  GND [EXT POWER]")
        elif comp == "Buzzer":
            result.append(f"  {comp:20s} VCC=3.3V   SIG=GPIO{p:<3d}  GND")
        elif comp == "RGB_LED":
            rp = _pin("RGB_LED_R", board)
            gp = _pin("RGB_LED_G", board)
            bp = _pin("RGB_LED_B", board)
            result.append(f"  {comp:20s} R=GPIO{rp:<3d}  G=GPIO{gp:<3d}  B=GPIO{bp:<3d}  GND")
        elif comp == "DFPlayer_Mini":
            result.append(f"  {comp:20s} VCC=5V     RX=GPIO{_pin(chr(68)+chr(70)+chr(80)+chr(108)+chr(97)+chr(121)+chr(101)+chr(114)+chr(95)+chr(82)+chr(88), board):<3d}  TX=GPIO{_pin(chr(68)+chr(70)+chr(80)+chr(108)+chr(97)+chr(121)+chr(101)+chr(114)+chr(95)+chr(84)+chr(88), board):<3d}  SPK")
        elif comp == "FlowSensor":
            result.append(f"  {comp:20s} VCC=5V     SIG=GPIO{p:<3d}  GND")
        elif comp == "ESP32-CAM":
            result.append(f"  {comp:20s} VCC=5V     UART-TX=GPIO1  UART-RX=GPIO3")
        elif comp == "PMS5003":
            result.append(f"  {comp:20s} VCC=5V     TX=GPIO16  RX=GPIO17  GND")
        elif comp in ("MAX9814",):
            result.append(f"  {comp:20s} VCC=3.3V   OUT=GPIO{p:<3d}  GAIN=SET  GND")
        elif comp == "I2S_MEMS":
            result.append(f"  {comp:20s} VCC=3.3V   SCK=GPIO2  WS=GPIO15  SD=GPIO13")
        elif comp == "DS18B20":
            result.append(f"  {comp:20s} VCC=3.3V   DQ=GPIO{p:<3d}  GND (4.7K PU)")
        elif comp in ("LM35", "LDR", "SoilMoisture", "Soil_pH", "WaterLevel", "RainSensor", "TDS_Sensor"):
            result.append(f"  {comp:20s} VCC=3.3V   SIG=GPIO{p:<3d}  GND")
        elif comp.startswith("MQ-"):
            result.append(f"  {comp:20s} VCC=5V(H)  AOUT=GPIO{p:<3d}  GND")

    result.append("")
    result.append("  " + "-" * 60)
    if level_shift:
        result.append("")
        result.append("  ! IMPORTANT: Level Shifting Required !")
        for c in level_shift:
            result.append(f"    - {c} outputs 5V logic, needs 5V->3.3V converter")
    if i2c_devs:
        result.append("")
        result.append("  I2C Bus: SDA=GPIO21, SCL=GPIO22")
        addr_map = {"BME280":"0x76","BMP280":"0x76","BMP180":"0x77","SHT30":"0x44",
                     "BH1750":"0x23","TSL2561":"0x39","MAX44009":"0x4A",
                     "MPU6050":"0x68","CCS811":"0x5A","OLED_SSD1306":"0x3C",
                     "LCD_1602":"0x27","LCD_2004":"0x27","PN532":"0x48"}
        for d in i2c_devs:
            addr = addr_map.get(d, "0x??")
            result.append(f"    - {d:20s} at {addr}")
    if spi_devs:
        result.append("")
        result.append("  SPI: MOSI=GPIO23, MISO=GPIO19, SCK=GPIO18")
    result.append("")
    result.append("=" * 70)
    return "\n".join(result)


# ===================================================================
# 8. IoT System Architecture Generator
# ===================================================================

_ARCHITECTURES = {
    "smart_home": {
        "description": 'Smart Home monitoring and control system',
        "sensors": ['DHT22', 'PIR', 'LDR', 'BH1750', 'MQ-135'],
        "actuators": ['Relay', 'LED', 'Buzzer', 'Servo_SG90'],
        "protocol": 'MQTT',
        "backend": 'Home Assistant',
        "features": ['Temperature/humidity monitoring', 'Motion detection', 'Light level sensing', 'Air quality monitoring', 'Smart light control', 'Alarm system', 'Voice assistant integration'],
        "diagram": '  [DHT22] -- GPIO4 ---+\\n  [PIR]   -- GPIO5 ---+--- [ESP32] ---- MQTT ---- [Home Assistant] ---- [Dashboard]\\n  [LDR]   -- GPIO34--+        |\\n  [BH1750]- I2C -----+      [Relay]--GPIO23--[Light]\\n  [MQ-135]- GPIO35 --+     [Servo]--GPIO13--[Blinds]\\n                       [Buzzer]--GPIO15--[Alarm]',
    },
    "weather_station": {
        "description": 'Weather station with multiple sensors and cloud upload',
        "sensors": ['BME280', 'BH1750', 'RainSensor', 'DS18B20'],
        "actuators": [],
        "protocol": 'MQTT',
        "backend": 'ThingsBoard',
        "features": ['Temperature, humidity, pressure', 'Rainfall measurement', 'Light intensity (lux)', 'Cloud dashboard with charts', 'Historical data storage', 'Solar powered option'],
        "diagram": '  [BME280]  -- I2C -----+\\n  [BH1750]  -- I2C -----+--- [ESP32] ---- MQTT ---- [ThingsBoard] ---- [Dashboard]\\n  [Rain]    -- GPIO34 --+        |\\n  [DS18B20] -- GPIO4 ---+    [OLED Display] -- I2C\\n                          [SD Card Logging]',
    },
    "smart_agriculture": {
        "description": 'Smart agriculture for soil monitoring and irrigation',
        "sensors": ['SoilMoisture', 'Soil_pH', 'DHT22', 'BH1750', 'RainSensor'],
        "actuators": ['Relay', 'DC_Motor'],
        "protocol": 'LoRaWAN/MQTT',
        "backend": 'AWS IoT',
        "features": ['Soil moisture monitoring', 'Soil pH level', 'Automatic irrigation control', 'Rain detection', 'Solar-powered', 'Long-range LoRaWAN'],
        "diagram": '  [SoilMoisture] -- GPIO34 -+\\n  [Soil pH]      -- GPIO35 -+--- [ESP32] ---- LoRaWAN ---- [Gateway] ---- [Cloud]\\n  [DHT22]        -- GPIO4  -+       |\\n  [Rain]         -- GPIO32 -+   [Relay]--GPIO23--[Water Pump]\\n  [BH1750]       -- I2C  --+   [Motor]--GPIO26/27--[Valve]',
    },
    "industrial_iot": {
        "description": 'Industrial machine monitoring and predictive maintenance',
        "sensors": ['MPU6050', 'DS18B20', 'PMS5003', 'CCS811', 'BME280'],
        "actuators": [],
        "protocol": 'MQTT',
        "backend": 'AWS IoT',
        "features": ['Vibration analysis (FFT)', 'Temperature monitoring', 'Air quality monitoring', 'Predictive maintenance alerts', 'Real-time machine status', 'Edge ML inference'],
        "diagram": '  [MPU6050] -- I2C ------+\\n  [DS18B20] -- GPIO4 ----+--- [ESP32] ---- MQTT/TLS ---- [AWS IoT] ---- [Grafana]\\n  [PMS5003] -- UART ----+        |\\n  [CCS811]  -- I2C ------+   [OLED Display]\\n  [BME280]  -- I2C ------+',
    },
    "wearable": {
        "description": 'Wearable health monitoring device',
        "sensors": ['MPU6050', 'MAX9814', 'LM35'],
        "actuators": [],
        "protocol": 'BLE',
        "backend": 'N/A',
        "features": ['Step counting', 'Fall detection', 'Body temperature', 'Activity recognition', 'BLE upload to phone', 'Low power design'],
        "diagram": '  [MPU6050] -- I2C ------+\\n  [LM35]    -- GPIO34 ---+--- [ESP32] ---- BLE ---- [Smartphone]\\n  [MAX9814] -- GPIO35 --+        |\\n                              [Vibration Motor] -- GPIO18',
    },
    "smart_parking": {
        "description": 'Smart parking with ultrasonic sensors',
        "sensors": ['HC-SR04'],
        "actuators": [],
        "protocol": 'LoRaWAN',
        "backend": 'Cloud Dashboard',
        "features": ['Ultrasonic distance measurement', 'Occupancy detection', 'LoRaWAN long-range', 'Battery-powered (3+ years)', 'Cloud dashboard with map'],
        "diagram": '  [HC-SR04] -- TRIG=GPIO16 -+\\n               ECHO=GPIO17 -+--- [ESP32] ---- LoRaWAN ---- [Gateway] ---- [Dashboard]\\n                              |\\n                          [Battery]',
    },
    "asset_tracking": {
        "description": 'GPS-based asset tracking system',
        "sensors": ['NEO-6M'],
        "actuators": [],
        "protocol": 'LoRaWAN/MQTT',
        "backend": 'Cloud',
        "features": ['GPS location tracking', 'Real-time position', 'Geofencing alerts', 'Low power deep sleep', 'Historical route replay'],
        "diagram": '  [GPS NEO-6M] -- UART ---+\\n                           +--- [ESP32] ---- LoRaWAN ---- [Cloud] ---- [Dashboard]\\n  [Battery]    -- ADC ----+        |\\n                                [Deep Sleep]',
    },
    "smart_energy": {
        "description": 'Smart energy/power monitoring system',
        "sensors": ['DS18B20', 'BME280', 'FlowSensor'],
        "actuators": ['Relay'],
        "protocol": 'MQTT',
        "backend": 'ThingsBoard',
        "features": ['Power consumption monitoring', 'Solar panel tracking', 'Battery management', 'Energy usage analytics', 'Load control via relays'],
        "diagram": '  [DS18B20]   -- GPIO4 ---+\\n  [BME280]    -- I2C ------+--- [ESP32] ---- MQTT ---- [ThingsBoard]\\n  [Flow]      -- GPIO34 --+      |\\n                           [Relay]--GPIO23--[Load Control]',
    },
}


# ===================================================================
# 9. Configuration Generators
# ===================================================================

def _config_wifimanager(**kw) -> str:
    return json.dumps({
        "wifis": [{"ssid": "HomeWiFi", "password": "home1234", "priority": 1},
                  {"ssid": "OfficeWiFi", "password": "office5678", "priority": 2}],
        "ap": {"ssid": "TOM_Device_AP", "password": "tomconfig",
               "channel": 6, "hidden": False, "max_connections": 4},
        "timeout": 180,
        "portal": {"title": "TOM IoT Config",
                   "fields": [
                       {"name": "MQTT_HOST", "label": "MQTT Broker", "default": "broker.emqx.io"},
                       {"name": "MQTT_PORT", "label": "MQTT Port", "default": "1883", "type": "number"},
                       {"name": "MQTT_USER", "label": "MQTT Username", "default": ""},
                       {"name": "DEVICE_NAME", "label": "Device Name", "default": "TOM_Sensor"}
                   ]}
    }, indent=2)

def _config_mosquitto(**kw) -> str:
    return _backend_mosquitto(**kw)

def _config_aws_policy(**kw) -> str:
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["iot:Connect"],
             "Resource": ["arn:aws:iot:us-east-1:ACCOUNT_ID:client/TOM_Device"]},
            {"Effect": "Allow", "Action": ["iot:Publish"],
             "Resource": [
                 "arn:aws:iot:us-east-1:ACCOUNT_ID:topic/$aws/things/TOM_Device/shadow/update",
                 "arn:aws:iot:us-east-1:ACCOUNT_ID:topic/tom/device/*"]},
            {"Effect": "Allow", "Action": ["iot:Subscribe"],
             "Resource": [
                 "arn:aws:iot:us-east-1:ACCOUNT_ID:topicfilter/$aws/things/TOM_Device/shadow/update/accepted",
                 "arn:aws:iot:us-east-1:ACCOUNT_ID:topicfilter/tom/device/cmd/#"]},
            {"Effect": "Allow", "Action": ["iot:Receive"],
             "Resource": [
                 "arn:aws:iot:us-east-1:ACCOUNT_ID:topic/$aws/things/TOM_Device/shadow/update/accepted",
                 "arn:aws:iot:us-east-1:ACCOUNT_ID:topic/tom/device/cmd/#"]}
        ]
    }, indent=2)

def _config_azure_twin(**kw) -> str:
    return json.dumps({
        "deviceId": "TOM_Device",
        "properties": {
            "desired": {
                "telemetryInterval": 30,
                "sensorConfig": {
                    "temperature": {"enabled": True, "pin": 4},
                    "humidity": {"enabled": True, "pin": 4}
                },
                "reporting": {
                    "mqttBroker": "broker.emqx.io",
                    "uploadInterval": 60
                }
            },
            "reported": {
                "firmware": "TOM_IoT_v1.0",
                "status": "online",
                "rssi": -65
            }
        },
        "tags": {
            "location": "living_room",
            "type": "environmental_sensor"
        }
    }, indent=2)

_CONFIG_GENERATORS = {
    "wifimanager": _config_wifimanager,
    "mosquitto": _config_mosquitto,
    "aws_policy": _config_aws_policy,
    "azure_twin": _config_azure_twin,
}


# ===================================================================
# THE MAIN IoTEngine CLASS
# ===================================================================

class IoTEngine:
    """Universal IoT Engine -- device code generation, firmware, protocols, backend."""

    def __init__(self):
        self._name = "TOM IoT Engine v1.0"
        self._supported_boards = ["esp32", "esp8266"]
        self._supported_components = sorted(_ALL_COMPONENTS)
        self._supported_protocols = sorted(_PROTOCOL_GENERATORS.keys())
        self._supported_backends = sorted(_BACKEND_GENERATORS.keys())
        self._supported_sensors = sorted(_SENSOR_GENERATORS.keys())
        self._supported_architectures = sorted(_ARCHITECTURES.keys())

    def generate_esp_code(self, board_type="esp32", components=None,
                          wifi_config=None, mqtt_config=None, **kwargs):
        """Generate complete Arduino .ino firmware for ESP32/ESP8266."""
        if board_type not in ("esp32", "esp8266"):
            return _err(f"Unsupported board: {board_type}")
        if not components:
            return _err("No components specified.")
        components = [c.strip() for c in components]
        # Case-insensitive matching
        comp_upper = {c.upper(): c for c in _ALL_COMPONENTS}
        matched = []
        unknown = []
        for c in components:
            cu = c.upper()
            if cu in comp_upper:
                matched.append(comp_upper[cu])
            else:
                unknown.append(c)
        if unknown:
            return _err(f"Unknown components: {unknown}")
        components = matched
        user_pins = kwargs.get("pins", {})
        deep_sleep = kwargs.get("deep_sleep", False)
        protocols = kwargs.get("protocols", ["mqtt"])
        try:
            result = _esp_code(board_type, components, wifi_config or {},
                               mqtt_config or {}, user_pins, deep_sleep, protocols)
            return _ok(result=result, message=f"{board_type.upper()} firmware ({len(result)} chars)")
        except Exception as e:
            return _err(f"Generation failed: {e}")

    def generate_micropython(self, board_type="esp32", components=None,
                             wifi_config=None, mqtt_config=None, **kwargs):
        """Generate MicroPython firmware for ESP32/ESP8266."""
        if board_type not in ("esp32", "esp8266"):
            return _err(f"Unsupported board: {board_type}")
        if not components:
            return _err("No components")
        components = [c.strip() for c in components]
        comp_upper = {c.upper(): c for c in _ALL_COMPONENTS}
        matched = []
        unknown = []
        for c in components:
            cu = c.upper()
            if cu in comp_upper:
                matched.append(comp_upper[cu])
            else:
                unknown.append(c)
        if unknown:
            return _err(f"Unknown: {unknown}")
        components = matched
        try:
            result = _micropython_code(board_type, components, wifi_config or {},
                                        mqtt_config or {},
                                        kwargs.get("pins", {}),
                                        kwargs.get("deep_sleep", False))
            return _ok(result=result, message=f"MicroPython ({len(result)} chars)")
        except Exception as e:
            return _err(f"Failed: {e}")

    def generate_protocol_code(self, protocol="mqtt", device_role="client", **kwargs):
        """Generate protocol code (MQTT, HTTP, WebSocket, CoAP, BLE, etc)."""
        proto = protocol.lower().strip()
        if proto not in _PROTOCOL_GENERATORS:
            return _err(f"Unsupported protocol. Use: {sorted(_PROTOCOL_GENERATORS.keys())}")
        try:
            result = _PROTOCOL_GENERATORS[proto](role=device_role, **kwargs)
            return _ok(result=result, message=f"{protocol.upper()} {device_role} ({len(result)} chars)")
        except Exception as e:
            return _err(f"Failed: {e}")

    def generate_sensor_code(self, sensor_type="DHT22", protocol="serial", **kwargs):
        """Generate standalone sensor code."""
        st = sensor_type.strip()
        if st not in _SENSOR_GENERATORS:
            return _err(f"Unsupported sensor. Use: {sorted(_SENSOR_GENERATORS.keys())}")
        try:
            kwargs.pop("sensor", None)
            kwargs.pop("board_type", None)
            result = _SENSOR_GENERATORS[st](sensor=st, board=kwargs.get("board", "esp32"), **kwargs)
            return _ok(result=result, message=f"{st} code ({len(result)} chars)")
        except Exception as e:
            return _err(f"Failed: {e}")

    def generate_backend_code(self, backend_type="aws", protocol="mqtt", **kwargs):
        """Generate backend integration code."""
        bt = backend_type.lower().strip().replace(" ", "_").replace("-", "_")
        if bt not in _BACKEND_GENERATORS:
            return _err(f"Unsupported. Use: {sorted(_BACKEND_GENERATORS.keys())}")
        try:
            result = _BACKEND_GENERATORS[bt](**kwargs)
            if bt in ("nodered", "node_red") and isinstance(result, str):
                try:
                    json.loads(result)
                except Exception:
                    pass
            return _ok(result=result, message=f"{backend_type} ({len(result)} chars)")
        except Exception as e:
            return _err(f"Failed: {e}")

    def generate_pinout(self, components, board_type="esp32"):
        """Generate ASCII-art wiring diagram."""
        if board_type not in ("esp32", "esp8266"):
            return _err("Unsupported board")
        if not components:
            return _err("No components")
        try:
            result = _generate_pinout(components, board_type)
            return _ok(result=result, message="Pinout generated")
        except Exception as e:
            return _err(f"Failed: {e}")

    def generate_architecture(self, use_case="smart_home", components=None, **kwargs):
        """Generate system architecture."""
        uc = use_case.lower().strip().replace(" ", "_").replace("-", "_")
        if uc not in _ARCHITECTURES:
            return _err(f"Unsupported. Use: {sorted(_ARCHITECTURES.keys())}")
        try:
            arch = _ARCHITECTURES[uc]
            a = []
            a.append("=" * 70)
            a.append(f"  TOM IoT -- Architecture: {use_case.replace(chr(95), chr(32)).title()}")
            a.append("=" * 70)
            a.append("")
            a.append(f"  Description: {arch[chr(100)+chr(101)+chr(115)+chr(99)+chr(114)+chr(105)+chr(112)+chr(116)+chr(105)+chr(111)+chr(110)]}")
            a.append("")
            a.append("  Sensors/Components:")
            for s in arch.get("sensors", []):
                a.append(f"    - {s}")
            for act in arch.get("actuators", []):
                a.append(f"    - {act} (actuator)")
            a.append("")
            a.append(f"  Protocol: {arch.get(chr(112)+chr(114)+chr(111)+chr(116)+chr(111)+chr(99)+chr(111)+chr(108), chr(78)+chr(47)+chr(65))}")
            a.append(f"  Backend: {arch.get(chr(98)+chr(97)+chr(99)+chr(107)+chr(101)+chr(110)+chr(100), chr(78)+chr(47)+chr(65))}")
            a.append("")
            a.append("  Key Features:")
            for f in arch.get("features", []):
                a.append(f"    * {f}")
            a.append("")
            a.append("  System Diagram:")
            a.append(arch.get("diagram", ""))
            a.append("")
            a.append("  Power: USB 5V or Battery 3.7V LiPo")
            a.append("")
            a.append("=" * 70)
            result = "\n".join(a)
            return _ok(result=result, message=f"Architecture for {use_case}")
        except Exception as e:
            return _err(f"Failed: {e}")

    def generate_config(self, device_type="wifimanager", **kwargs):
        """Generate device configuration."""
        dt = device_type.lower().strip().replace(" ", "_").replace("-", "_")
        if dt not in _CONFIG_GENERATORS:
            return _err(f"Unsupported. Use: {sorted(_CONFIG_GENERATORS.keys())}")
        try:
            result = _CONFIG_GENERATORS[dt](**kwargs)
            return _ok(result=result, message=f"{device_type} config ({len(result)} chars)")
        except Exception as e:
            return _err(f"Failed: {e}")

    def get_supported(self):
        """Return all supported items."""
        return _ok(result={
            "boards": self._supported_boards,
            "components": self._supported_components,
            "protocols": self._supported_protocols,
            "backends": self._supported_backends,
            "sensors": self._supported_sensors,
            "architectures": self._supported_architectures,
        })

    def get_info(self):
        """Return engine info."""
        return _ok(result={
            "name": self._name,
            "version": "1.0",
            "description": "Universal IoT Engine for TOM"
        })


# ===================================================================
# Demo / Test
# ===================================================================
if __name__ == "__main__":
    engine = IoTEngine()
    r = engine.generate_esp_code(
        board_type="esp32",
        components=["DHT22", "PIR", "BME280", "LED"],
        wifi_config={"ssid": "MyWiFi", "password": "MyPass"},
        mqtt_config={"broker": "broker.emqx.io", "topic_prefix": "tom/demo"}
    )
    if r["status"] == "success":
        print("=== ESP32 FIRMWARE ===")
        print(r["result"][:2000])
        print(f"... ({len(r[chr(114)+chr(101)+chr(115)+chr(117)+chr(108)+chr(116)])} chars)")
    else:
        print("ERROR:", r["message"])