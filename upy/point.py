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
    With a target heading, asynchronously aligns the robot with that
    heading by outputting rotational speed (omega) to the motor controller.
    This Behaviour does not subscribe to any events.

    Note that the functioning of the behaviour relies not on enable/disable
    but on suppress and release. The behaviour does need to be enabled in order
    for its loop task to occur, but its suppress and release determine if
    the intent vector is actually modified.

    :param config:           the configuration dictionary
    :param message_bus:      the message bus instance
    :param motor_controller: the MotorController instance
    :param imu:              the IMU instance
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
        self._verbose      = _cfg['verbose']
        self._priority     = _cfg['priority']
        self._kp           = _cfg.get('kp', 0.003)            # proportional gain (heading error sensitivity) (was 0.007)
        self._ki           = _cfg.get('ki', 0.0)              # integral gain (steady-state error accumulation)
        self._kd           = _cfg.get('kd', 0.001)            # derivative gain (rotational velocity damping)
        self._tolerance    = _cfg.get('tolerance', 1.5)       # target error threshold in degrees
        self._hysteresis   = _cfg.get('hysteresis', 1.0)      # deadband buffer in degrees to prevent oscillation
        self._max_omega    = _cfg.get('max_omega', 0.08)      # maximum angular velocity output cap
        self._max_slew     = _cfg.get('max_slew', 5.0)        # maximum allowable change in angular velocity per loop (was 0.4)
        self._max_integral = _cfg.get('max_integral', 10.0)   # anti-windup clamp on accumulated integral error
        self._use_gyro_damping = False

        # target & state ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._target_heading = 0.0
        self._stop_on_target = False
        self._aligned        = False

        # intent vector ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._vx    = 0.0
        self._vy    = 0.0
        self._omega = 0.0
        self._intent_vector = (self._vx, self._vy, self._omega)

        # PID controller ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._previous_error = 0.0
        self._integral = 0.0
        self._log.info('ready.')

    def _update_vector(self):
        self._intent_vector = (self._vx, self._vy, self._omega)
        self._log.debug('intent updated: ' + Fore.GREEN + '{}'.format(self._intent_vector))

    def _normalize_error(self, target_heading, current_heading):
        '''
        Calculates shortest angular distance in range [-180, 180].
        '''
        return (target_heading - current_heading + 180) % 360 - 180

    def align_to(self, target_heading, stop_on_target=False, rate_hz=20):
        '''
        Synchronously sets or updates the target heading and spawns the loop
        task if it is not already running.
        '''
        self._target_heading = target_heading
        self._stop_on_target = stop_on_target
        self._aligned = False

        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop(rate_hz))

    def stop(self):
        '''
        Cancels the active control task and zero-sets rotational velocity.
        '''
        if self._task is not None and not self._task.done():
            self._task.cancel()
            self._task = None
        self._omega = 0.0
        self._aligned = False
        self._update_vector()

    async def _run_loop(self, rate_hz=20):
        self._previous_error = 0.0
        self._integral = 0.0
        self._aligned = False

        interval_ms = int(1000 / rate_hz)
        last_ticks = time.ticks_ms()

        try:
            while self.enabled:
                now_ticks = time.ticks_ms()
                dt = time.ticks_diff(now_ticks, last_ticks) / 1000.0
                last_ticks = now_ticks

                current_heading = self._imu.heading
                error = self._normalize_error(self._target_heading, current_heading)
                abs_error = abs(error)

                # evaluate deadband and hysteresis
                if self._aligned:
                    if abs_error > (self._tolerance + self._hysteresis):
                        self._aligned = False
                else:
                    if abs_error <= self._tolerance:
                        self._aligned = True

                if self._aligned:
                    self._omega = 0.0
                    self._integral = 0.0
                    self._previous_error = 0.0

                    if self._stop_on_target:
                        self._update_vector()
                        self._log.info('target heading reached.')
                        break

                elif self.released:
                    self._integral += error * dt
                    if self._max_integral > 0.0:
                        self._integral = max(-self._max_integral, min(self._max_integral, self._integral))

                    if self._use_gyro_damping:
                        # direct gyro damping (CW negative, CCW positive)
                        gyro_z = self._imu.gyro[2]
                        raw_omega = (self._kp * error) + (self._ki * self._integral) + (self._kd * gyro_z)
                        target_omega = max(-self._max_omega, min(self._max_omega, raw_omega))
                    else:
                        derivative = (error - self._previous_error) / dt if dt > 0 and self._previous_error != 0.0 else 0.0
                        self._previous_error = error
                        raw_omega = (self._kp * error) + (self._ki * self._integral) + (self._kd * derivative)
                        target_omega = max(-self._max_omega, min(self._max_omega, raw_omega))

                    # apply slew rate limiting
                    if self._max_slew > 0.0 and dt > 0.0:
                        max_change = self._max_slew * dt
                        delta = target_omega - self._omega
                        if delta > max_change:
                            self._omega += max_change
                        elif delta < -max_change:
                            self._omega -= max_change
                        else:
                            self._omega = target_omega
                    else:
                        self._omega = target_omega

                    self._log.info('released at {:.2f}°; '.format(current_heading) + Fore.GREEN + 'omega: {:.2f}.'.format(self._omega))
                else:
                    self._omega = 0.0
#                   self._log.debug(Style.DIM + 'suppressed at {:.2f}°; '.format(current_heading) + Fore.GREEN + 'omega: {:.2f}.'.format(self._omega))

                self._update_vector()

                await asyncio.sleep_ms(interval_ms)

        except asyncio.CancelledError:
            self._omega = 0.0
            self._update_vector()
            raise
        finally:
            self._task = None

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
            self.stop()
            if self._motor_controller:
                self._motor_controller.remove_intent_vector(Point.NAME)
            super().disable()
            self._log.info('disabled.')
        else:
            self._log.warn('already disabled.')

#EOF
