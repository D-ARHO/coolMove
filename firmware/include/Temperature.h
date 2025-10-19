#ifndef TEMPERATURE_H
#define TEMPERATURE_H

#include <DallasTemperature.h>
#include <OneWire.h>
#include <Arduino.h>

class TemperatureSensor {
private:
    OneWire oneWire;
    DallasTemperature sensors;
public:
    TemperatureSensor(uint8_t pin);
    void begin();
    float readCelsius();
};

#endif