#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <WebServer.h>  // Ensure WebServer.h is included if using WebServer class

const char* ssid_ap = "ESP32_Hotspot";  // The SSID for the ESP32 hotspot
const char* password_ap = "12345678";   // The password for the ESP32 hotspot

int lightsForLessThanThreshold = 1; 
int countThreshold = 8; 

const int relayPins[] = {22, 23};  // Adjust these pins based on your wiring
const int initialTotalLights = sizeof(relayPins) / sizeof(relayPins[0]);  // The actual total number of lights
int lightStates[initialTotalLights] = {0};  // 0: off, 1: on
int availableLights = initialTotalLights;  // Track available lights to switch

WebServer server(80);  // Initialize the WebServer instance

// Function to switch lights on or off with a new condition for count < threshold
void switchLight(int numLightsToSwitchOn, bool turnOn, bool isThresholdCheck) {
  if (turnOn) {
    int switchedOn = 0;  // Track how many lights were turned on
    bool anyLightsOn = false;

    // Check if any lights are already on
    for (int i = 0; i < initialTotalLights; i++) {
      if (lightStates[i] == 1) {
        anyLightsOn = true;
        break;  // Exit the loop if any light is already on
      }
    }

    // If we are in threshold check and any lights are already on, do nothing
    if (isThresholdCheck && anyLightsOn) {
      Serial.println("One or more lights are already on, no additional lights will be switched on.");
      return;
    }

    for (int i = (initialTotalLights-availableLights); i < initialTotalLights; i++) {
      if (lightStates[i] == 0 && switchedOn < numLightsToSwitchOn) {  // Only switch on lights that are off
        digitalWrite(relayPins[i], LOW);  // Assuming LOW turns on the relay/light
        lightStates[i] = 1;  // Mark the light as on
        switchedOn++;
        Serial.print("Turning on light ");
        Serial.println(relayPins[i]);
      }
    }
    availableLights -= switchedOn;  // Update available lights
  } else {
    Serial.println("Switching off all lights.");
    int switchedOff = 0;
    for (int i = availableLights; i < initialTotalLights; i++) {
      if (lightStates[i] == 1 && switchedOff < numLightsToSwitchOn) {  // Only switch off lights that are on
        digitalWrite(relayPins[i], HIGH);  // Assuming HIGH turns off the relay/light
        lightStates[i] = 0;  // Mark the light as off
        switchedOff++;
        Serial.print("Turning off light ");
        Serial.println(relayPins[i]);
      }
    }
    availableLights += switchedOff;  // Update available lights
  }
}

// Handle turning lights on with added threshold check logic
void handleSwitchLightsOn() {
  Serial.println(availableLights);
  if (availableLights == 0) {
    server.send(200, "text/plain", "All lights are already on.");
    return;
  }

  if (server.hasArg("count")) {
    int count = server.arg("count").toInt();
    int numLightsToSwitchOn = (count < countThreshold) ? lightsForLessThanThreshold : availableLights;

    if (count >= 0) {
      bool isThresholdCheck = (count < countThreshold);  // Flag for threshold check
      switchLight(numLightsToSwitchOn, true, isThresholdCheck);  // Pass the threshold flag to switchLight
      server.send(200, "text/plain", "Lights turned on based on count.");
    } else {
      server.send(400, "text/plain", "Invalid count.");
    }
  } else {
    server.send(400, "text/plain", "Count required.");
  }
}

void handleSwitchLightsOff() {
  Serial.println(availableLights);

  // Check if all lights are already off
  if (availableLights == initialTotalLights) {
    server.send(200, "text/plain", "All lights are already off.");
    return;
  }

  if (server.hasArg("count")) {
    int count = server.arg("count").toInt();
    
    // Determine the number of lights to switch off
    int numLightsToSwitchOff = (count < countThreshold) ? lightsForLessThanThreshold : initialTotalLights - availableLights;

    // If count is zero, switch off all currently on lights
    if (count == 0) {
      switchLight(initialTotalLights - availableLights, false, false);  // Turn off all lights that are currently on
      server.send(200, "text/plain", "All lights turned off.");
    } 
    // If count is greater than zero
    else if (count > 0) {
      // Check if one light is already off before proceeding
      bool anyLightOff = false;
      for (int i = 0; i < initialTotalLights; i++) {
        if (lightStates[i] == 0) {  // If light is off
          anyLightOff = true;
          break;
        }
      }

      // If at least one light is off, prevent turning off more lights
      if (anyLightOff) {
        server.send(200, "text/plain", "At least one light is off, no additional lights will be switched off.");
        return;
      } else {
        switchLight(numLightsToSwitchOff, false, false);  // Turn off lights based on count
        server.send(200, "text/plain", "Lights turned off based on count.");
      }
    }
  } else {
    server.send(400, "text/plain", "Count required.");
  }
}

