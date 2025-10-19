#ifndef LCDDISPLAY_H
#define LCDDISPLAY_H

#include <LiquidCrystal_I2C.h>

class LcdDisplay {
private:
    LiquidCrystal_I2C lcd;
public:
    // Constructor: address, columns, rows
    LcdDisplay(uint8_t addr, uint8_t cols, uint8_t rows);
    void begin();
    void printLine(int line, const char* message);
    void printLine(int line, String message);
    void clearScreen();
};

#endif