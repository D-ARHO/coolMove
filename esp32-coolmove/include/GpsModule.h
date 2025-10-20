#ifndef GPSMODULE_H
#define GPSMODULE_H

#include <Arduino.h>
#include <TinyGPSPlus.h>

struct GpsData {
    float latitude;
    float longitude;
    bool fix;
};

class GpsModule {
private:
    HardwareSerial& gpsSerial; 
    TinyGPSPlus gps;
    
public:
    GpsModule(HardwareSerial& serialPort); 
    void begin(long baudRate = 9600);
    GpsData getCoordinates();
};

#endif