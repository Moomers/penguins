// Main controller code running on the Arduino built into each penguin
// (c) Moomers, Inc. 2012

#include <Arduino.h>
#include <Wire.h>
#include <SoftwareSerial.h>

#include "config.h"
#include "Sensors/Sensors.h"

/*********** Pin Assignments ***********************/

// these aren't used in the code, they're just here
// as a reminder that those pins are not available
const byte ServerRXPin = 0;
const byte ServerTXPin = 1;

// talking to the Sabertooth driver
const byte DriverRXPin = 10;
const byte DriverTXPin = 11;

// reading the pot for steering (analog pins)
const byte LeftPotPin = 0;
const byte RightPotPin = 1;

// pushbuttons on controller
const byte LeftButtonPin = 6;
const byte RightButtonPin = 7;

// motor speed (these pins can be interrupts)
const byte LeftMotorSpeedPin = 2;
const byte RightMotorSpeedPin = 3;

// sonar
const byte LeftSonarPWPin = 4;
const byte rightSonarPWPin = 5;

// magnetometer/accelerometer LSM303 (analog pins)
const byte LSM303SDAPin = 4;
const byte LSM303SCLPin = 5;

/*************** Constants *********************/

const unsigned long MaxLoopsSinceCommand = 10000;  // TODO: 1 second.
const unsigned long LoopsBetweenStateSend = 10000;  // TODO: 1 second.

/*************** Globals *********************/

// Sabertooth serial interface is unidirectional, so only TX is really needed
SoftwareSerial sabertoothSerial(DriverRXPin, DriverTXPin);

Potentiometer leftPot("LP", LeftPotPin);
Potentiometer rightPot("RP", RightPotPin);
Sonar leftSonar("LS", LeftSonarPWPin);
#if defined(USE_AMG)
AMG amg("AMG");
#endif

Sensor* sensors[] = {
  &leftPot,
  &rightPot,
  &leftSonar,
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
    RESET = 3,
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
    loopsSinceLastCommand(0),
    loopsSinceStateSent(0),
    emergencyStop(false) { }
  unsigned long badCommandsReceived;
  unsigned long commandsReceived;
  unsigned long loopsSinceLastCommand;
  unsigned long loopsSinceStateSent;
  bool emergencyStop;
} state;

/*************** Prototypes  *********************/

const char* scan_int(const char* buf, int* value);
SerialCommand parse_command_buffer(const char* buf, int len);
SerialCommand read_server_command();
void execute_command(const SerialCommand& cmd);
void emergency_stop();
void send_state();
void send_velocity_to_sabertooth(int left, int right);

// begin code
void setup()
{
  // initialize the serial communication with the server
  Serial.begin(9600);
  Serial.println("R");  // Tell the server we reset.

  // start the wire protocol
  Wire.begin();

  // initialize communication with the sabertooth motor controller
  sabertoothSerial.begin(19200);
  sabertoothSerial.write(uint8_t(0));
}

void loop()
{
  //read out the sensors
  //if sensor data is strange, stop the bot

  // communicate with the server
  send_state();
  SerialCommand cmd = read_server_command();

  if (cmd.type == SerialCommand::NONE ||
      cmd.type == SerialCommand::BAD) {
    // no command was received
    state.loopsSinceLastCommand++;

    // if too long since server sent something, stop
    if (state.loopsSinceLastCommand > MaxLoopsSinceCommand) {
      if (!state.emergencyStop)
          emergency_stop();
    }

    // log receiving bad commands
    if (cmd.type == SerialCommand::BAD) {
      state.badCommandsReceived++;
    }

  // got a good command from the server; log and execute
  } else {
    state.loopsSinceLastCommand = 0;
    state.commandsReceived++;
    execute_command(cmd);
  }
}

void read_sensor_state() {
}

void execute_command(const SerialCommand& cmd)
{
  if (cmd.type == SerialCommand::GETSTATE) {
    state.loopsSinceStateSent = LoopsBetweenStateSend;
  }

  if (cmd.type == SerialCommand::RESET) {
    state.emergencyStop = false;
  }

  if (cmd.type == SerialCommand::VELOCITY) {
    send_velocity_to_sabertooth(cmd.leftVelocity, cmd.rightVelocity);
  }

  if (cmd.type == SerialCommand::STOP) {
    state.emergencyStop = true;
    send_velocity_to_sabertooth(0, 0);
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
void send_state()
{
  if (state.loopsSinceStateSent++ < LoopsBetweenStateSend) {
    return;
  }
  Serial.print("C:");
  Serial.print(state.commandsReceived, DEC);
  Serial.print(";");

  Serial.print("B:");
  Serial.print(state.badCommandsReceived, DEC);
  Serial.print(";");

  Serial.print("L:");
  Serial.print(state.loopsSinceLastCommand, DEC);
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

  Serial.print("\r\n");
  state.loopsSinceStateSent = 0;
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
  // R\n                -- reset (clears an emergency stop)
  // X\n                -- stop (causes an emergency stop to occur)

  SerialCommand cmd;
  switch (buf[0]) {
  case 'H': 
    cmd.type = SerialCommand::HEARTBEAT;
    break;
  case 'R':
    cmd.type = SerialCommand::RESET;
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
  send_velocity_to_sabertooth(0,0);
}
