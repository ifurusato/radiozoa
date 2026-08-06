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
#
# Align the robot's heading with true/magnetic north (using a compass),
# then note the printed raw heading value. that value is the heading_trim to
# use in configuration of the IMU so that heading reads 0 when pointing north.

import sys

# force module reload
for mod in ['icm20948', 'lis2mdl', 'imu', 'find_heading_trim']:
    if mod in sys.modules:
        del sys.modules[mod]

from machine import Pin, I2C
from utime import sleep_ms

from imu import IMU

i2c = I2C(1, scl=38, sda=18, freq=400000)

# fill these in from cal_lis2mdl.py output; heading_trim not yet applied
imu = IMU(i2c)

print('Align the robot to north using a compass, then read the raw heading below…')

while True:
    heading = imu.heading
    print('''raw heading: {:7.3f}; suggested heading_trim: {:7.3f}'''.format(heading, heading))
    sleep_ms(250)

#EOF
