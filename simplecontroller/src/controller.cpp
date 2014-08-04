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

static struct Drive {
  Drive() : forward(1),
    backward(-1),
    max_speed(45),
    turn_assist(15),
    h_center(450),
    v_center(450),
    h_gap(50),
    v_gap(50),
    h_range(400),
    v_range(400) { }
  short forward;
  short backward;
  short max_speed;
  short turn_assist;
  short h_center;
  short v_center;
  short h_gap;
  short v_gap;
  short h_range;
  short v_range;
} drive;

/*************** Prototypes  *********************/

void send_velocity_to_computer(int speed, int side, int left, int right);
void send_velocity_to_sabertooth(int left, int right);
void left_encoder_interrupt();
void right_encoder_interrupt();
void read_sensors();
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

  // turn on the warn led to indicate calibration
  digitalWrite(WarnLEDPin, HIGH);

  int h_reads = 0,
      v_reads = 0,
      reads = 16;

  for (int i =0; i < reads; i++) {
    read_sensors();
    h_reads += horizontal.value();
    v_reads += vertical.value();
  }

  drive.h_center = h_reads / reads;
  drive.v_center = v_reads / reads;

  // calibration complete
  digitalWrite(WarnLEDPin, LOW);
}

inline int clamp(int value, int min, int max)
{
  if (value < min) {
    return min;
  } else if (value > max) {
    return max;
  }
  return value;
}

void loop()
{
  read_sensors();

  short direction = drive.forward;

  int speed = clamp(
          vertical.value(),
          drive.v_center - drive.v_gap - drive.v_range,
          drive.v_center + drive.v_gap + drive.v_range);

  // speed is from 0 to 100
  if (speed > drive.v_center + drive.v_gap) {
    speed = (speed - (drive.v_center + drive.v_gap)) / 4;
    direction = drive.backward;
  } else if (speed < drive.v_center - drive.v_gap) {
    speed = (drive.v_center - drive.v_gap - speed) / 4;
  } else {
    speed = 0;
  }

  // side is between -100 and 100
  // -100 is all the way on the right
  int side = clamp(
          horizontal.value(),
          drive.h_center - drive.h_gap - drive.h_range,
          drive.h_center + drive.h_gap + drive.h_range);

  if (side > drive.h_center + drive.h_gap) {
    side = (side - (drive.h_center + drive.h_gap)) / 4;
  } else if (side < (drive.h_center - drive.h_gap)) {
    side = (side - (drive.h_center - drive.h_gap)) / 4;
  } else {
    side = 0;
  }

  // allow more careful controls while turning
  short min_speed = -drive.turn_assist * direction;
  short max_speed = speed + (drive.turn_assist * direction);

  // get the left/right speed -- never more than limits
  long right = direction * clamp(speed - side, min_speed, max_speed);
  long left = direction * clamp(speed + side, min_speed, max_speed);

  // proportional to the max speed we want sabertooth to go
  left = drive.max_speed * left / 100;
  right = drive.max_speed * right / 100;

  send_velocity_to_computer(speed, side, left, right);
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

void read_sensors()
{
  //read out the sensors
  for(unsigned int i = 0; i < NumSensors; i++) {
    if (!sensors[i])
      continue;

    sensors[i]->read();
  }
}

// code for talking to the sabertooth
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

void send_velocity_to_computer(int speed, int side, int left, int right) {
  Serial.print("V/H raw:");
  Serial.print(vertical.value());
  Serial.print("/");
  Serial.print(horizontal.value());
  Serial.print(";");

  Serial.print("-- h/v center:");
  Serial.print(drive.h_center);
  Serial.print("/");
  Serial.print(drive.v_center);
  Serial.print(";");


  Serial.print("-- speed/side:");
  Serial.print(speed);
  Serial.print("/");
  Serial.print(side);
  Serial.print(";");


  Serial.print(" -- left/right:");
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
