// Main controller code running on the Arduino built into each penguin
// (c) Moomers, Inc. 2012

#include <Arduino.h>
#include <Wire.h>
#include <SoftwareSerial.h>

#include "config.h"
#include "Sensors/Sensors.h"

/*********** Pin Assignments ***********************/

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


/*************** Constants *********************/

const unsigned long EmergencyBrakeMS = 1000;
const unsigned long StateSendMS = 50;

/*************** Globals *********************/

// Sabertooth serial interface is unidirectional, so only TX is really needed
SoftwareSerial sabertoothSerial(DriverRXPin, DriverTXPin);

AnalogSensor voltage("BV", BatteryVoltagePin);
AnalogSensor temperature("DT", TemperaturePin);

Sonar leftSonar("LS", LeftSonarPWPin);
Sonar rightSonar("RS", RightSonarPWPin);

#if defined(USE_AMG)
AMG amg("AMG");
#endif

Sensor* sensors[] = {
  &voltage,
  &temperature,

  &leftSonar,
  &rightSonar,

#if defined(USE_AMG)
  &amg,
#endif
};

const unsigned int NumSensors = sizeof(sensors) / sizeof(sensors[0]);

/*************** Data Types  *********************/

struct SerialCommand {
  enum Type {
    BAD = -1,
    NONE = 0,
    HEARTBEAT = 1,
    VELOCITY = 2,
    GO = 3,
    GETSTATE = 4,
    STOP = 5,
  };
  SerialCommand() : type(BAD), leftVelocity(0), rightVelocity(0) { }
  SerialCommand(Type t) : type(t), leftVelocity(0), rightVelocity(0) { }

  Type type;
  int leftVelocity;
  int rightVelocity;
};

static struct State {
  State() : badCommandsReceived(0),
    commandsReceived(0),
    lastCommandTimestamp(0),
    lastStateSentTimestamp(0),
    emergencyStop(false),
    runLED(false) { }
  unsigned long badCommandsReceived;
  unsigned long commandsReceived;
  unsigned long lastCommandTimestamp;
  unsigned long lastStateSentTimestamp;
  bool emergencyStop;
  bool runLED;
} state;

/*************** Prototypes  *********************/

const char* scan_int(const char* buf, int* value);
SerialCommand parse_command_buffer(const char* buf, int len);
SerialCommand read_server_command();
void execute_command(const SerialCommand& cmd);
void send_state(unsigned long now);
void send_velocity_to_sabertooth(int left, int right);
void left_encoder_interrupt();
void right_encoder_interrupt();
void emergency_stop();
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

  // go into emergency stop to begin with
  emergency_stop();
}

