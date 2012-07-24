#ifndef Sensor_h
#define Sensor_h

#include <Arduino.h>

// The interface that sensors implement.
class Sensor
{
  public:
    // sensor_prefix is a string that will be printed in messages from the sensor.
    explicit Sensor(const char *sensor_prefix);
    virtual ~Sensor();

    // Read data from the sensor and store it.
    virtual void read() = 0;
    // Return whatever buffered data has been read.
    virtual char *get_data() = 0;

  protected:
    const char *prefix_;
};

class Potentiometer : public Sensor
{
  public:
    Potentiometer(const char *sensor_prefix, const byte potPin);
    virtual ~Potentiometer();

    // Sensor interface:
    virtual void read();
    virtual char *get_data();

  private:
    const byte pin_;
    unsigned int last_value_;
};

#endif
