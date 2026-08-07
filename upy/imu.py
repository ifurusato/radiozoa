#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-08-06
# modified: 2026-08-06

import time
from math import degrees, atan2, asin, sqrt, sin, cos, radians

import icm20948
import lis2mdl

from component import Component
from logger import Logger, Level

class IMU(Component):
    NAME = 'imu'
    LIS2MDL_I2C_ADDRESS  = 0x1E
    ICM20948_I2C_ADDRESS = 0x69
    '''
    Combines pitch and roll from the ICM20948 via its Digital Motion Processor (DMP) 
    ROTATION_VECTOR virtual sensor, with a heading value from the LIS2MDL magnetometer.
    '''
    def __init__(self, config, i2c, level=Level.INFO):
        Component.__init__(self, IMU.NAME, suppressed=False, enabled=False, level=level)
        _icm_debug = 0
        self._icm = icm20948.ICM20948(i2c, dmp=True, debug=_icm_debug)
        if self._icm.dmp_ready:
            self._icm.DMP_enable_sensor("ROTATION_VECTOR", True)
            self._icm.DMP_enable_sensor("MAGNETIC_FIELD_UNCALIBRATED", True)
        self._lis = lis2mdl.LIS2MDL(i2c)
        _cfg = config['rros']['imu']
        self._heading_trim = _cfg['heading_trim'] # offset to north
        self._offset_x     = _cfg['offset_x'] # X orientation offset
        self._offset_y     = _cfg['offset_y'] # Y orientation offset
        self._scale_x      = _cfg['scale_x']  # offset oval X axis
        self._scale_y      = _cfg['scale_y']  # offset oval Y axis
        self._pitch = 0.0
        self._roll  = 0.0
        self._log.info('ready.')

    @property
    def pitch(self):
        '''
        Pitch in degrees.
        '''
        self._update_pitch_roll()
        return self._pitch

    @property
    def roll(self):
        '''
        Roll in degrees.
        Port down is negative, starboard down is positive.
        '''
        self._update_pitch_roll()
        return self._roll

    @property
    def heading(self):
        '''
        Heading in degrees (0-360).
        '''
        return self._compute_heading()

    @property
    def heading_tilt_compensated(self):
        '''
        Heading in degrees (0-360), tilt compensated using pitch and roll
        from the ICM20948.
        '''
        return self._compute_heading_tilt_compensated()

    @property
    def heading_pitch_roll(self, tilt_compensated=True):
        '''
        Returns a tuple of (heading, pitch, roll) in degrees, obtained
        in a single call. Default is tilt compensation.
        '''
        heading = self._compute_heading_tilt_compensated() if tilt_compensated else self._compute_heading() 
        self._update_pitch_roll()
        return heading, self._pitch, self._roll

    @property
    def heading_trim(self):
        '''
        The heading trim value in degrees, added to the raw computed heading.
        Used to align the reported heading with true or magnetic north.
        '''
        return self._heading_trim

    @heading_trim.setter
    def heading_trim(self, value):
        self._heading_trim = value

    @property
    def offsets(self):
        '''
        The current (offset_x, offset_y) hard-iron calibration values.
        '''
        return self._offset_x, self._offset_y

    @property
    def scales(self):
        '''
        The current (scale_x, scale_y) soft-iron calibration values.
        '''
        return self._scale_x, self._scale_y

    def _update_pitch_roll(self):
        self._icm.DMP_fifo_proceed()
        q1, q2, q3 = self._icm._quat9
        q0_sq = 1.0 - (q1 * q1 + q2 * q2 + q3 * q3)
        q0 = sqrt(q0_sq) if q0_sq > 0 else 0.0
        self._pitch = -degrees(-asin(2.0 * (q1 * q3 - q0 * q2)))
        self._roll  = degrees(atan2(2.0 * (q0 * q1 + q2 * q3), q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3))

    def _compute_heading_tilt_compensated(self):
        x, y, z = self._lis.magnetic
        cx = (x - self._offset_x) * self._scale_x
        cy = (y - self._offset_y) * self._scale_y
        cz = z
        self._update_pitch_roll()
        pitch_rad = radians(self._pitch)
        roll_rad = radians(self._roll)
        xh = cx * cos(pitch_rad) + cz * sin(pitch_rad)
        yh = (cx * sin(roll_rad) * sin(pitch_rad) + cy * cos(roll_rad)
              - cz * sin(roll_rad) * cos(pitch_rad))
        # negated as atan2 increases counter-clockwise, heading increases clockwise
        heading = self._heading_trim - degrees(atan2(yh, xh))
        if heading < 0:
            heading += 360
        elif heading >= 360:
            heading -= 360
        return heading

    def _compute_heading(self):
        x, y, z = self._lis.magnetic
        cx = (x - self._offset_x) * self._scale_x
        cy = (y - self._offset_y) * self._scale_y
        # negated as atan2 increases counter-clockwise, heading increases clockwise
        heading = self._heading_trim - degrees(atan2(cy, cx))
        if heading < 0:
            heading += 360
        elif heading >= 360:
            heading -= 360
        return heading

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def calibrate(self, callback=None, duration_ms=20000, sample_ms=100):
        '''
        Samples the magnetometer while the robot rotates in place through a full
        360°, then computes and stores the hard-iron offsets and soft-iron scale
        factors. The caller is responsible for rotating the robot during this
        call. The callback, if provided, is invoked with no arguments once
        calibration completes, signaling that rotation can stop.
        '''
        x0, y0, z0 = self._lis.magnetic
        min_x = max_x = x0
        min_y = max_y = y0

        elapsed_ms = 0
        while elapsed_ms < duration_ms:
            x, y, z = self._lis.magnetic
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            time.sleep_ms(sample_ms)
            elapsed_ms += sample_ms

        self._offset_x = (max_x + min_x) / 2
        self._offset_y = (max_y + min_y) / 2

        range_x = (max_x - min_x) / 2
        range_y = (max_y - min_y) / 2
        avg_range = (range_x + range_y) / 2
        self._scale_x = avg_range / range_x if range_x != 0 else 1.0
        self._scale_y = avg_range / range_y if range_y != 0 else 1.0

        if callback:
            callback()

#EOF
