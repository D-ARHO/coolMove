#include <Arduino.h>
#include <SoftwareSerial.h>

#define SIM808_RX 3  // Arduino RX <- SIM808 TX
#define SIM808_TX 4  // Arduino TX -> SIM808 RX

SoftwareSerial sim808Serial(SIM808_RX, SIM808_TX); // RX, TX

// Function declarations
void connectGPRS();
void sendAT(String command);

void setup() {
  Serial.begin(9600);
  sim808Serial.begin(9600);
  delay(1000);

  Serial.println("CoolMove: SIM808 GPRS Test");
  connectGPRS(); // call the GPRS test function
}

void loop() {
  // nothing in loop, GPRS test is in setup
}

// Function definitions
void connectGPRS() {
  Serial.println("Setting up GPRS...");

  // 1. Check module
  sendAT("AT");
  sendAT("AT+CSQ");        // Signal quality
  sendAT("AT+CREG?");      // Network registration

  // 2. Configure GPRS
  sendAT("AT+SAPBR=3,1,\"CONTYPE\",\"GPRS\"");
  sendAT("AT+SAPBR=3,1,\"APN\",\"your_apn_here\""); // Replace with your SIM card APN

  // 3. Open GPRS context
  sendAT("AT+SAPBR=1,1");
  delay(3000);
  sendAT("AT+SAPBR=2,1"); // Check connection status

  // 4. Test HTTP GET request
  sendAT("AT+HTTPINIT");
  sendAT("AT+HTTPPARA=\"CID\",1");
  sendAT("AT+HTTPPARA=\"URL\",\"http://example.com\""); // Replace with a test URL
  sendAT("AT+HTTPACTION=0"); // 0 = GET
  delay(5000);
  sendAT("AT+HTTPREAD");
  sendAT("AT+HTTPTERM");

  // 5. Close GPRS
  sendAT("AT+SAPBR=0,1");

  Serial.println("GPRS test finished.");
}

void sendAT(String command) {
  sim808Serial.println(command);
  Serial.print("> "); Serial.println(command);
  delay(2000);

  while (sim808Serial.available()) {
    char c = sim808Serial.read();
    Serial.write(c);
  }
  Serial.println();
}
