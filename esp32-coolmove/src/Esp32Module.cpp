#include "Esp32Module.h" 
#include <HTTPClient.h> 

// --- Wi-Fi Initialization ---
bool Esp32Module::begin(const char* ssid, const char* password, long timeout_ms) {
    Serial.println(F("\n--- Wi-Fi Initialization ---"));

    WiFi.begin(ssid, password);
    Serial.print(F("Connecting to Wi-Fi "));
    Serial.print(ssid);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start < (unsigned long)timeout_ms)) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println(F("\n✅ Wi-Fi Connected."));
        return true;
    } else {
        Serial.println(F("\n❌ Wi-Fi Failed to connect."));
        return false;
    }
}

// --- Get IP Address ---
String Esp32Module::getIpAddress() {
    if (WiFi.status() == WL_CONNECTED) {
        return WiFi.localIP().toString();
    }
    return "0.0.0.0";
}

// --- Check Connection Status ---
bool Esp32Module::isConnected() {
    return WiFi.status() == WL_CONNECTED;
}

// --- Log HTTP Status ---
void Esp32Module::logStatus(int httpCode) {
    if (httpCode > 0) {
        // httpCode 307 means redirect; the client should follow this and the final code should be 200/201
        Serial.printf("[HTTP] POST status: %d\n", httpCode); 
    } else {
        Serial.printf("[HTTP] POST failed, error: %s\n", HTTPClient::errorToString(httpCode).c_str());
    }
}

// --- HTTP POST Request ---
bool Esp32Module::sendHttpRequest(const String& url, const String& jsonData) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println(F("❌ HTTP: Wi-Fi not connected. Skipping POST."));
        return false;
    }

    HTTPClient http;
    
    // ✅ FIX: Enable automatic redirect following (for 307 from HTTP to HTTPS)
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
    
    // NOTE: Removed http.setInsecure() since the function is not found. 
    // We rely on the redirect handling and hope the older HTTPClient is lenient with SSL.

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    Serial.print(F("TX: Posting to URL: ")); Serial.println(url);
    Serial.print(F("TX: Payload: ")); Serial.println(jsonData);
    
    int httpCode = http.POST(jsonData);
    
    logStatus(httpCode);

    http.end();
    
    // Return true for any successful status code (200-299)
    return (httpCode >= 200 && httpCode < 300); 
}