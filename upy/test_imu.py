#!/micropython
# -*- coding: utf-8 -*-
#
# note: port down is negative roll, starboard down is positive roll

import sys

# force module reload
for mod in ['icm20948', 'test_imu']:
    if mod in sys.modules:
        del sys.modules[mod]

from machine import Pin, I2C
from math import degrees, atan2, asin, sqrt
from utime import sleep_ms

import icm20948

i2c = I2C(1, scl=38, sda=18, freq=400000)
imu = icm20948.ICM20948(i2c, dmp=True, debug=0)

if imu.dmp_ready:
    imu.DMP_enable_sensor("ROTATION_VECTOR", True)

def quat_to_euler(q123, north_angle=0):
    '''
    Convert a 3-component DMP quaternion (q1, q2, q3) to heading, pitch, roll in degrees.
    q0 (w) is reconstructed from the unit-quaternion constraint.
    '''
    q1, q2, q3 = q123
    q0_sq = 1.0 - (q1 * q1 + q2 * q2 + q3 * q3)
    q0 = sqrt(q0_sq) if q0_sq > 0 else 0.0
    pitch   = -degrees(-asin(2.0 * (q1 * q3 - q0 * q2)))
    roll    = degrees(atan2(2.0 * (q0 * q1 + q2 * q3), q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3))
    heading = north_angle + degrees(atan2(2.0 * (q1 * q2 + q0 * q3), q0 * q0 + q1 * q1 - q2 * q2 - q3 * q3))
    if heading < 0:
        heading += 360
    return heading, pitch, roll

while True:
    imu.DMP_fifo_proceed()
    heading, pitch, roll = quat_to_euler(imu._quat9)
    print('''heading: {:7.3f}; pitch: {:7.3f}; roll: {:7.3f}'''.format(heading, pitch, roll))
    sleep_ms(250)

#EOF
