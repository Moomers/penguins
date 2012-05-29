// Main controller code running on the Arduino built into each penguin
// (c) Moomers, Inc. 2012

#include <Arduino.h>

const unsigned long MaxLoopsSinceCommand = 10000;  // TODO: 1 second.
const unsigned long LoopsBetweenStateSend = 10000;  // TODO: 1 second.

struct SerialCommand {
  enum Type {
    BAD = -1,
    NONE = 0,
    HEARTBEAT = 1,
    MOVE = 2,
    REFRESH = 3,
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
    loopsSinceStateSent(0) { }
  unsigned long badCommandsReceived;
  unsigned long commandsReceived;
  unsigned long loopsSinceLastCommand;
  unsigned long loopsSinceStateSent;
} state;

const char* scan_int(const char* buf, int* value);
SerialCommand parse_command_buffer(const char* buf, int len);
SerialCommand read_server_command();
void emergency_stop();
void send_state();

void setup()
{
  // initialize the serial communication with the server
  Serial.begin(9600);
  Serial.println("R");  // Tell the server we reset.
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

    if (cmd.type == SerialCommand::REFRESH) {
      state.loopsSinceStateSent = LoopsBetweenStateSend;
    }
  }
}

void send_state()
{
  if (state.loopsSinceStateSent++ < LoopsBetweenStateSend) {
    return;
  }
  Serial.print("S ");

  Serial.print("C:");
  Serial.print(state.commandsReceived, DEC);
  Serial.print(",");

  Serial.print("B:");
  Serial.print(state.badCommandsReceived, DEC);
  Serial.print(",");

  Serial.print("L:");
  Serial.print(state.loopsSinceLastCommand, DEC);
  Serial.print("\r\n");
  state.loopsSinceStateSent = 0;
}

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

SerialCommand parse_command_buffer(const char* buf, int len)
{
  // Protocol from the server:
  // V<left>,<right>\n  -- set motor velocities, int in [-100, 100]
  // H\n                 -- heartbeat
  // R\n

  SerialCommand cmd;
  switch (buf[0]) {
  case 'H': 
    cmd.type = SerialCommand::HEARTBEAT;
    break;
  case 'R':
    cmd.type = SerialCommand::REFRESH;
    break;
  case 'V':
    cmd.type = SerialCommand::MOVE;
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
}
