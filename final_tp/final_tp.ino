#include <WiFi.h>
#include <PubSubClient.h>
#include <ESPAsyncWebServer.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include "SPIFFS.h" 
#include <HTTPClient.h>
#include "wifi_utils.h"
#include "OneWire.h"
#include "DallasTemperature.h"
#include <math.h>

// Pin definitions
const int LEDSTRIP_PIN = 13;
const int TEMPERATURE_PIN = 23;
const int LIGHTSENSOR_PIN = A5;
const int ONBOARD_LED = 2; // Internal LED for hotspot indication
const int NUMLEDS = 5;

// MQTT details
const char* mqtt_server = "test.mosquitto.org";
const char* topic_piscine = "uca/iot/piscine";

// Initialize Objects
OneWire oneWire(TEMPERATURE_PIN);
DallasTemperature tempSensor(&oneWire);
Adafruit_NeoPixel strip(NUMLEDS, LEDSTRIP_PIN, NEO_GRB + NEO_KHZ800);
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Constants
const float fireSuspectTemperature = 50.0;
const int fireThresholdLight = 300;
const int brightLightThreshold = 1000;
const float OCCUPIED_LIGHT_THRESHOLD = 150;
const float LOCAL_LAT = 43.7;  // Example latitude
const float LOCAL_LON = 7.25; // Example longitude

// Global variables
bool isOccupied = false;
bool hotspotActive = false;
float localTemperature = 0.0;
float maxTemperature = -1000.0;

struct Pool {
  String id;
  float lat;
  float lon;
  float temperature;
};

Pool pools[30]; // Array to store data for up to 30 pools
int poolCount = 0; // Count of pools currently stored


void setup() {
  Serial.begin(115200);

  // Initialize SPIFFS
  if (!SPIFFS.begin(true)) {
    Serial.println("Failed to mount SPIFFS");
    return;
  }

  // Initialize sensors
  tempSensor.begin();
  strip.begin();
  strip.show();

  // Configure onboard LED
  pinMode(ONBOARD_LED, OUTPUT);

  // Connect to Wi-Fi
  wifi_connect_multi("ESP32");
  wifi_printstatus(0);

  // Set MQTT server and callback
  mqttClient.setServer(mqtt_server, 1883);
  mqttClient.setCallback(mqttCallback);
}

unsigned long lastPublishTime = 0;
const unsigned long publishInterval = 5000;

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

   // Non-blocking delay using millis()
  if (millis() - lastPublishTime > publishInterval) {
    lastPublishTime = millis();
    publishStatus();
  }

    // Read sensors
  localTemperature = readTemperature();
  int lightIntensity = readLightIntensity();
  isOccupied = checkOccupancy(lightIntensity);

  // Check for fire
  if (checkForFire(localTemperature, lightIntensity)) {
    Serial.println("Fire detected!");
    handleFire();
  }

  // Update hotspot status
  updateHotspotStatus();
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    String clientId = "ESP32Client_" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("MQTT connected");
      mqttClient.subscribe(topic_piscine); // Subscribe to the topic
      Serial.println("Subscribed to topic: " + String(topic_piscine));
    } else {
      Serial.print("MQTT connection failed, rc=");
      Serial.println(mqttClient.state());
      delay(2000); // Wait 2 seconds before retrying
    }
  }
}

float readTemperature() {
  tempSensor.requestTemperatures();
  float tempC = tempSensor.getTempCByIndex(0);
  return tempC == DEVICE_DISCONNECTED_C ? NAN : tempC;
}

int readLightIntensity() {
  return 4096 - analogRead(LIGHTSENSOR_PIN);
}

bool checkForFire(float temp, int light) {
  return (temp > fireSuspectTemperature) &&
         (light < fireThresholdLight || light > brightLightThreshold);
}

void handleFire() {
  digitalWrite(ONBOARD_LED, HIGH);
  delay(1000);
  digitalWrite(ONBOARD_LED, LOW);
}

bool checkOccupancy(int lightIntensity) {
  return lightIntensity < OCCUPIED_LIGHT_THRESHOLD;
}

void updateHotspotStatus() {
   hotspotActive = is_hotspot(localTemperature, LOCAL_LAT, LOCAL_LON, "P_22411341");
   digitalWrite(ONBOARD_LED, hotspotActive ? HIGH : LOW);
}

void publishStatus() {
  StaticJsonDocument<1024> doc;
  doc["info"]["ident"] = "P_22411341";
  doc["info"]["user"] = "ESP Nourrr";
  doc["status"]["temperature"] = localTemperature;
  doc["status"]["light_intensity"] = readLightIntensity();
  doc["status"]["fire_detected"] = checkForFire(localTemperature, readLightIntensity());
  doc["piscine"]["hotspot"] = hotspotActive;
  doc["piscine"]["occuped"] = isOccupied;
  doc["location"]["gps"]["lat"] = LOCAL_LAT;
  doc["location"]["gps"]["lon"]= LOCAL_LON;

  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);

   bool success = mqttClient.publish(topic_piscine, jsonBuffer);
  if (success) {
    Serial.println("Published successfully:");
  } else {
    Serial.println("Publish failed:");
  }
  Serial.println("Topic: " + String(topic_piscine));
  Serial.println("Payload: " + String(jsonBuffer));
}

