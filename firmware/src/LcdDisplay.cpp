#include "LcdDisplay.h"

LcdDisplay::LcdDisplay(uint8_t addr, uint8_t cols, uint8_t rows)
    : lcd(addr, cols, rows) {}

void LcdDisplay::begin() {
    lcd.init();
    lcd.backlight();
    lcd.print("Tracker Initialized");
}

void LcdDisplay::printLine(int line, const char* message) {
    lcd.setCursor(0, line);
    lcd.print("                "); // Clear line
    lcd.setCursor(0, line);
    lcd.print(message);
}

void LcdDisplay::printLine(int line, String message) {
    lcd.setCursor(0, line);
    lcd.print("                "); // Clear line
    lcd.setCursor(0, line);
    lcd.print(message);
}

void LcdDisplay::clearScreen() {
    lcd.clear();
}