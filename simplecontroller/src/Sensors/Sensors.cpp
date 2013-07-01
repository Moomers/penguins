// Sensors code for the penguin project, by Igor Serebryany and Jered Wierzbicki
// There are many kinds of sensors defined here:
// Potentiometer: Similar to Potentiometer arduino library by Alexander Brevig
// Pushbutton: original code by Igor Serebryany
// Sonar: uses the MaxSonar device, code borrowed from Bruce Allen
// Gyro/Magnetometer/Accelerometer: on the L3G4200D carrier; code borrowed from Popolu Corporation

#include <Arduino.h>
#include <stdio.h>

#include "Sensors.h"

Sensor::Sensor(const char *sensor_prefix)
  : prefix_(sensor_prefix) {
}

Sensor::~Sensor() {
}

// *** an analog sensor ***
AnalogSensor::AnalogSensor(const char *sensor_prefix, const byte sensorPin)
  : Sensor(sensor_prefix),
    pin_(sensorPin),
    //bigger than any possible value we can read
    last_value_(1025) {
}

AnalogSensor::~AnalogSensor() {
}

void AnalogSensor::read() {
  last_value_ = analogRead(pin_);
}

char *AnalogSensor::get_data() {
  if (last_value_ > 1024) {
    return NULL;
  } else {
    static char buf[10];
    sprintf(buf, "%s:%d", prefix_, last_value_);
    return buf;
  }
}

// *** digital sensor ***
DigitalSensor::DigitalSensor(const char *sensor_prefix, const byte sensorPin)
  : Sensor(sensor_prefix),
    pin_(sensorPin),
    //bigger than any possible value we can read
    last_value_(0) {
  pinMode(pin_, INPUT);           // set pin to input
  digitalWrite(pin_, HIGH);       // turn on pullup resistors
}

DigitalSensor::~DigitalSensor() {
}

void DigitalSensor::read() {
  last_value_ = digitalRead(pin_);
}

char *DigitalSensor::get_data() {
  static char buf[6];
  sprintf(buf, "%s:%d", prefix_, last_value_);
  return buf;
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
  unsigned long pulse = pulseIn(pin_, HIGH, 60000);
  last_value_ = pulse / 147; //147 uS per inch
}

char *Sonar::get_data() {
  static char buf[10];
  sprintf(buf, "%s:%d", prefix_, last_value_);
  return buf;
}

// *** Pushbutton

// *** Encoder
Encoder::Encoder(const char *sensor_prefix, const byte sensorPin)
  : Sensor(sensor_prefix),
    pin_(sensorPin),
    rotations_(0) {
  pinMode(pin_, INPUT);           // set pin to input
  digitalWrite(pin_, HIGH);       // turn on pullup resistors
}

Encoder::~Encoder() {
}

void Encoder::log_rotation() {
  rotations_++;
}

void Encoder::read() {
}

char *Encoder::get_data() {
  static char buf[10];
  sprintf(buf, "%s:%d", prefix_, rotations_);
  return buf;
}
