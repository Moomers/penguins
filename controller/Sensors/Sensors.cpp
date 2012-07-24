// Sensors code for the penguin project, by Igor Serebryany and Jered Wierzbicki
// There are many kinds of sensors defined here:
// Potentiometer: Similar to Potentiometer arduino library by Alexander Brevig
// Pushbutton: original code by Igor Serebryany
// Sonar: uses the MaxSonar device, code borrowed from Bruce Allen
// Gyro: ??
// Magnetometer/Accelerometer: ??

#include <Arduino.h>
#include <stdio.h>
#include "Sensors.h"

Sensor::Sensor(const char *sensor_prefix)
  : prefix_(sensor_prefix) {
}

Sensor::~Sensor() {
}

// *** Potentiometer ***
Potentiometer::Potentiometer(const char *sensor_prefix, const byte potPin)
  : Sensor(sensor_prefix),
    pin_(potPin),
    //bigger than any possible value we can read
    last_value_(1025) {
}

Potentiometer::~Potentiometer() {
}

void Potentiometer::read() {
  last_value_ = analogRead(pin_);
}

char *Potentiometer::get_data() {
  if (last_value_ > 1024) {
    return NULL;
  } else {
    static char buf[10];
    sprintf(buf, "%s:%d", prefix_, last_value_);
    return buf;
  }
}

// *** Sonar ***
Sonar::Sonar(const char *sensor_prefix, const byte sonarPin)
  : Sensor(sensor_prefix),
    pin_(sonarPin),
    last_value_(0) {
  pinMode(pin_, INPUT);
}

Sonar::~Sonar() {
}

void Sonar::read() {
  unsigned long pulse = pulseIn(pin_, HIGH);
  last_value_ = pulse / 147; //147 uS per inch
}

char *Sonar::get_data() {
  static char buf[10];
  sprintf(buf, "%s:%d", prefix_, last_value_);
  return buf;
}
