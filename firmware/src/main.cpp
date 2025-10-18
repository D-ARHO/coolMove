#include <Arduino.h>
#include <DallasTemperature.h>
#include <TinyGPS++.h>
#include <OneWire.h>
#include <SoftwareSerial.h>
#include <ArduinoJson.h>

#define TINY_GSM_MODEM_SIM808  // Tell TinyGSM you are using SIM808
#include <TinyGsmClient.h>

#define ONE_WIRE_BUS 2  // DS18B20 data pin

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

void setup() {
  Serial.begin(9600);
  sensors.begin();
  Serial.println("DS18B20 Temperature Test");
}

void loop() {
  sensors.requestTemperatures(); // Request temperature from sensor
  float tempC = sensors.getTempCByIndex(0); // Read first sensor
  Serial.print("Temperature: ");
  Serial.print(tempC);
  Serial.println(" °C");
  Serial.print("Found ");
  Serial.print(sensors.getDeviceCount());
  Serial.println(" device(s).");

  delay(100); // Update every 1 second
}


