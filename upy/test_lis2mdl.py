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

from machine import Pin, I2C
from math import atan2, degrees
import time

import lis2mdl

i2c = I2C(1, scl=38, sda=18, freq=400000)
lis = lis2mdl.LIS2MDL(i2c)

# fill these in from cal_lis2mdl.py output
OFFSET_X = 26.78
OFFSET_Y = -22.95

while True:
    x, y, z = lis.magnetic
    heading = degrees(atan2(y - OFFSET_Y, x - OFFSET_X))
    if heading < 0:
        heading += 360
    print('''heading: {:7.3f}'''.format(heading))
    time.sleep_ms(100)

#EOF