void loop()
{
  //read out the sensors
  //if sensor data is strange, stop the bot

  // get the current time
  unsigned long now = millis();
  // if time overflows, reset last command timestamp to now instead of
  // having a ridiculous overflow. this happens every 50 days, so every
  // 50 days, penguin will take twice as long to ebrake.
  if (state.lastCommandTimestamp > now)
    state.lastCommandTimestamp = now;

  // communicate with the server
  send_state(now);
  SerialCommand cmd = read_server_command();

  if (cmd.type == SerialCommand::NONE ||
      cmd.type == SerialCommand::BAD) {
    // no command was received
    // if too long since server sent something, stop
    if (now - state.lastCommandTimestamp > EmergencyBrakeMS) {
      if (!state.emergencyStop)
          emergency_stop();
    }

    // log receiving bad commands
    if (cmd.type == SerialCommand::BAD) {
      state.badCommandsReceived++;
    }

  // got a good command from the server; log and execute
  } else {
    state.lastCommandTimestamp = now;
    state.commandsReceived++;
    execute_command(cmd);
    digitalWrite(WarnLEDPin, LOW);
  }
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

void read_sensor_state() {
}

void execute_command(const SerialCommand& cmd)
{
  if (cmd.type == SerialCommand::GETSTATE) {
    // send state now
    state.lastStateSentTimestamp = 0;
  }

  if (cmd.type == SerialCommand::GO) {
    state.emergencyStop = false;
    digitalWrite(StoppedLEDPin, LOW);
  }

  if (cmd.type == SerialCommand::VELOCITY) {
    send_velocity_to_sabertooth(cmd.leftVelocity, cmd.rightVelocity);
  }

  if (cmd.type == SerialCommand::STOP) {
    emergency_stop();
  }
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

void send_velocity_to_sabertooth(int left, int right)
{
  left = clamp(left, -63, 63);
  right = clamp(right, -63, 63);
  if (state.emergencyStop) {
    left = 0;
    right = 0;
  }
  if (left == 0 && right == 0) {
    sabertoothSerial.write(uint8_t(0));
  } else {
    sabertoothSerial.write(uint8_t(64 + left));
    sabertoothSerial.write(uint8_t(192 + right));
  }
}

// sends the current program state to the computer
void send_state(unsigned long now)
{
  if (state.lastStateSentTimestamp != 0 &&
      now - state.lastStateSentTimestamp < StateSendMS) {
    return;
  }
  Serial.print("C:");
  Serial.print(state.commandsReceived, DEC);
  Serial.print(";");

  Serial.print("B:");
  Serial.print(state.badCommandsReceived, DEC);
  Serial.print(";");

  Serial.print("L:");
  Serial.print(now - state.lastCommandTimestamp, DEC);
  Serial.print(";");

  Serial.print("E:");
  Serial.print(state.emergencyStop, DEC);
  Serial.print(";");

  Serial.print("!");
  for(unsigned int i = 0; i < NumSensors; i++) {
    if (!sensors[i])
      continue;

    sensors[i]->read();
    Serial.print(sensors[i]->get_data());
    Serial.print(";");
  }

  // special handling for encoders
  Serial.print("LE:");
  Serial.print(LEFT_PULSES);
  Serial.print(";");
  Serial.print("RE:");
  Serial.print(RIGHT_PULSES);
  Serial.print(";");

  Serial.print("\r\n");

  state.lastStateSentTimestamp = now;
  toggle_led();
}

// reads data from the serial port and returns the last sent SerialCommand
SerialCommand read_server_command()
{
  // Commands end with a '\n'
  static char buf[20];
  static int buf_pos = 0;
  static bool buffer_overflow = false;
  char c;

  // read data from serial port and write it into buf
  while ((c = Serial.read()) != -1) {
    buf[buf_pos] = c;
    
    // we've read a whole command once we see a '\n'
    if (c == '\n') {
      break;

    } else {
      buf_pos++;
      if (buf_pos == sizeof(buf)) {
        // command buffer overflow
        buf_pos = 0;
        buffer_overflow = true;
      }
    }
  }

  // we read a full command from the serial port
  if (buf[buf_pos] == '\n') {
    SerialCommand cmd;
    if (buffer_overflow) {
      cmd = SerialCommand(SerialCommand::BAD);
    } else {
      cmd = parse_command_buffer(buf, buf_pos);
    }

    buf_pos = 0;
    buffer_overflow = false;
    for (int i = 0; i < sizeof(buf); i++) {
        buf[i] = 0;
    }

    return cmd;

  // haven't read a full command yet; lets return no command
  } else {
    return SerialCommand(SerialCommand::NONE);
  }
}

// parses string read from incoming serial from the computer into a SerialCommand
SerialCommand parse_command_buffer(const char* buf, int len)
{
  // Protocol from the server:
  // V<left>,<right>\n  -- set motor velocities, int in [-63, 63]
  // H\n                -- heartbeat
  // S\n                -- causes an immediate send of the current state
  // G\n                -- go (clears an emergency stop)
  // X\n                -- stop (causes an emergency stop to occur)

  SerialCommand cmd;
  switch (buf[0]) {
  case 'H': 
    cmd.type = SerialCommand::HEARTBEAT;
    break;
  case 'G':
    cmd.type = SerialCommand::GO;
    break;
  case 'S':
    cmd.type = SerialCommand::GETSTATE;
    break;
  case 'X':
    cmd.type = SerialCommand::STOP;
    break;
  case 'V':
    cmd.type = SerialCommand::VELOCITY;
    buf = scan_int(buf+1, &cmd.leftVelocity);
    if (*buf != ',') {
      cmd.type = SerialCommand::BAD;
    } else {
      buf = scan_int(buf+1, &cmd.rightVelocity);
      if (*buf != '\n') {
        cmd.type = SerialCommand::BAD;
      }
    }
    break;
  default:
    cmd.type = SerialCommand::BAD;
  }

  return cmd;
}

// used to read an integer from serial data
const char* scan_int(const char* buf, int *value)
{
  // initialize the value
  *value = 0;

  // determine the sign of the value
  int sign = 1;
  if (buf[0] == '-') {
    sign = -1;
    buf++;
  }

  // parse the value -- works as long as we encounter valid numbers
  while (*buf >= '0' && *buf <= '9') {
    *value = (10 * (*value)) + (*buf - '0');
    buf++;
  }

  // we're done
  *value = *value * sign;
  return buf;
}

void emergency_stop() 
{
  state.emergencyStop = true;
  digitalWrite(StoppedLEDPin, HIGH);
  send_velocity_to_sabertooth(0,0);
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
