#ifndef GSMMODULE_H
#define GSMMODULE_H

#include <SoftwareSerial.h>
#include <Arduino.h>

class GsmModule {
private:
    SoftwareSerial& gsm; 

    String readResponse(int timeout_ms);
    bool waitForResponse(const char* expected, int timeout_ms);
    
public:
    GsmModule(SoftwareSerial& serialPort); 
    bool begin();
    String getIpAddress();
    bool sendHttpRequest(const String& url, const String& data);
};

#endif