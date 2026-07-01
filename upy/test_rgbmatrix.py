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

import time
from machine import I2C, Pin
from breakout_rgbmatrix5x5 import BreakoutRgbMatrix5x5

try:

    # configuring I2C bus…
    i2c_bus = I2C(1, scl=38, sda=18, freq=400_000)

    # instantiate the matrix with 30% dimming level
    matrix = BreakoutRgbMatrix5x5(i2c_bus, brightness=0.3)
    if not matrix.init():
        print("failed to initialize the 11x7 matrix.")
        raise SystemExit

    print("starting 5x5 Matrix color bands test…")
    for _ in range(5):
        for x in range(matrix.WIDTH):
            for y in range(matrix.HEIGHT):
                if y == 0 or y == 1:
                    # top rows: Red
                    matrix.set_pixel(x, y, 255, 0, 0)
                elif y == 2:
                    # middle row: Green
                    matrix.set_pixel(x, y, 0, 255, 0)
                else:
                    # bottom rows: Blue
                    matrix.set_pixel(x, y, 0, 0, 255)
        matrix.update()
        time.sleep(0.1)

    print("starting 5x5 Matrix rainbow cycle test…")
    hue_offset = 0.0
    while True:
        for x in range(matrix.WIDTH):
            for y in range(matrix.HEIGHT):
                # Calculate a diagonal hue spatial distribution across the grid
                pixel_hue = (hue_offset + (x + y) * 35.0) % 360.0
                r, g, b = BreakoutRgbMatrix5x5.hsv_to_rgb(pixel_hue, 1.0, 1.0)
                matrix.set_pixel(x, y, r, g, b)
        matrix.update()
        # advance the color wheel transition and match frame timing pace
        hue_offset = (hue_offset + 4.0) % 360.0
        time.sleep(0.03)

except KeyboardInterrupt:
    print('Ctrl-C caught, exiting…')
finally:
    matrix.clear()
    matrix.update()

#EOF
