#ifndef GPSMODULE_H
#define GPSMODULE_H

#include <SoftwareSerial.h>
#include <Arduino.h>

struct GpsData {
    float latitude;
    float longitude;
    bool fix;
};

class GpsModule {
private:
    SoftwareSerial& gsm; 
    const char* GNSS_POWER_ON = "AT+CGNSPWR=1\r\n";
    const char* GET_GNSS_INFO = "AT+CGNSINF\r\n"; 

    String readResponse(int timeout_ms);
    
public:
    GpsModule(SoftwareSerial& serialPort); 
    void begin();
    GpsData getCoordinates();
};

#endif