#!/usr/bin/env python

driver = {
        'min_speed':5,
        'max_speed':95,
        'max_turn_speed':50,
        'max_acceleration':3,
        'max_braking':20,
        'speed_adjust':1,
        'left_speed_adjust':1,
        'right_speed_adjust':.95,
        'min_update_interval':0.2,
        }

monitor = {
        'time_between_reset_attempts':.5,
        'client_timeout':5,
        'control_timeout_brake':3,
        'control_timeout_stop':8,
        'timeout_brake_speed':2,

        'file_touch_path':'/tmp/server-monitor-alive',
        'file_touch_interval':1,

        'loop_min_interval':.05,

        'driver_safe_temperature':30,
        'driver_warn_temperature':40,
        'driver_estop_temperature':70,
        'battery_safe_voltage':22,
        'battery_warn_voltage':20,
        'battery_estop_voltage':15,

        'sonar_warn_distance':40,
        'sonar_safe_distance':60,

        'encoder_safe_delta':100,
        'encoder_warn_delta':200,
        }
