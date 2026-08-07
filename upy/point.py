#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-08-07
# modified: 2026-08-07

import asyncio
import time
from colorama import Fore, Style

from component import Component
from behaviour import Behaviour
from logger import Level
from imu import IMU

class Point(Behaviour):
    NAME = 'point'
    '''
    With a target heading, asynchronously attempts aligns the robot with that
    heading, by outputting rotational speed (omega) to the motor controller.
    This Behaviour does not subscribe to any events.

    Note that the functioning of the behaviour relies not on enable/disable
    but on suppress and release. The behaviour does need to be enabled in order
    for its loop task to occur, but it's suppress and release that determine if
    the intent vector is actually modified.

    :param message_bus:      the message bus
    :param motor_controller: the MotorController instance
    :param level:            the logging level
    '''
    def __init__(self, config=None, message_bus=None, motor_controller=None, imu=None, level=Level.INFO):
        Behaviour.__init__(self, Point.NAME, message_bus, level)
        if config is None:
            raise TypeError('configuration argument is null.')
        _cfg = config['rros']['point']
        self._motor_controller = motor_controller
        registry = Component.get_registry()
        self._imu = registry.get(IMU.NAME)
        if self._imu is None:
            raise TypeError('no imu available.')
        else:
            self._log.info('imu available.')
        self._task = None
        # configuration ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._verbose  = _cfg['verbose']
        self._priority = _cfg['priority']
        # intent vector ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._vx    = 0.0
        self._vy    = 0.0
        self._omega = 0.0
        self._intent_vector = (self._vx, self._vy, self._omega)
        # PID controller ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._kp = 0.02 # TODO from config
        self._ki = 0.0
        self._kd = 0.005
        self._tolerance = tolerance
        self._previous_error = 0.0
        self._integral = 0.0
        self._log.info('ready.')

    def _update_vector(self):
        self._intent_vector = (self._vx, self._vy, self._omega)
        self._log.info('intent updated: ' + Fore.GREEN + '{}'.format(self._intent_vector))

    def _normalize_error(self, target_heading, current_heading):
        '''
        Calculates shortest angular distance in range [-180, 180].
        '''
        return (target_heading - current_heading + 180) % 360 - 180

    async def align_to(self, target_heading, rate_hz=20):
        '''
        Rotates in place until current heading is within tolerance of target.
        '''
        self._previous_error = 0.0
        self._integral = 0.0

        interval_ms = int(1000 / rate_hz)
        last_ticks = time.ticks_ms()

        while self.enabled:
            now_ticks = time.ticks_ms()
            dt = time.ticks_diff(now_ticks, last_ticks) / 1000.0
            last_ticks = now_ticks

            current_heading = self._imu.heading
            error = self._normalize_error(target_heading, current_heading)

            if abs(error) <= self._tolerance:
                # target reached; halt rotation and exit task
                self._motor_controller.set_intent((0.0, 0.0, 0.0))
                break

            self._integral += error * dt
            derivative = (error - self._previous_error) / dt if dt > 0 else 0.0
            self._previous_error = error

            # pass intent vector (vx, vy, omega) to motor controller
            if self.released:
                self._omega = (self._kp * error) + (self._ki * self._integral) + (self._kd * derivative)
                self._log.info('released; ' + Fore.GREEN + 'omega: {:.2f}.'.format(self._omega))
#               self._motor_controller.set_intent((0.0, 0.0, omega))
            else:
                self._omega = 0.0
                self._log.info(Style.DIM + 'suppressed; ' + Fore.GREEN + 'omega: {:.2f}.'.format(omega))

            self._update_vector():

            await asyncio.sleep_ms(interval_ms)

    def enable(self):
        if self.disabled:
            if self._motor_controller:
                self._motor_controller.add_intent_vector(
                    Point.NAME,
                    lambda: self._intent_vector if self.is_active else (0.0, 0.0, 0.0),
                    lambda: self._priority)
            super().enable()
            self._log.info('enabled.')
        else:
            self._log.warn('already enabled.')

    def disable(self):
        if self.enabled:
            if self._motor_controller:
                self._motor_controller.remove_intent_vector(Point.NAME)
            super().disable()
            self._log.info('disabled.')
        else:
            self._log.warn('already disabled.')

#EOF
