#include "GPS.h"

SIM808GPS::SIM808GPS(uint8_t rxPin, uint8_t txPin)
  : sim808Serial(rxPin, txPin) {}

void SIM808GPS::begin(long baud) {
  sim808Serial.begin(baud);
}

bool SIM808GPS::readData() {
  while (sim808Serial.available() > 0) {
    gps.encode(sim808Serial.read());
  }
  return gps.location.isUpdated();
}

double SIM808GPS::getLatitude() {
  return gps.location.lat();
}

double SIM808GPS::getLongitude() {
  return gps.location.lng();
}

bool SIM808GPS::hasFix() {
  return gps.location.isValid();
}
