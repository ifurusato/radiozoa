#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-07
# modified: 2026-07-18

from math import sqrt
from colorama import Fore, Style

from logger import Logger, Level
from event import TOF_DISTANCES
from behaviour import Behaviour
from radiozoa_sensor import OUT_OF_RANGE

# sensor index order matches device registry: N=0, NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7
# corresponding angles (degrees):              0,   45,   90,  135,  180,  225,  270,  315

_R2 = sqrt(2.0) / 2.0   # sin/cos of 45° ≈ 0.7071

# pre-computed trig constants — never reallocated
_SIN = [  0.0,  _R2,  1.0,  _R2,  0.0, -_R2, -1.0, -_R2 ]
_COS = [  1.0,  _R2,  0.0, -_R2, -1.0, -_R2,  0.0,  _R2 ]

# pre-allocated pressure buffer — updated in-place each call, never reallocated
_P = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]

class Radiozoa(Behaviour):
    NAME = 'radiozoa'
    '''
    Subscribes to TOF_DISTANCES messages and converts the eight distance
    readings into a (vx, vy, omega) intent vector for the MotorController.

    vx is the lateral component (robot cannot physically strafe; the
    MotorController folds this into omega via lateral_gain).
    vy is the longitudinal component (forward/reverse).
    omega is the rotational component derived from port/starboard pressure
    asymmetry via the torque moment formula.

    Priority scales dynamically with proximity: closer obstacles produce
    higher priority, giving avoidance greater weight in the motor blend.

    A note on the omega formula:
    N (index 0) and S (index 4) are excluded from the P_left − P_right sum since
    they sit exactly on the fore-aft axis and contribute zero net torque. 
    Including them would dilute the port/starboard asymmetry signal without 
    adding directional information.

    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    _D_MIN        =   40.0
    _D_MAX        = 1000.0
    _D_RANGE      = _D_MAX - _D_MIN   # 960.0
    _GAIN_VX      = 0.25  # tune empirically
    _GAIN_VY      = 0.25  # tune empirically
    _GAIN_OMEGA   = 0.40  # tune empirically
    _DEADBAND     = 0.02
    _PRIORITY_MIN = 0.3   # priority when no obstacles in range
    _PRIORITY_MAX = 1.0   # priority at closest obstacle threshold

    def __init__(self, message_bus, motor_controller=None, level=Level.INFO):
        Behaviour.__init__(self, Radiozoa.NAME, message_bus, level)
        self._motor_controller = motor_controller
        self._priority = self._PRIORITY_MIN
        self.add_event(TOF_DISTANCES)
        self._intent_vector = (0.0, 0.0, 0.0)
        self._log.info('ready.')

    def enable(self):
        if self.disabled:
            if self._motor_controller:
                self._motor_controller.add_intent_vector(
                    Radiozoa.NAME,
                    lambda: self._intent_vector if self.is_active else (0.0, 0.0, 0.0),
                    lambda: self._priority)
            super().enable()
            self._log.info('enabled.')
        else:
            self._log.warn('already enabled.')

    def disable(self):
        if self.enabled:
            if self._motor_controller:
                self._motor_controller.remove_intent_vector(Radiozoa.NAME)
            super().disable()
            self._log.info('disabled.')
        else:
            self._log.warn('already disabled.')

    async def process_message(self, message):
        self._log.info('processing message: ' + Fore.GREEN + '{}'.format(message))
        distances = message.value
        vx, vy, omega = self._process(distances)
        self._intent_vector = (vx, vy, omega)

    def _process(self, distances):
        '''
        Converts 8 distance readings into a (vx, vy, omega) intent vector
        and updates dynamic priority.
        Sensor order: N=0, NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7.
        '''
        # 1. compute proximity pressure for each sensor: [0.0=no obstacle, 1.0=critical]
        min_dist = self._D_MAX
        for i in range(8):
            d = distances[i]
            if d is None or d >= OUT_OF_RANGE or d >= self._D_MAX:
                _P[i] = 0.0
            else:
                if d < self._D_MIN:
                    d = self._D_MIN
                _P[i] = (self._D_MAX - d) / self._D_RANGE
                if d < min_dist:
                    min_dist = d

        # 2. dynamic priority: scales linearly from _PRIORITY_MIN (no obstacle)
        #    to _PRIORITY_MAX (obstacle at _D_MIN)
        if min_dist < self._D_MAX:
            t = 1.0 - ((min_dist - self._D_MIN) / self._D_RANGE)
            if t < 0.0: t = 0.0
            if t > 1.0: t = 1.0
            self._priority = self._PRIORITY_MIN + t * (self._PRIORITY_MAX - self._PRIORITY_MIN)
        else:
            self._priority = self._PRIORITY_MIN

        # 3. spatial decomposition:
        #    vy: forward/reverse repulsion via cos projection
        #    vx: lateral repulsion via sin projection (fed to MotorController as steering bias)
        #    omega: port/starboard torque moment — P_left minus P_right where
        #           port  = N(0), NW(7), W(6), SW(5)
        #           starboard = N(0), NE(1), E(2), SE(3)
        #           N(0) and S(4) are excluded as they straddle the centre axis
        vx_raw    = 0.0
        vy_raw    = 0.0
        for i in range(8):
            p       = _P[i]
            vx_raw -= p * _SIN[i]
            vy_raw -= p * _COS[i]

        # port sensors: NW=7, W=6, SW=5; starboard sensors: NE=1, E=2, SE=3
        omega_raw = (_P[7] + _P[6] + _P[5]) - (_P[1] + _P[2] + _P[3])

        # obtain bias from motor controller's analog control
#       _bias = self._motor_controller.bias

        # 4. apply gain, clamp, deadband
        vx = vx_raw * self._GAIN_VX
        if vx >  1.0: vx =  1.0
        elif vx < -1.0: vx = -1.0
        if -self._DEADBAND < vx < self._DEADBAND: vx = 0.0

        vy = vy_raw * self._GAIN_VY
        if vy >  1.0: vy =  1.0
        elif vy < -1.0: vy = -1.0
        if -self._DEADBAND < vy < self._DEADBAND: vy = 0.0

        omega = omega_raw * self._GAIN_OMEGA
        if omega >  1.0: omega =  1.0
        elif omega < -1.0: omega = -1.0
        if -self._DEADBAND < omega < self._DEADBAND: omega = 0.0

        return (vx, vy, omega)

#EOF