void handletoggle() {
  Serial.println("Entered");  // Debug line 
  if (server.hasArg("togl")) {
    Serial.println("Received togl argument");  // Debug line 
    bool toggle = server.arg("togl") == "1";
    Serial.println(toggle);
    Serial.println(availableLights);

    if (toggle) {  // If toggle is true (turn lights on)
      if (availableLights == 0) {
        server.send(200, "text/plain", "All lights are already on.");
        return;
      }
      server.send(200, "text/plain", "Turning ON available lights.");
      Serial.print("Switching on ");
      Serial.print(availableLights);
      Serial.println(" lights.");

      int switchedOn = 0;  // Track how many lights have been switched on
      for (int i = 0; i < initialTotalLights; i++) {
        if (lightStates[i] == 0 && switchedOn < availableLights) {  // Only turn on lights that are off
          digitalWrite(relayPins[i], LOW);  // Assuming LOW turns on the relay/light
          lightStates[i] = 1;  // Mark the light as on
          switchedOn++;
          Serial.print("Turning on light ");
          Serial.println(relayPins[i]);
          delay(2000);
        }
      }
      availableLights -= switchedOn;  // Update the number of available lights
    } else {  // If toggle is false (turn lights off)
      if (availableLights == initialTotalLights) {
        server.send(200, "text/plain", "No need to turn off the lights.");
        return;
      }

      server.send(200, "text/plain", "Turning OFF all lights.");
      Serial.println("Switching off all lights.");

      int switchedOff = 0;  // Track how many lights have been switched off
      for (int i = 0; i < initialTotalLights; i++) {
        if (lightStates[i] == 1) {  // Only turn off lights that are on
          digitalWrite(relayPins[i], HIGH);  // Assuming HIGH turns off the relay/light
          lightStates[i] = 0;  // Mark the light as off
          switchedOff++;
          Serial.print("Turning off light ");
          Serial.println(relayPins[i]);
          delay(2000);
        }
      }
      availableLights += switchedOff;  // Update the number of available lights
    }
  } else {
    server.send(400, "text/plain", "toggle required.");
  }
}

// Endpoint to set the configuration for lights and count threshold
void handleSetLightConfig() {
  if (server.hasArg("lightsLessThanThreshold") && server.hasArg("countThreshold")) {
    int newLightsForLessThanThreshold = server.arg("lightsLessThanThreshold").toInt();
    int newCountThreshold = server.arg("countThreshold").toInt();

    if (newLightsForLessThanThreshold >= 0 && newLightsForLessThanThreshold <= initialTotalLights &&newCountThreshold > 0) {
      lightsForLessThanThreshold = newLightsForLessThanThreshold;
      countThreshold = newCountThreshold;
      Serial.println(lightsForLessThanThreshold);
      Serial.println(countThreshold);
      server.send(200, "text/plain", "Configuration updated successfully.");
    } else {
      server.send(400, "text/plain", "Invalid configuration values.");
    }
  } else {
    server.send(400, "text/plain", "Parameters (lightsLessThanThreshold, countThreshold) are required.");
  }
}
void handleConnectToWiFi() {
  String ssid = server.arg("ssid");
  String password = server.arg("password");

  Serial.print("Received SSID: ");

  if (ssid.length() > 0 && password.length() > 0) {
    WiFi.begin(ssid.c_str(), password.c_str());
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 10) {
      delay(1000);
      attempts++;
      Serial.print(".");
    }
    Serial.println();  // Move to the next line

    if (WiFi.status() == WL_CONNECTED) {
      
      String ip = WiFi.localIP().toString();
      server.send(200, "text/plain", ip);

      Serial.println(initialTotalLights);
      for (int i = 0; i < initialTotalLights; i++) {
        pinMode(relayPins[i], OUTPUT);
        digitalWrite(relayPins[i], HIGH); // Assuming HIGH means 'off' and LOW means 'on'
        Serial.println(relayPins[i]);
      }
      // Define endpoints to control lights
      server.on("/lights/on", HTTP_POST, handleSwitchLightsOn);
      server.on("/lights/off", HTTP_POST, handleSwitchLightsOff);
      // Define the endpoint to set light configuration
      server.on("/lights/config", HTTP_POST, handleSetLightConfig);
      // Define the endpoint to set light configuration
      server.on("/lights/toggle", HTTP_POST, handletoggle);
      //delay(000); 
      //WiFi.softAPdisconnect(true);
    } else {
      server.send(500, "text/plain", "Failed to connect to Wi-Fi.");
      Serial.println("Failed to connect to Wi-Fi.");
    }
  } else {
    server.send(400, "text/plain", "SSID and Password required.");
    Serial.println("SSID and Password required.");
  }
}

void setup() {
  Serial.begin(115200);
  
  // Start ESP32 as an access point
  WiFi.softAP(ssid_ap, password_ap);
  IPAddress IP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(IP);

  // Initialize mDNS service
  if (!MDNS.begin("esp32")) {
    Serial.println("Error starting mDNS");
    return;
  }

  // Define endpoint to receive SSID and password for Wi-Fi connection
  server.on("/connect", HTTP_POST, handleConnectToWiFi);

  server.begin();  
  Serial.println("Server started");
}

void loop() {
  server.handleClient();  // Handle incoming client requests
}
