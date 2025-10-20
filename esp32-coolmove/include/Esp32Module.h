#ifndef ESP32MODULE_H
#define ESP32MODULE_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

class Esp32Module { // Renamed the class
public:
    // Initialization and Connectivity
    bool begin(const char* ssid, const char* password, long timeout_ms = 20000L);
    String getIpAddress();
    bool isConnected();

    // Data Transmission
    bool sendHttpRequest(const String& url, const String& jsonData);

private:
    // Helper to log HTTP status
    void logStatus(int httpCode);
};

#endif