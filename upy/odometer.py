#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-08-22
# modified: 2026-08-22
#
# Odometer for a two-wheel differential drive robot.
#
# This class provides robot-level velocity and odometry calculation from the
# step counts of the two drive motors. It tracks changes in step counts and
# computes:
#
#  - instantaneous lateral (vx), longitudinal (vy), and rotational (omega)
#    velocity,
#  - cumulative pose: (x, y, theta) displacement of the robot since
#    initialisation or last reset.
#
# vx is always 0.0 for a differential drive robot (no lateral motion).
#
# Robot body frame convention:
#   X: port-starboard (lateral), starboard positive
#   Y: forward-backward (longitudinal), forward positive
#
# All distances and positions are in millimetres.
#
# Usage:
#
#   odom = Odometer(config, motor_controller)
#   odom.update(timestamp) # call from MotorController._tick()
#   vx, vy, omega = odom.velocity
#   x, y, theta = odom.pose
#   odom.add_callback(distance_mm, direction, callback)
#   odom.reset()
#
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

import time
import math
from colorama import Fore, Style

from logger import Logger, Level
from component import Component
from orientation import Orientation
from direction import AHEAD, ASTERN

class Odometer(Component):
    NAME = 'odometer'
    '''
    Computes robot velocity and pose (odometry) from the step counts of the
    two drive motors on a differential drive robot.

    Robot body frame convention:
      X: port-starboard (lateral), starboard positive
      Y: forward-backward (longitudinal), forward positive

    vx is always 0.0 for a differential drive robot.
    All distances and positions are in millimetres.

    - update():    call from MotorController._tick() with the current timestamp
                   (seconds, e.g. time.ticks_ms() / 1000.0).
    - velocity:    returns (vx, vy, omega) where vx = 0.0, vy = longitudinal mm/s,
                   omega = rad/s.
    - pose:        returns (x, y, theta) where x = lateral mm,
                   y = longitudinal mm, theta = heading in radians.
    - add_callback(distance_mm, direction, callback):
                   registers a one-shot callback to fire when the robot has
                   traveled at least distance_mm in the given direction
                   (AHEAD or ASTERN) from the point of registration.
    - reset():     resets cumulative pose and previous readings to (0, 0, 0).
    '''
    def __init__(self, config, motor_controller, level=Level.INFO):
        Component.__init__(self, Odometer.NAME, suppressed=False, enabled=True, level=level)
        self._motor_controller = motor_controller
        _cfg = config['rros']['odometer']
        self._verbose        = _cfg['verbose']
        self._wheel_track_mm = _cfg['wheel_track_mm']
        self._pose_delta_mm  = _cfg['pose_delta_mm']
        # geometry from motor
        _motor_port = motor_controller.get_motor(Orientation.PORT)
        self._mm_per_tick    = _motor_port.mm_per_tick
        self._log.info('wheel track: {:5.1f}mm'.format(self._wheel_track_mm))
        self._log.info('mm per tick: {:8.5f}mm'.format(self._mm_per_tick))
        # callbacks: list of dicts with keys: distance_mm, direction, callback, x0, y0
        self._callbacks      = []
        # pose logging threshold
        self._last_printed_x = 0.0
        self._last_printed_y = 0.0
        # internal state
        self._last_steps_port = None
        self._last_steps_stbd = None
        self._last_time       = None
        self._x               = 0.0   # lateral position (mm)
        self._y               = 0.0   # longitudinal position (mm)
        self._theta           = 0.0   # heading (radians)
        self._vx              = 0.0   # lateral velocity (mm/s), always 0.0
        self._vy              = 0.0   # longitudinal velocity (mm/s)
        self._omega           = 0.0   # yaw rate (rad/s)
        self._log.info('ready.')

    @property
    def pose(self):
        '''
        Returns (x, y, theta): x (lateral mm), y (longitudinal mm), theta (radians).
        '''
        return self._x, self._y, self._theta

    @property
    def velocity(self):
        '''
        Returns (vx, vy, omega): vx (always 0.0), vy (longitudinal mm/s), omega (rad/s).
        '''
        return self._vx, self._vy, self._omega

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def add_callback(self, distance_mm, direction, callback):
        '''
        Registers a one-shot callback to fire when the robot has traveled at
        least distance_mm from the point of registration, in the given direction.

        direction must be AHEAD or ASTERN. Multiple callbacks may be registered
        simultaneously. Each fires once and is then removed.

        :param distance_mm:  threshold distance in mm from registration point
        :param direction:    AHEAD or ASTERN
        :param callback:     callable, no arguments
        '''
        if direction is not AHEAD and direction is not ASTERN:
            raise ValueError('direction must be AHEAD or ASTERN.')
        if not callable(callback):
            raise TypeError('callback argument is not callable.')
        self._callbacks.append({
            'distance_mm': distance_mm,
            'direction':   direction,
            'callback':    callback,
            'x0':          self._x,
            'y0':          self._y,
        })
        self._log.info('added callback: {:.1f}mm {}'.format(distance_mm, direction.name))

    def remove_callback(self, callback):
        '''
        Removes a registered callback by reference.
        '''
        self._callbacks = [e for e in self._callbacks if e['callback'] is not callback]

    def _check_callbacks(self):
        '''
        Checks all registered callbacks against the current pose and fires any
        whose distance threshold and direction condition are met. Fired callbacks
        are removed.
        '''
        if not self._callbacks:
            return
        _fired = []
        for entry in self._callbacks:
            _dx   = self._x - entry['x0']
            _dy   = self._y - entry['y0']
            _dist = math.sqrt(_dx * _dx + _dy * _dy)
            if _dist >= entry['distance_mm']:
                if entry['direction'] is AHEAD and _dy >= 0.0:
                    _fired.append(entry)
                elif entry['direction'] is ASTERN and _dy <= 0.0:
                    _fired.append(entry)
        for entry in _fired:
            self._callbacks.remove(entry)
            self._log.info('callback fired: {:.1f}mm {}'.format(
                    entry['distance_mm'], entry['direction'].name))
            entry['callback']()

    def update(self, timestamp_ms):
        '''
        Call at each MotorController tick with the current time in milliseconds.
        Reads step counts directly from the motor controller's motors.

        :param timestamp_ms:  time in milliseconds (e.g. time.ticks_ms())
        '''
        if not self.enabled:
            return
        _steps_port = self._motor_controller._motor_port.steps
        _steps_stbd = self._motor_controller._motor_stbd.steps
        if self._last_steps_port is not None and self._last_time is not None:
            _dt_ms = time.ticks_diff(timestamp_ms, self._last_time)
            if _dt_ms <= 0:
                self._last_steps_port = _steps_port
                self._last_steps_stbd = _steps_stbd
                self._last_time       = timestamp_ms
                return
            _dt      = _dt_ms / 1000.0
            # step deltas
            _ds_port = _steps_port - self._last_steps_port
            _ds_stbd = _steps_stbd - self._last_steps_stbd
            # convert to distances in mm
            _d_port  = _ds_port * self._mm_per_tick
            _d_stbd  = _ds_stbd * self._mm_per_tick
            # differential drive kinematics
            _d_center = (_d_port + _d_stbd) / 2.0
            _dtheta   = (_d_port - _d_stbd) / self._wheel_track_mm
            # velocities in robot body frame
            self._vx    = 0.0
            self._vy    = _d_center / _dt
            self._omega = _dtheta   / _dt
            # integrate pose
            _cos_t = math.cos(self._theta)
            _sin_t = math.sin(self._theta)
            _dx    = -_d_center * _sin_t
            _dy    = _d_center * _cos_t
            self._x     += _dx
            self._y     += _dy
            self._theta += _dtheta
            # normalise theta to [-π, π]
            while self._theta > math.pi:
                self._theta -= 2.0 * math.pi
            while self._theta < -math.pi:
                self._theta += 2.0 * math.pi
            self._check_callbacks()
            self._print_pose_if_due()
        self._last_steps_port = _steps_port
        self._last_steps_stbd = _steps_stbd
        self._last_time       = timestamp_ms

    def _print_pose_if_due(self):
        '''
        Logs the current pose if the robot has moved at least pose_delta_mm
        since the last log.
        '''
        _dx = self._x - self._last_printed_x
        _dy = self._y - self._last_printed_y
        if (_dx * _dx + _dy * _dy) >= (self._pose_delta_mm * self._pose_delta_mm):
            self._last_printed_x = self._x
            self._last_printed_y = self._y
            _deg    = math.degrees(self._theta)
            _rad_pi = self._theta / math.pi
            if self._verbose:
                self._log.info('pose: '
                        + Fore.CYAN  + 'x: '     + Fore.YELLOW + '{:7.2f}mm; '.format(self._x)
                        + Fore.CYAN  + 'y: '     + Fore.YELLOW + '{:7.2f}mm; '.format(self._y)
                        + Fore.CYAN  + 'theta: ' + Fore.YELLOW + '{:.3f}π ({:.1f}°)'.format(_rad_pi, _deg))
                self._log.info('velocity: '
                        + Fore.CYAN  + 'vy: '    + Fore.YELLOW + '{:7.2f}mm/s; '.format(self._vy)
                        + Fore.CYAN  + 'omega: ' + Fore.YELLOW + '{:7.4f}rad/s'.format(self._omega))

    def reset(self):
        '''
        Resets the odometer: clears cumulative pose, velocities, step state,
        and all registered callbacks.
        '''
        self._last_steps_port = None
        self._last_steps_stbd = None
        self._last_time       = None
        self._x               = 0.0
        self._y               = 0.0
        self._theta           = 0.0
        self._vx              = 0.0
        self._vy              = 0.0
        self._omega           = 0.0
        self._last_printed_x  = 0.0
        self._last_printed_y  = 0.0
        self._callbacks       = []
        self._log.info('odometry reset.')

    def enable(self):
        if not self.enabled:
            super().enable()
            self._log.info('enabled.')
        else:
            self._log.warn('already enabled.')

    def disable(self):
        if self.enabled:
            super().disable()
            self._log.info('disabled.')
        else:
            self._log.warn('already disabled.')

    def close(self):
        if not self.closed:
            super().close()
            self._log.info('closed.')
        else:
            self._log.warn('already closed.')

#EOF
