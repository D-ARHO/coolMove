#include <OneWire.h>
#include <DallasTemperature.h>

// Data wire is connected to Arduino digital pin 2
#define ONE_WIRE_BUS 2

// Setup a one-wire instance to communicate with any OneWire device
OneWire oneWire(ONE_WIRE_BUS);

// Pass our oneWire reference to Dallas Temperature sensor 
DallasTemperature sensors(&oneWire);

// Variable to store the device address (if found)
DeviceAddress tempDeviceAddress;

void setup(void) {
  Serial.begin(9600);
  Serial.println("DS18B20 Test Sketch");

  // Start the library
  sensors.begin();

  // Locate devices on the bus
  Serial.print("Locating devices...");
  Serial.print("Found ");
  Serial.print(sensors.getDeviceCount(), DEC);
  Serial.println(" device(s).");

  // Check if a device was found
  if (sensors.getDeviceCount() == 0) {
    Serial.println("\n--- STATUS: FAILED ---");
    Serial.println("No DS18B20 sensor found! Check wiring and 4.7k resistor.");
    return; // Stop here if no sensor is found
  }

  // Get the address of the first device on the bus
  if (sensors.getAddress(tempDeviceAddress, 0)) {
    Serial.println("\n--- STATUS: DETECTED ---");
    Serial.print("Device Address: ");
    for (uint8_t i = 0; i < 8; i++) {
      // Print the address in hexadecimal format
      Serial.print(tempDeviceAddress[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
  } else {
    Serial.println("Could not find a valid address.");
  }
}

void loop(void) {
  // Request temperature conversion from all devices on the bus
  sensors.requestTemperatures(); 

  // Read the temperature from the device
  float tempC = sensors.getTempCByIndex(0);
  float tempF = sensors.getTempFByIndex(0);

  // Check for a valid reading (CRC error, etc.)
  if (tempC == DEVICE_DISCONNECTED_C) {
    Serial.println("--- STATUS: FAILED ---");
    Serial.println("Error reading temperature! Check connection stability.");
  } else {
    Serial.print("Temperature: ");
    Serial.print(tempC);
    Serial.print(" °C  |  ");
    Serial.print(tempF);
    Serial.println(" °F");
  }

  // A working sensor should show a realistic ambient temperature.
  // Perform the "Flick Test" now: Briefly touch the sensor with your finger 
  // and watch the temperature rise!
  
  delay(2000); // Wait 2 seconds before the next reading
}