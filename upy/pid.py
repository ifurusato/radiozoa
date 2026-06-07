#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-07
# modified: 2026-06-07

import time

class PID:
    '''
    A minimal PID controller for MicroPython.

    :param kp:          proportional gain
    :param ki:          integral gain
    :param kd:          derivative gain
    :param min_output:  minimum output (default -1.0)
    :param max_output:  maximum output (default  1.0)
    '''
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, min_output=-1.0, max_output=1.0):
        self._kp         = kp
        self._ki         = ki
        self._kd         = kd
        self._min_output = min_output
        self._max_output = max_output
        self._setpoint   = 0.0
        self.reset()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def kp(self):
        return self._kp

    @kp.setter
    def kp(self, value):
        self._kp = value

    @property
    def ki(self):
        return self._ki

    @ki.setter
    def ki(self, value):
        self._ki = value

    @property
    def kd(self):
        return self._kd

    @kd.setter
    def kd(self, value):
        self._kd = value

    @property
    def setpoint(self):
        return self._setpoint

    @setpoint.setter
    def setpoint(self, value):
        self._setpoint = value

    def __call__(self, measured):
        '''
        Compute and return the PID output for the given measured value.
        '''
        _now = time.ticks_ms()
        _dt  = time.ticks_diff(_now, self._last_time) / 1000.0
        if _dt <= 0.0:
            _dt = 0.001
        _error           = self._setpoint - measured
        _d_input         = measured - self._last_input
        self._integral  += self._ki * _error * _dt
        self._integral   = self._clip(self._integral)
        _derivative      = (-self._kd * _d_input / _dt) if _dt > 0.0 else 0.0
        _output          = self._clip(self._kp * _error + self._integral + _derivative)
        self._last_input = measured
        self._last_time  = _now
        return _output

    def reset(self):
        '''
        Reset all internal state to zero.
        '''
        self._integral   = 0.0
        self._last_input = 0.0
        self._last_time  = time.ticks_ms()

    def _clip(self, value):
        if value < self._min_output: return self._min_output
        if value > self._max_output: return self._max_output
        return value

#EOF
