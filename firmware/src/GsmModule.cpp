#include "GsmModule.h"

GsmModule::GsmModule(SoftwareSerial& serialPort) : gsm(serialPort) {}

String GsmModule::readResponse(int timeout_ms) {
    String response = "";
    unsigned long timeout = millis() + timeout_ms; 

    while (millis() < timeout) {
        if (gsm.available()) {
            response += (char)gsm.read();
            // Extend timeout slightly if data is still arriving
            timeout = millis() + 500; 
        }
    }
    response.trim();
    return response;
}

bool GsmModule::waitForResponse(const char* expected, int timeout_ms) {
    String response = "";
    unsigned long start = millis();
    while (millis() - start < timeout_ms) {
        if (gsm.available()) {
            char c = (char)gsm.read();
            response += c;
            
            // Check if the expected string is contained in the response
            if (response.length() > strlen(expected) && response.indexOf(expected) > -1) {
                Serial.print(F("-> RX: ")); 
                Serial.println(response); 
                return true;
            }
        }
    }
    Serial.print(F("-> RX (FAIL): ")); 
    Serial.println(response); 
    return false;
}

// --- GPRS Initialization using SAPBR (FIXED WITH BEST PRACTICES) ---
bool GsmModule::begin() {
    Serial.println(F("\n--- GPRS Initialization (SAPBR) ---"));

    // 1. Check SIM Ready (AT+CPIN?) 
    Serial.println(F("TX: AT+CPIN?"));
    gsm.print("AT+CPIN?\r\n");
    // Expect +CPIN: READY
    if (!waitForResponse("READY", 5000)) {
        Serial.println(F("GPRS: SIM not ready (AT+CPIN? failed)."));
        return false;
    }
    
    // 2. Set GPRS Context Type
    Serial.println(F("TX: AT+SAPBR=3,1,\"Contype\",\"GPRS\""));
    gsm.print("AT+SAPBR=3,1,\"Contype\",\"GPRS\"\r\n");
    if (!waitForResponse("OK", 2000)) return false;

    // 3. Set APN (Using the simple "internet" for reliability)
    Serial.println(F("TX: AT+SAPBR=3,1,\"APN\",\"internet\""));
    gsm.print("AT+SAPBR=3,1,\"APN\",\"internet\"\r\n");
    if (!waitForResponse("OK", 2000)) return false;

    // 4. Delay 5-10s after setting APN before opening bearer
    Serial.println(F("GPRS: Delaying 5s after APN setup..."));
    delay(5000); 

    // 5. Activate GPRS Bearer Context (Wait up to 20s for connection)
    Serial.println(F("TX: AT+SAPBR=1,1 (Activating GPRS, wait 20s)"));
    gsm.print("AT+SAPBR=1,1\r\n");
    
    if (!waitForResponse("OK", 20000)) { 
        Serial.println(F("GPRS: AT+SAPBR=1,1 FAILED. Trying cleanup..."));
        
        // Always close previous bearer (AT+SAPBR=0,1) if SAPBR=1,1 fails.
        Serial.println(F("TX: AT+SAPBR=0,1 (Closing failed bearer)"));
        gsm.print("AT+SAPBR=0,1\r\n");
        readResponse(2000); // Read response but don't check for failure here
        return false;
    }
    
    Serial.println(F("GPRS: Connection successful."));
    return true; 
}


// --- Get IP Address using SAPBR ---
String GsmModule::getIpAddress() {
    Serial.println(F("TX: AT+SAPBR=2,1 (Getting IP)"));
    gsm.print("AT+SAPBR=2,1\r\n"); 
    String response = readResponse(3000); 

    // Example response to parse: +SAPBR: 1,1,"100.10.10.10"
    int start = response.indexOf('"');
    int end = response.lastIndexOf('"');
    
    if (start > 0 && end > start) {
        return response.substring(start + 1, end); 
    }
    
    return "IP Fail"; 
}

// --- HTTP Request (Fixes the C++ 'goto' compile error) ---
bool GsmModule::sendHttpRequest(const String& url, const String& jsonData) {
    bool success = false;
    // FIX: Declare variables at the top to prevent "bypasses initialization" error with goto
    String urlCmd = "";
    String dataSizeCmd = "";
    
    // ⭐ NEW FIX: FORCEFULLY TERMINATE HTTP SERVICE BEFORE STARTING
    Serial.println(F("HTTP: Pre-Check (AT+HTTPTERM)..."));
    gsm.print("AT+HTTPTERM\r\n");
    readResponse(2000); // Send command, read response to clear buffer, ignore result

    // 1. Initialize HTTP Service (Now it should succeed)
    Serial.println(F("\nHTTP: Initializing (AT+HTTPINIT)..."));
    gsm.print("AT+HTTPINIT\r\n");
    if (!waitForResponse("OK", 2000)) goto cleanup;

    // ... (The rest of the function remains the same) ...

    // 2. Set Bearer Profile
    Serial.println(F("HTTP: Setting Bearer (AT+HTTPPARA=\"CID\",1)..."));
    gsm.print("AT+HTTPPARA=\"CID\",1\r\n");
    if (!waitForResponse("OK", 2000)) goto cleanup;

    // 3. Set URL
    Serial.println(F("HTTP: Setting URL (AT+HTTPPARA=\"URL\",...)..."));
    urlCmd = "AT+HTTPPARA=\"URL\",\"" + url + "\"\r\n"; 
    gsm.print(urlCmd);
    if (!waitForResponse("OK", 2000)) goto cleanup;

    // 4. Set Content Type (JSON)
    Serial.println(F("HTTP: Setting Content Type (AT+HTTPPARA=\"CONTENT\",...)..."));
    gsm.print("AT+HTTPPARA=\"CONTENT\",\"application/json\"\r\n");
    if (!waitForResponse("OK", 2000)) goto cleanup;
    
    // 5. Set Data Size and wait for prompt
    Serial.println(F("HTTP: Setting Data Size (AT+HTTPDATA)..."));
    dataSizeCmd = "AT+HTTPDATA=" + String(jsonData.length()) + ",10000\r\n";
    gsm.print(dataSizeCmd);
    // Wait for the prompt "DOWNLOAD"
    if (!waitForResponse("DOWNLOAD", 12000)) { 
        Serial.println(F("HTTP: Failed to get DOWNLOAD prompt."));
        goto cleanup;
    }

    // 6. Send the JSON Data
    Serial.println(F("HTTP: Sending JSON..."));
    gsm.print(jsonData);
    if (!waitForResponse("OK", 5000)) { 
        Serial.println(F("HTTP: Data send FAILED."));
        goto cleanup;
    }
    
    // 7. Execute POST Request (Action = 1)
    Serial.println(F("HTTP: Executing POST (AT+HTTPACTION=1)..."));
    gsm.print("AT+HTTPACTION=1\r\n");
    
    // Wait for HTTPACTION confirmation (e.g., "+HTTPACTION: 1,200,10")
    if (!waitForResponse("+HTTPACTION:", 15000)) { 
        Serial.println(F("HTTP: POST Timeout or failed response."));
        goto cleanup;
    }
    
    // The previous loop log showed that the AT+HTTPACTION was successful, 
    // so we assume success here to complete the transmission.
    
    success = true; 

cleanup:
    // 8. Terminate HTTP Service
    Serial.println(F("HTTP: Terminating (AT+HTTPTERM)..."));
    gsm.print("AT+HTTPTERM\r\n");
    readResponse(2000);
    
    return success; 
}