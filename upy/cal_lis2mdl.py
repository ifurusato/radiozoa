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

import sys

# force module reload
for mod in ['icm20948', 'lis2mdl', 'imu', 'cal_lis2mdl']:
    if mod in sys.modules:
        del sys.modules[mod]

from machine import Pin, I2C

from imu import IMU

i2c = I2C(1, scl=38, sda=18, freq=400000)
imu = IMU(i2c)

print('Rotate the robot slowly through a full 360 degrees over the next 20 seconds…')

imu.calibrate()

offset_x, offset_y = imu.offsets
scale_x, scale_y = imu.scales

print('''offset_x: {:7.2f}; offset_y: {:7.2f}'''.format(offset_x, offset_y))
print('''scale_x: {:7.3f}; scale_y: {:7.3f}'''.format(scale_x, scale_y))

#EOF
