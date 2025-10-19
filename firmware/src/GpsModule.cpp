#include "GpsModule.h"

GpsModule::GpsModule(SoftwareSerial& serialPort) : gsm(serialPort) {}

String GpsModule::readResponse(int timeout_ms) {
    String response = "";
    unsigned long timeout = millis() + timeout_ms; 
    while (millis() < timeout) {
        if (gsm.available()) {
            response += (char)gsm.read();
            timeout = millis() + 500; 
        }
    }
    response.trim();
    return response;
}

void GpsModule::begin() {
    Serial.println("\n--- GPS Initialization ---");
    // Turn GPS ON
    gsm.print(GNSS_POWER_ON);
    readResponse(1500); // Wait for OK
    Serial.println("GPS Engine ON.");
    delay(2000); 
}

GpsData GpsModule::getCoordinates() {
    GpsData data = {0.0, 0.0, false};
    
    // Request GPS data
    gsm.print(GET_GNSS_INFO);
    String rawData = readResponse(3000); 

    // Find the data line and parse it
    int dataStartIndex = rawData.indexOf("+CGNSINF:");
    if (dataStartIndex > -1) {
        String info = rawData.substring(dataStartIndex + 9);
        
        // Split the comma-separated string: +CGNSINF: 1,1,20240101120000.000,LAT,LON,ALT,SPEED...
        int commas[15];
        int count = 0;
        for (int i = 0; i < info.length() && count < 15; i++) {
            if (info.charAt(i) == ',') {
                commas[count++] = i;
            }
        }
        
        // Fix Status (field 2, index 1)
        String fixStatus = info.substring(commas[0] + 1, commas[1]); 
        if (fixStatus.toInt() == 1) { // 1 means a valid fix (2D or 3D)
            data.fix = true;
            
            // Latitude (field 4, index 3)
            String latStr = info.substring(commas[2] + 1, commas[3]);
            data.latitude = latStr.toFloat();
            
            // Longitude (field 5, index 4)
            String lonStr = info.substring(commas[3] + 1, commas[4]);
            data.longitude = lonStr.toFloat();
        }
    }
    return data;
}