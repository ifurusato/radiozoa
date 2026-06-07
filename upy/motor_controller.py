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

import asyncio

from logger import Logger, Level
from component import Component
from motor import Motor
from pid import PID

class MotorController(Component):
    '''
    Owns the two drive motors (port and starboard) and their PID controllers.
    Blends registered intent vectors from Behaviours by priority weighting,
    applies slew limiting, folds lateral intent (vx) into rotation via
    lateral_gain, then drives the motors using differential kinematics:

        V_port = vy + omega_final
        V_stbd = vy - omega_final
        omega_final = omega + lateral_gain × vx

    When _closed_loop is False (default until encoders are calibrated), encoder
    feedback is bypassed and target speed is mapped directly to motor power.

    Intended to be run as an asyncio task via _run(), registered by RROS.

    :param ring:   optional NeoPixel ring for motor speed visualisation
    :param level:  the logging level
    '''
    NAME = 'motor-ctrl'

    # GPIO pin assignments
    _IN1   = 14
    _IN2   = 12
    _IN3   =  6
    _IN4   =  4
    _ENC1A = 16
    _ENC1B = 17
    _ENC2A =  2
    _ENC2B =  1

    # ring pixels for motor speed visualisation: free pixels between cardinal positions
    _PORT_PIXEL = 5   # between SW(3) and W(6)
    _STBD_PIXEL = 19  # between E(18) and SE(21)

    # control loop period in ms (20Hz)
    _PERIOD_MS  = 50

    def __init__(self, ring=None, level=Level.INFO):
        Component.__init__(self, MotorController.NAME)
        self._log  = Logger(MotorController.NAME, level)
        self._ring = ring
        # motors: port uses IN1/IN2 and ENC1; stbd uses IN3/IN4 and ENC2
        self._motor_port = Motor('port', self._IN1, self._IN2, self._ENC1A, self._ENC1B, level=level)
        self._motor_stbd = Motor('stbd', self._IN3, self._IN4, self._ENC2A, self._ENC2B, level=level)
        # PID controllers — gains are initial estimates pending tuning with hardware
        self._pid_port   = PID('port', kp=0.8, ki=0.1, kd=0.05, level=level)
        self._pid_stbd   = PID('stbd', kp=0.8, ki=0.1, kd=0.05, level=level)
        # intent vectors registry: name → (vx, vy, omega, priority)
        self._intent_vectors = {}
        # lateral gain: scales vx contribution into omega correction
        self._lateral_gain   = 0.5  # tune empirically
        # slew limits: max change per tick at 20Hz (≈ 1.0/sec for vy, 2.0/sec for omega)
        self._slew_vy        = 0.05
        self._slew_omega     = 0.10
        self._last_vy        = 0.0
        self._last_omega     = 0.0
        # when False, bypasses PID and maps target speed directly to motor power
        self._closed_loop    = False
        self._stop           = False
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def closed_loop(self):
        return self._closed_loop

    @closed_loop.setter
    def closed_loop(self, value):
        self._closed_loop = value
        self._log.info('{} closed-loop mode.'.format('enabled' if value else 'disabled'))

    @property
    def lateral_gain(self):
        return self._lateral_gain

    @lateral_gain.setter
    def lateral_gain(self, value):
        self._lateral_gain = value

    def set_intent_vector(self, name, vx, vy, omega, priority):
        '''
        registers or updates an intent vector entry by name.
        '''
        self._intent_vectors[name] = (vx, vy, omega, priority)

    def remove_intent_vector(self, name):
        '''
        removes a previously registered intent vector.
        '''
        if name in self._intent_vectors:
            del self._intent_vectors[name]

    def _blend_intent_vectors(self):
        '''
        returns a priority-weighted average of all registered intent vectors
        as a (vx, vy, omega) tuple.
        '''
        if not self._intent_vectors:
            return (0.0, 0.0, 0.0)
        total_p = 0.0
        vx      = 0.0
        vy      = 0.0
        omega   = 0.0
        for entry in self._intent_vectors.values():
            p       = entry[3]
            vx     += entry[0] * p
            vy     += entry[1] * p
            omega  += entry[2] * p
            total_p += p
        if total_p > 0.0:
            vx    /= total_p
            vy    /= total_p
            omega /= total_p
        return (vx, vy, omega)

    def _slew(self, current, target, max_change):
        diff = target - current
        if diff >  max_change: return current + max_change
        elif diff < -max_change: return current - max_change
        return target

    def _tick(self):
        '''
        single control iteration: blend intent vectors, apply slew limiting,
        fold vx into omega, apply differential kinematics, drive motors,
        and update ring visualisation.
        '''
        vx, vy, omega = self._blend_intent_vectors()
        # slew limiting
        vy    = self._slew(self._last_vy,    vy,    self._slew_vy)
        omega = self._slew(self._last_omega, omega, self._slew_omega)
        self._last_vy    = vy
        self._last_omega = omega
        # fold lateral intent into rotation: ω_final = ω + lateral_gain × vx
        omega_final = omega + self._lateral_gain * vx
        if omega_final >  1.0: omega_final =  1.0
        elif omega_final < -1.0: omega_final = -1.0
        # differential kinematics
        v_port = vy + omega_final
        v_stbd = vy - omega_final
        if v_port >  1.0: v_port =  1.0
        elif v_port < -1.0: v_port = -1.0
        if v_stbd >  1.0: v_stbd =  1.0
        elif v_stbd < -1.0: v_stbd = -1.0
        # motor drive: closed-loop uses PID with encoder feedback, open-loop passes directly
        if self._closed_loop:
            self._pid_port.setpoint = v_port
            self._pid_stbd.setpoint = v_stbd
            self._pid_port.target   = self._motor_port.velocity
            self._pid_stbd.target   = self._motor_stbd.velocity
            pwr_port = self._pid_port()
            pwr_stbd = self._pid_stbd()
        else:
            pwr_port = v_port
            pwr_stbd = v_stbd
        self._motor_port.set_power(pwr_port)
        self._motor_stbd.set_power(pwr_stbd)
        # ring visualisation: cyan brightness encodes power magnitude
        if self._ring:
            n_port = int(abs(pwr_port) * 255)
            n_stbd = int(abs(pwr_stbd) * 255)
            self._ring.set_color(self._PORT_PIXEL, (0, n_port, n_port))
            self._ring.set_color(self._STBD_PIXEL, (0, n_stbd, n_stbd))

    async def _run(self):
        '''
        main asyncio coroutine, to be added as a task by RROS.
        runs _tick() at _PERIOD_MS intervals while enabled and not suppressed.
        '''
        while not self._stop:
            if self.enabled and not self.suppressed:
                self._tick()
            await asyncio.sleep_ms(self._PERIOD_MS)

    def brake(self):
        '''
        applies active braking to both motors and resets PID and slew state.
        '''
        self._motor_port.brake()
        self._motor_stbd.brake()
        self._pid_port.reset()
        self._pid_stbd.reset()
        self._last_vy    = 0.0
        self._last_omega = 0.0

    def coast(self):
        '''
        coasts both motors to a stop.
        '''
        self._motor_port.coast()
        self._motor_stbd.coast()

    def enable(self):
        if not self.enabled:
            Component.enable(self)
            self._log.info('enabled.')

    def disable(self):
        if self.enabled:
            self.coast()
            Component.disable(self)
            self._log.info('disabled.')

    def close(self):
        if not self.closed:
            self._stop = True
            self.coast()
            self._motor_port.close()
            self._motor_stbd.close()
            if self._ring:
                self._ring.set_color(self._PORT_PIXEL, (0, 0, 0))
                self._ring.set_color(self._STBD_PIXEL, (0, 0, 0))
            Component.close(self)
            self._log.info('closed.')

#EOF
