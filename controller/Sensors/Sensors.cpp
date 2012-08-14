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
  unsigned long pulse = pulseIn(pin_, HIGH, 20000);
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

// *** Accelerometer/Magnetometer/Gyro
#if defined(USE_AMG)

AMG::AMG(const char *sensor_prefix)
  : Sensor(sensor_prefix),
    initialized_(0) {
}

AMG::~AMG() {
}

void AMG::init() {
  gyro_.enableDefault();
  compass_.init();
  compass_.enableDefault();
}

void AMG::read() {
  if (!initialized_)
    init();

  compass_.read();
  a_.x = compass_.a.x;
  a_.y = compass_.a.y;
  a_.z = compass_.a.z;

  m_.x = compass_.m.x;
  m_.y = compass_.m.y;
  m_.z = compass_.m.z;

  gyro_.read();
  g_.x = gyro_.g.x;
  g_.y = gyro_.g.y;
  g_.z = gyro_.g.z;
}

char *AMG::get_data() {
  static char buf[60];
  sprintf(buf, "%s:%d,%d,%d,%d,%d,%d,%d,%d,%d", prefix_, (int)a_.x, (int)a_.y, (int)a_.z, (int)m_.x, (int)m_.y, (int)m_.z, (int)g_.x, (int)g_.y, (int)g_.z);
  return buf;
}
#endif
