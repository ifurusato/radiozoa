# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

import time
from machine import Pin, I2C
import lis2mdl

i2c = I2C(1, scl=38, sda=18, freq=400000)
lis = lis2mdl.LIS2MDL(i2c)

while True:
    mag_x, mag_y, mag_z = lis.magnetic
    print(f"X:{mag_x:.2f}, Y:{mag_y:.2f}, Z:{mag_z:.2f} uT")
    print()
    time.sleep(1)

