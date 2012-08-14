#!/usr/bin/env python

driver = {
        'min_speed':5,
        'max_speed':95,
        'max_turn_speed':50,
        'max_acceleration':1,
        'max_braking':20,
        'speed_adjust':1,
        'left_speed_adjust':1,
        'right_speed_adjust':.95,
        'min_update_interval':0.1,
        }

monitor = {
        'time_between_reset_attempts':.5,
        'client_timeout':5,
        'control_timeout_brake':2,
        'control_timeout_stop':6,
        'timeout_brake_speed':2,

        'file_touch_path':'/tmp/server-monitor-alive',
        'file_touch_interval':1,

        'loop_min_interval':.05,
        }
