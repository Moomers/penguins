#include <Arduino.h>
#include <stdio.h>
#include "Sensors.h"

Sensor::Sensor(const char *sensor_prefix)
  : prefix_(sensor_prefix) {
}

Sensor::~Sensor() {
}

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


