#include "GpsModule.h"

// The ESP32's HardwareSerial is passed to the constructor
GpsModule::GpsModule(HardwareSerial& serialPort) : gpsSerial(serialPort) {}

void GpsModule::begin(long baudRate) {
    Serial.println("\n--- GPS Initialization ---");
    gpsSerial.begin(baudRate);
    Serial.print("GPS Serial started at ");
    Serial.print(baudRate);
    Serial.println(" baud.");
}

GpsData GpsModule::getCoordinates() {
    // Process any available GPS data on the serial port
    while (gpsSerial.available() > 0) {
        gps.encode(gpsSerial.read());
    }

    GpsData data = {0.0, 0.0, false};
    
    // TinyGPSPlus checks for valid fix
    if (gps.location.isValid() && gps.location.isUpdated()) {
        data.fix = true;
        data.latitude = gps.location.lat();
        data.longitude = gps.location.lng();
    }
    
    // If no fix, but the time is valid, still useful for debugging.
    if (!data.fix) {
        if (gps.location.isValid()) {
             Serial.println("GPS: Valid location data, but no recent update.");
        } else {
             Serial.println("GPS: No valid location data received yet.");
        }
    }

    return data;
}