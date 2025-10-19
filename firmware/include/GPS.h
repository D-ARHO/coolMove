#ifndef GPS_H
#define GPS_H

#include <Arduino.h>
#include <TinyGPSPlus.h>
#include <SoftwareSerial.h>

class SIM808GPS {
  private:
    SoftwareSerial sim808Serial;
    TinyGPSPlus gps;
  public:
    SIM808GPS(uint8_t rxPin, uint8_t txPin);
    void begin(long baud = 9600);
    bool readData();
    double getLatitude();
    double getLongitude();
    bool hasFix();
};

#endif
