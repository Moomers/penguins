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
        'control_timeout_brake':2.5,
        'control_timeout_stop':5,
        'timeout_brake_speed':3,

        'file_touch_path':'/tmp/server-monitor-alive',
        'file_touch_interval':1,

        'loop_min_interval':.05,
        }







            min_speed = 0, max_speed = 100, max_turn_speed = 200, max_acceleration = 1, max_braking = 10,
            speed_adjust = 1, left_speed_adjust = 1, right_speed_adjust = 1,
            min_update_interval = 0.1):

        'driver':{
            'minimum speed':5,
            'maximum speed':90,

            # max diff between left and right speed
            # this is the equivant of max turn velocity
            'maximum difference':50,

            # subtract some speed to allow driving straight
            # must be between 0 and 1
            'steering adjust':{
                'left':[
                    (100, 1),
                    ],
                'right':[
                    (20, 0.98),
                    (100,0.96)
                    ],
                },

            'acceleration_velocity':200,
            },

        'monitor':{
            'sensor_alerts':{
                {'sensor':'Driver temperature', 'set':50, 'clear':40, 'action':'nothing'},
                {'sensor':'Battery voltage', 'set',
                'temperature'
            'max_running_time':[
                (


            'left motor adjust':1,
            'right motor adjust':1,


