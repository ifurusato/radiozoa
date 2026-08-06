#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2026-06-23
# modified: 2026-06-23

from machine import Pin, I2C
from utime import sleep_ms

import lis2mdl

i2c = I2C(1, scl=38, sda=18, freq=400000)
lis = lis2mdl.LIS2MDL(i2c)

print('Rotate the robot slowly through a full 360 degrees over the next 20 seconds…')

min_x = min_y = 9999.0
max_x = max_y = -9999.0

for _ in range(200):
    x, y, z = lis.magnetic
    min_x = min(min_x, x)
    max_x = max(max_x, x)
    min_y = min(min_y, y)
    max_y = max(max_y, y)
    sleep_ms(100)

offset_x = (max_x + min_x) / 2
offset_y = (max_y + min_y) / 2

print('''min_x: {:7.2f}; max_x: {:7.2f}'''.format(min_x, max_x))
print('''min_y: {:7.2f}; max_y: {:7.2f}'''.format(min_y, max_y))
print('''offset_x: {:7.2f}; offset_y: {:7.2f}'''.format(offset_x, offset_y))

#EOF
