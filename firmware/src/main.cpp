#include <SoftwareSerial.h>
#include "GpsModule.h" // Assuming this is correct
#include "GsmModule.h"
#include "Temperature.h" // Assuming this is correct
#include "LcdDisplay.h" // Assuming this is correct

// ********************************************
// ⚠️ IMPORTANT: UPDATE THIS LINE 
// This IMEI must be registered to a device in your PostgreSQL database
// ********************************************
const char* DEVICE_IMEI = "123456789012345"; 

// --- PIN & CONFIG DEFINITIONS ---
#define RX_GSM 10 
#define TX_GSM 11 
#define TEMP_PIN 2 
#define LCD_ADDR 0x23 

// --- OBJECT INSTANTIATION ---
SoftwareSerial gsmSerial(RX_GSM, TX_GSM);

GpsModule gps(gsmSerial); 
GsmModule gsm(gsmSerial); 

TemperatureSensor thermometer(TEMP_PIN);
LcdDisplay lcd(LCD_ADDR, 16, 2); 

void setup() {
    Serial.begin(9600);
    Serial.println(F("\n===================================="));
    Serial.println(F("     CoolMove Tracker Initialized     "));
    Serial.println(F("===================================="));
    
    // Initialize LCD
    lcd.begin();
    lcd.printLine(0, "Tracker Start...");
    
    // Initialize Temperature Sensor
    thermometer.begin();
    
    // Initialize SIM808 module's serial port
    gsmSerial.begin(9600);
    delay(1000);
    
    // Initialize GPS 
    gps.begin(); 
    
    // Initialize GSM (connect to GPRS)
    if (gsm.begin()) {
        String ip = gsm.getIpAddress();
        Serial.print(F("✅ GPRS: Connected. IP: ")); 
        Serial.println(ip);
        lcd.printLine(1, "GPRS OK | " + ip);
    } else {
        Serial.println(F("⚠️ GPRS: Setup failed. Will attempt data transmission."));
        lcd.printLine(1, "GPRS Fail (Retry)");
    }
}

void loop() {
    Serial.println(F("\n--- LOOP START ---"));
    
    // 1. Get GPS Data
    GpsData location = gps.getCoordinates(); 
    
    // 2. Get Temperature Data
    float tempC = thermometer.readCelsius();
    
    // --- 3. Display Data Summary ---
    Serial.print(F("[DATA] Temp: ")); Serial.print(tempC); Serial.println(F(" C"));
    
    // LCD Output
    lcd.printLine(0, "T:" + String(tempC, 1) + "C | GPS: " + (location.fix ? "Y" : "N"));
    
    // --- 4. COMPILE AND SEND DATA ---
    if (location.fix) { 
        Serial.print(F("[DATA] GPS Fix OK. Lat=")); Serial.print(location.latitude, 4);
        Serial.print(F(", Lon=")); Serial.println(location.longitude, 4);
        
        // Compile JSON Payload with IMEI, Lat, Lon, and Temp
        String jsonPayload = "{";
        jsonPayload += F("\"imei\":\""); jsonPayload += DEVICE_IMEI; jsonPayload += F("\","); 
        jsonPayload += F("\"lat\":"); jsonPayload += String(location.latitude, 4); jsonPayload += F(",");
        jsonPayload += F("\"lon\":"); jsonPayload += String(location.longitude, 4); jsonPayload += F(",");
        jsonPayload += F("\"temp\":"); jsonPayload += String(tempC, 2);
        jsonPayload += F("}");

        // The target API endpoint on your server
        String apiURL = "http://webhook.site/6eb4dbb2-700a-4656-8d4f-8c56d4d5ea7f"; // Use your IP!
        // String apiURL = "https://coolmove-tracker.onrender.com/api/data"; // Use your IP!

        Serial.print(F("TX: Payload: ")); Serial.println(jsonPayload); 

        if (gsm.sendHttpRequest(apiURL, jsonPayload)) {
            Serial.println(F("✅ POST: Data sent successfully!"));
            lcd.printLine(1, "Data Sent OK!");
        } else {
            Serial.println(F("❌ POST: Data transmission FAILED. (Check IMEI and Server Logs)"));
            lcd.printLine(1, "POST FAILED!");
        }
    } else {
        Serial.println(F("⚠️ GPS: No fix. Skipping data send."));
        lcd.printLine(1, "Acquiring GPS...");
    }
    
    Serial.println(F("--- LOOP END (Wait 10s) ---"));
    
    delay(8000); // Wait 10 seconds before next loop cycle
}