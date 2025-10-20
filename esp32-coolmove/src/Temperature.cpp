#include "Temperature.h"

TemperatureSensor::TemperatureSensor(uint8_t pin) 
    : oneWire(pin), sensors(&oneWire) {}

void TemperatureSensor::begin() {
    sensors.begin();
}

float TemperatureSensor::readCelsius() {
    sensors.requestTemperatures(); 
    return sensors.getTempCByIndex(0); 
}