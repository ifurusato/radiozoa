#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-10
# modified: 2026-06-10

import itertools
from math import sqrt
from colorama import Fore, Style

from analog_ctrl import AnalogControl
from behaviour import Behaviour
from event import TOF_DISTANCES
from logger import Level
from pixel import Pixel
from radiozoa_sensor import OUT_OF_RANGE

class Roam(Behaviour):
    '''
    Subscribes to TOF_DISTANCES messages and uses the North (index 0) sensor
    reading to produce a forward/reverse velocity intent (vy only). Speed is
    set by the MotorController's analog bias value and scaled down as the
    robot approaches a forward obstacle, stopping at _D_MIN.

    vx and omega are always 0.0; steering is handled by RadiozoaBehaviour.
    Priority is fixed; RadiozoaBehaviour's dynamic priority naturally
    dominates as obstacles are detected on other axes.

    :param message_bus:      the message bus
    :param motor_controller: the MotorController instance
    :param visualiser:       the ring visualiser
    :param level:            the logging level
    '''
    _D_MIN    = 150.0   # stop threshold in mm
    _D_MAX    = 800.0   # full-speed threshold in mm
    _D_RANGE  = _D_MAX - _D_MIN

    _PRIORITY = 0.4     # fixed; below RadiozoaBehaviour's maximum
    _DEADBAND = 0.02

    def __init__(self, config=None, message_bus=None, motor_controller=None, visualiser=None, level=Level.INFO):
        Behaviour.__init__(self, 'roam', message_bus, level)
        if config is None:
            raise TypeError('configuration argument is null.')
        _cfg = config['rros']['roam']
        self._motor_controller = motor_controller
        self._visualiser = visualiser
        self._priority   = self._PRIORITY
        self.add_event(TOF_DISTANCES)
        # analog controller ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._pin_analog = _cfg['pin_analog']    # 22
        self._counter    = itertools.count()
        self._control    = AnalogControl(config)
        self._bias       = 0.0
        self._last_bias  = 0.0
        self._intent_vector = (0.0, 0.0, 0.0)
        if self._motor_controller is not None:
            self._motor_controller.add_intent_vector(
                'roam',
                lambda: self._intent_vector if self.is_active else (0.0, 0.0, 0.0),
                lambda: self._priority)
        self._log.info('ready.')

    async def process_message(self, message):
        distances = message.value
        vx, vy, omega = self._process(distances)
        self._intent_vector = (vx, vy, omega)

    def _process(self, distances):
        '''
        Computes (0.0, vy, 0.0) from the North sensor reading and analog bias.
        Speed is obstacle-scaled with square-root easing between _D_MIN and _D_MAX.
        '''
        # analog bias [-1.0, 1.0] is the requested speed and direction
        self._bias = round(self._control.value, 2)
        self._visualiseBias()
        self._last_bias = self._bias

        if -self._DEADBAND < self._bias < self._DEADBAND:
            return (0.0, 0.0, 0.0)
        # forward obstacle scaling only applies when moving forward
        if self._bias > 0.0:
            d = distances[0]  # North sensor
            if d is None or d >= OUT_OF_RANGE or d >= self._D_MAX:
                obstacle_scale = 1.0
            elif d <= self._D_MIN:
                obstacle_scale = 0.0
            else:
                normalised     = (d - self._D_MIN) / self._D_RANGE
                obstacle_scale = sqrt(normalised)  # square-root easing
            vy = self._bias * obstacle_scale
        else:
            # reverse motion: no obstacle scaling
            vy = self._bias
        if -self._DEADBAND < vy < self._DEADBAND:
            vy = 0.0
        return (0.0, vy, 0.0)

    def _visualiseBias(self):
        # map [-1.0, 1.0] to [0.0, 0.5] to use only half the color wheel.
        # -1.0 becomes 0.0 (Red), 0.0 becomes 0.25 (Green), 1.0 becomes 0.5 (Cyan)
        hue = (self._bias + 1.0) / 4.0
        # Brightness still dips to 0.0 at the center deadband
        brightness = abs(self._bias)
        rgb_analog = Pixel.hsv_to_rgb(hue, 1.0, brightness)
        self._visualiser.set_color(self._pin_analog, rgb_analog)
        self._count = next(self._counter)
        if self._bias != self._last_bias:
            self._log.info("analog value: {}".format(self._bias))
        elif self._count % 20 == 0:
            self._log.info(
                Fore.BLACK
                + "analog value: {}".format(self._bias)
                + Style.RESET_ALL
            )

#EOF