float haversine(float lat1, float lon1, float lat2, float lon2) {
  const float R = 6371.0; // Earth's radius in kilometers
  float dLat = radians(lat2 - lat1);
  float dLon = radians(lon2 - lon1);
  float a = sin(dLat / 2) * sin(dLat / 2) +
            cos(radians(lat1)) * cos(radians(lat2)) *
            sin(dLon / 2) * sin(dLon / 2);
  float c = 2 * atan2(sqrt(a), sqrt(1 - a));
  return R * c; // Distance in kilometers
}

bool is_hotspot(float current_temp, float current_lat, float current_lon, String pool_id) {
  bool isHotspot = true;

  // Iterate over received pool data
  for (int i = 0; i < poolCount; i++) {
    Pool otherPool = pools[i];
    if (otherPool.id == pool_id) continue; // Skip self-comparison

    float distance = haversine(current_lat, current_lon, otherPool.lat, otherPool.lon);
    if (distance <= 10.0 && otherPool.temperature > current_temp) {
      isHotspot = false;
      break;
    }
  }

  return isHotspot;
}

String lastLedColor = "";

// Function to set the LED strip color
void setLedColor(int red, int green, int blue, String colorName) {
  if (lastLedColor != colorName) {
    lastLedColor = colorName;
    for (int i = 0; i < NUMLEDS; i++) {
      strip.setPixelColor(i, strip.Color(red, green, blue));
    }
    strip.show();
    Serial.println("LED color changed to: " + colorName);
  } else {
    Serial.println("LED color is already " + colorName + ", no update needed.");
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.println("MQTT message received:");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]); // Print raw payload
  }
  Serial.println();
  Serial.flush(); //Ensure all output is printed before continuing

  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  if (!error) {
    String poolId = doc["pool_id"] | "null"; // Use default value if not found
    String ledColor = doc["led_color"] | "null";

     // Extract pool information
    String id = doc["info"]["ident"] | "unknown";
    float lat = doc["location"]["gps"]["lat"] | 0.0;
    float lon = doc["location"]["gps"]["lon"] | 0.0;
    float temperature = doc["status"]["temperature"] | NAN;

      // Check if pool already exists in the array
    bool poolExists = false;
    for (int i = 0; i < poolCount; i++) {
      if (pools[i].id.equals(id)) { //using equals() for string comparison
        pools[i].lat = lat;
        pools[i].lon = lon;
        pools[i].temperature = temperature;
        poolExists = true;
        break;
      }
    }

    // If pool doesn't exist, add it to the array
    if (!poolExists && poolCount < 30) {
      pools[poolCount].id = id;
      pools[poolCount].lat = lat;
      pools[poolCount].lon = lon;
      pools[poolCount].temperature = temperature;
      poolCount++;
    }

    // Debug: Print all pools
    Serial.println("Current pools:");
    for (int i = 0; i < poolCount; i++) {
      Serial.print("Pool ID: ");
      Serial.print(pools[i].id);
      Serial.print(", Lat: ");
      Serial.print(pools[i].lat);
      Serial.print(", Lon: ");
      Serial.print(pools[i].lon);
      Serial.print(", Temp: ");
      Serial.println(pools[i].temperature);
    }
  
    // Update maxTemperature for hotspot detection
    maxTemperature = -1000.0;
    for (int i = 0; i < poolCount; i++) {
      if (pools[i].temperature > maxTemperature) {
        maxTemperature = pools[i].temperature;
      }
    }

    // Re-evaluate hotspot status
    hotspotActive = is_hotspot(localTemperature, LOCAL_LAT, LOCAL_LON, "P_22411341");
    digitalWrite(ONBOARD_LED, hotspotActive ? HIGH : LOW);

    Serial.println("Parsed values:");
    Serial.println("Pool ID: " + poolId);
    Serial.println("LED Color: " + ledColor);

    // Update LED strip color based on the received command
    if (ledColor == "green" && lastLedColor != "green") {
      setLedColor(0, 255, 0, "green");
    } else if (ledColor == "yellow" && lastLedColor != "yellow") {
      setLedColor(255, 255, 0, "yellow");
    } else if (ledColor == "red" && lastLedColor != "red") {
      setLedColor(255, 0, 0, "red");
    } else {
      Serial.println("Unknown LED color command.");
    }
  } else {
    Serial.println("Error parsing MQTT message:");
    Serial.println(error.c_str());
  }
  delay(100); //small delay to allow processing
}
