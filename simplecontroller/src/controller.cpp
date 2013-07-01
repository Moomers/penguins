// Main controller code running on the Arduino built into each penguin
// (c) Moomers, Inc. 2012

#include <Arduino.h>
#include <Wire.h>
#include <SoftwareSerial.h>

#include "config.h"
#include "Sensors/Sensors.h"

/*********** Pin Assignments ***********************/
//joystick pins
const byte VerticalStickPin = 0;
const byte HorizontalStickPin = 1;

// temperature sensor (analog pin)
const byte TemperaturePin = 2;

// for sensing the approximate voltage on the battery (analog pin)
const byte BatteryVoltagePin = 3;

// magnetometer/accelerometer LSM303 (analog pins)
const byte LSM303SDAPin = 4;
const byte LSM303SCLPin = 5;

// these aren't used in the code, they're just here
// as a reminder that those pins are not available
const byte ServerRXPin = 0;
const byte ServerTXPin = 1;

// motor speed (these pins can be interrupts)
const byte RightEncoderPin = 2;
const byte LeftEncoderPin = 3;

// sonar
// NOTE: Timer0 is used for millis() timing, and shares pin 5 and 6,
// so don't mess with the frequency or nothing will happen on time.
const byte LeftSonarPWPin = 4;
const byte RightSonarPWPin = 5;

// talking to the Sabertooth driver
const byte DriverTXPin = 9;
const byte DriverRXPin = 10;

// used to show that the arduino main loop is running
const byte StoppedLEDPin = 11;
const byte WarnLEDPin = 12;
const byte RunLEDPin = 13;

/*************** Globals *********************/

// Sabertooth serial interface is unidirectional, so only TX is really needed
SoftwareSerial sabertoothSerial(DriverRXPin, DriverTXPin);

AnalogSensor horizontal("HS", HorizontalStickPin);
AnalogSensor vertical("VS", VerticalStickPin);
AnalogSensor voltage("BV", BatteryVoltagePin);
AnalogSensor temperature("DT", TemperaturePin);

Sonar leftSonar("LS", LeftSonarPWPin);
Sonar rightSonar("RS", RightSonarPWPin);

Sensor* sensors[] = {
  &horizontal,
  &vertical,

  &voltage,
  &temperature,

  &leftSonar,
  &rightSonar,
};

const unsigned int NumSensors = sizeof(sensors) / sizeof(sensors[0]);

/*************** Data Types  *********************/

static struct State {
  State() : emergencyStop(false),
    runLED(false) { }
  bool emergencyStop;
  bool runLED;
} state;

/*************** Prototypes  *********************/

void send_velocity_to_sabertooth(int left, int right);
void left_encoder_interrupt();
void right_encoder_interrupt();
void toggle_led();

// begin code
void setup()
{
  // initialize the serial communication with the server
  Serial.begin(9600);

  // start the wire protocol
  Wire.begin();

  // initialize communication with the sabertooth motor controller
  sabertoothSerial.begin(19200);
  sabertoothSerial.write(uint8_t(0));

  // initialize the interrupts on encoders
  pinMode(LeftEncoderPin, INPUT);           // set pin to input
  digitalWrite(LeftEncoderPin, HIGH);       // turn on pullup resistors
  attachInterrupt(LeftEncoderPin - 2, left_encoder_interrupt, FALLING);

  pinMode(RightEncoderPin, INPUT);           // set pin to input
  digitalWrite(RightEncoderPin, HIGH);       // turn on pullup resistors
  attachInterrupt(RightEncoderPin - 2, right_encoder_interrupt, FALLING);

  // initialize the led pin
  pinMode(StoppedLEDPin, OUTPUT);
  pinMode(WarnLEDPin, OUTPUT);
  pinMode(RunLEDPin, OUTPUT);

  // turn on the warn led to indicate a recent reset
  digitalWrite(WarnLEDPin, HIGH);
}

void loop()
{
  //read out the sensors
  for(unsigned int i = 0; i < NumSensors; i++) {
    if (!sensors[i])
      continue;

    sensors[i]->read();
  }

  // speed is from 100 to -100
  long speed = clamp(vertical.value(), 0, 1000);

  if (speed > 650) {
    speed = (speed - 600) / 4;
  } else if (speed < 350) {
    speed = (speed - 400) / 4;
  } else {
    speed = 0;
  }

  // we wired the joystick backwards...
  speed = -speed;

  // direction is between 0 and 100
  // 50 is in the middle, 0 is all the way to the left
  long direction = clamp(horizontal.value(), 0, 1000);

  if (direction > 650) {
    direction = 50 + (direction - 600) / 8;
  } else if (direction < 350) {
    direction = 50 + (direction - 400) / 8;
  } else {
    direction = 50;
  }

  int left = (2 * speed * direction * 30) / (100 * 100);
  int right = (2 * speed * (100 - direction) * 30) / (100 * 100);

  send_velocity_to_computer(left, right);
  send_velocity_to_sabertooth(left, right);

  // toggle the run led every time
  toggle_led();
}

// interrupt functions for logging encoder events
volatile int LEFT_PULSES = 0;
void left_encoder_interrupt() {
  LEFT_PULSES++;
}

volatile int RIGHT_PULSES = 0;
void right_encoder_interrupt() {
  RIGHT_PULSES++;
}

// code for talking to the sabertooth
inline int clamp(int value, int min, int max)
{
  if (value < min) {
    return min;
  } else if (value > max) {
    return max;
  }
  return value;
}

void send_velocity_to_sabertooth(int left, int right)
{
  left = clamp(left, -63, 63);
  right = clamp(right, -63, 63);

  if (left == 0 && right == 0) {
    digitalWrite(StoppedLEDPin, HIGH);
    sabertoothSerial.write(uint8_t(0));
  } else {
    digitalWrite(StoppedLEDPin, LOW);
    sabertoothSerial.write(uint8_t(64 + left));
    sabertoothSerial.write(uint8_t(192 + right));
  }
}

void send_velocity_to_computer(left, right) {
  Serial.print("V/H raw:");
  Serial.print(vertical.value());
  Serial.print("/");
  Serial.print(horizontal.value());
  Serial.print(";");

  Serial.print(" -- left/right speed:");
  Serial.print(left);
  Serial.print("/");
  Serial.print(right);
  Serial.print("\r\n");
}

void toggle_led()
{
  if(state.runLED) {
    digitalWrite(RunLEDPin, LOW);
    state.runLED = false;
  } else {
    digitalWrite(RunLEDPin, HIGH);
    state.runLED = true;
  }
}
