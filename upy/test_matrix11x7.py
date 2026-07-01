#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-07-01
# modified: 2026-07-01

import sys
import time
from machine import Pin, I2C
from breakout_matrix11x7 import BreakoutMatrix11x7

# force module reload
for mod in ['test_matrix11x7']:
    if mod in sys.modules:
        del sys.modules[mod]

print('configuring I2C bus…')
i2c_bus = I2C(1, scl=38, sda=18, freq=400_000)

# instantiate and configure the 11x7 matrix driver object
matrix = BreakoutMatrix11x7(i2c_bus, address=0x77, brightness=0.3)
if not matrix.init():
    print("failed to initialize the 11x7 matrix.")
    raise SystemExit

print("matrix initialized successfully. running static layout test...")
# 1. draw a bounding border around the frame edges
for x in range(matrix.WIDTH):
    matrix.set_pixel(x, 0, 128)                  # Top edge
    matrix.set_pixel(x, matrix.HEIGHT - 1, 128)  # Bottom edge

for y in range(matrix.HEIGHT):
    matrix.set_pixel(0, y, 128)                 # Left edge
    matrix.set_pixel(matrix.WIDTH - 1, y, 128)  # Right edge

# 2. light up the center coordinate at full brightness
matrix.set_pixel(5, 3, 255)
matrix.update()

time.sleep(2.0)
matrix.clear()
matrix.update()

print("running coordinate animation sweep loop. Press Ctrl+C to stop.")
# 3. continuous sweep cycle over every individual pixel coordinate
try:
    while True:
        for y in range(matrix.HEIGHT):
            for x in range(matrix.WIDTH):
                matrix.clear()
                matrix.set_pixel(x, y, 255)
                matrix.update()
                time.sleep(0.05)

except KeyboardInterrupt:
    print('Ctrl-C caught, exiting…')
finally:
    matrix.clear()
    matrix.update()

#EOF
