#include <Arduino.h> 
#include <WiFi.h> 
#include "GpsModule.h" 
#include "Esp32Module.h" 
#include "Temperature.h" 
#include "LcdDisplay.h" 

// ********************************************
// ⚠️ IMPORTANT: UPDATE THESE LINES 
// ********************************************
// IMEI updated to match the successful Postman payload
const char* DEVICE_IMEI = "123456789012345"; 
const char* WIFI_SSID = "DARHO";       // Your Wi-Fi SSID
const char* WIFI_PASS = "12345678";   // Your Wi-Fi Password

// Reverting to HTTP URL. Redirects must be handled by Esp32Module.cpp.
// const String API_URL = "https://coolmove-dashboard.onrender.com/api/data";
const String API_URL = "https://webhook.site/6eb4dbb2-700a-4656-8d4f-8c56d4d5ea7f";

// --- ERROR VALUES (Web App interprets these as sensor failure) ---
const float ERROR_LAT = -999.000;
const float ERROR_LON = -999.000;
const float ERROR_TEMP = -999.00;
// ********************************************

// --- PIN & CONFIG DEFINITIONS (Common ESP32 Pins) ---
#define GPS_RX_PIN 16 
#define GPS_TX_PIN 17 
#define TEMP_PIN 4    
#define LCD_ADDR 0x25 

// --- OBJECT INSTANTIATION ---
HardwareSerial gpsSerial(2); 

GpsModule gps(gpsSerial); 
Esp32Module http; 
TemperatureSensor thermometer(TEMP_PIN);
LcdDisplay lcd(LCD_ADDR, 16, 2); 

void setup() {
    Serial.begin(115200); 
    Serial.println(F("\n===================================="));
    Serial.println(F("    CoolMove Tracker Initialized    "));
    Serial.println(F("===================================="));
    
    // Initialize LCD
    lcd.begin();
    lcd.printLine(0, "Tracker Start...");
    
    // Initialize Temperature Sensor
    thermometer.begin();
    
    // Initialize GPS (9600 baud is standard for NEO-6M)
    gps.begin(9600); 
    
    // Initialize Wi-Fi
    if (http.begin(WIFI_SSID, WIFI_PASS)) {
        String ip = http.getIpAddress();
        Serial.print(F("✅ Wi-Fi: Connected. IP: ")); 
        Serial.println(ip);
        lcd.printLine(1, "WiFi OK | " + ip.substring(ip.lastIndexOf('.') + 1)); 
    } else {
        Serial.println(F("⚠️ Wi-Fi: Setup failed. Will attempt reconnection."));
        lcd.printLine(1, "WiFi Fail (Retry)");
    }
}

void loop() {
    Serial.println(F("\n--- LOOP START ---"));
    
    // --- 0. Wi-Fi Stability Check (Reconnection Logic) ---
    if (!http.isConnected()) {
        Serial.println(F("⚠️ Wi-Fi: Connection lost/unstable. Attempting to reconnect..."));
        lcd.printLine(1, "WiFi Reconnect...");
        
        if (!http.begin(WIFI_SSID, WIFI_PASS, 10000L)) { 
            Serial.println(F("❌ Wi-Fi: Reconnection failed. Skipping data send."));
            lcd.printLine(1, "Recon FAILED!");
            delay(15000); 
            return; 
        }
        String currentIp = http.getIpAddress();
        lcd.printLine(1, "WiFi OK | " + currentIp.substring(currentIp.lastIndexOf('.') + 1));
    }
    
    // 1. Get GPS Data 
    GpsData location = gps.getCoordinates(); 
    
    // 2. Get Temperature Data
    float rawTempC = thermometer.readCelsius();
    
    // --- 3. Determine Final Values (Error Handling) ---
    
    // GPS Check: Use actual location or error values
    float finalLat = location.fix ? location.latitude : ERROR_LAT;
    float finalLon = location.fix ? location.longitude : ERROR_LON;
    bool gpsOK = location.fix;
    
    // Temperature Check: DS18B20 returns -127.0 for error
    bool tempOK = (rawTempC > -100.0);
    float finalTemp = tempOK ? rawTempC : ERROR_TEMP;
    
    // --- 4. Display Data Summary ---
    Serial.print(F("[DATA] Raw Temp: ")); Serial.print(rawTempC, 2); Serial.println(F(" C"));
    
    // LCD Line 0: Status Summary
    String tempStatus = tempOK ? String("T:") + String(finalTemp, 1) + "C" : "T:Fail";
    String gpsStatus = gpsOK ? "Y" : "N";
    lcd.printLine(0, tempStatus + " | GPS: " + gpsStatus);
    
    // LCD Line 1: Action Status (Update before POST)
    String line1Msg = "Sending Data...";

    // Print error status to Serial
    if (!gpsOK) {
        Serial.println("⚠️ GPS: No fix. Sending error coordinates (" + String(ERROR_LAT) + ").");
        line1Msg = "GPS Error!";
    }
    if (!tempOK) {
        Serial.println("⚠️ TEMP: Sensor failed. Sending error temperature (" + String(ERROR_TEMP) + ").");
        line1Msg = "Temp Error!";
    }
    if (!gpsOK && !tempOK) {
        line1Msg = "All Sensors Fail!";
    }
    
    lcd.printLine(1, line1Msg); // Display immediate status
    
    // --- 5. COMPILE AND SEND DATA (ALWAYS SEND) ---
    
    // Compile JSON Payload using final (possibly error) values
    String jsonPayload = "{";
    jsonPayload += "\"imei\":\"" + String(DEVICE_IMEI) + "\","; 
    jsonPayload += "\"lat\":" + String(finalLat, 6) + ","; 
    jsonPayload += "\"lon\":" + String(finalLon, 6) + ","; 
    jsonPayload += "\"temp\":" + String(finalTemp, 2) + "}";

    Serial.print(F("TX: Payload Size: ")); Serial.println(jsonPayload.length()); 

    if (http.sendHttpRequest(API_URL, jsonPayload)) {
        lcd.printLine(1, "Data Sent OK! ✅");
        Serial.println("✅ POST: Data sent successfully!");
    } else {
        lcd.printLine(1, "POST FAILED! ❌");
        Serial.println("❌ POST: Data transmission FAILED. Retrying in next loop.");
    }

    delay(10000); // 10 seconds delay between sending attempts
}