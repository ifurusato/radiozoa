#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2021-07-01
# modified: 2026-07-01

import time
from machine import I2C

class BreakoutMatrix11x7:
    '''
    Provides MicroPython support for the Pimoroni 11x7 Matrix display,
    based on the C code.
    '''

    WIDTH  = 11
    HEIGHT = 7
    DEFAULT_I2C_ADDRESS   = 0x75
    ALTERNATE_I2C_ADDRESS = 0x77

    CONFIG_BANK   = 0x0b
    ENABLE_OFFSET = 0x00
    COLOR_OFFSET  = 0x24

    REG_MODE      = 0x00
    REG_FRAME     = 0x01
    REG_SHUTDOWN  = 0x0a
    REG_AUDIOSYNC = 0x06
    REG_BANK      = 0xfd

    MODE_PICTURE  = 0x00

    GAMMA_8BIT = bytes([
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2,
        2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 5,
        5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10,
        10, 11, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 18,
        18, 19, 19, 20, 21, 21, 22, 23, 23, 24, 25, 26, 26, 27, 28, 29,
        30, 31, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44,
        45, 46, 47, 48, 50, 51, 52, 53, 55, 56, 57, 59, 60, 61, 63, 64,
        66, 67, 69, 70, 72, 73, 75, 77, 78, 80, 82, 84, 85, 87, 89, 91,
        93, 95, 97, 99, 101, 103, 105, 107, 109, 111, 114, 116, 118, 120, 123, 125,
        127, 130, 132, 135, 137, 140, 142, 145, 147, 150, 153, 155, 158, 161, 164, 167,
        170, 173, 176, 179, 182, 185, 188, 191, 194, 197, 201, 204, 207, 211, 214, 218,
        221, 225, 228, 232, 235, 239, 243, 246, 250, 254, 255, 255, 255, 255, 255, 255,
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255
    ])

    LOOKUP_TABLE = (
        6, 22, 38, 54, 70, 86, 14, 30, 46, 62, 78,
        5, 21, 37, 53, 69, 85, 13, 29, 45, 61, 77,
        4, 20, 36, 52, 68, 84, 12, 28, 44, 60, 76,
        3, 19, 35, 51, 67, 83, 11, 27, 43, 59, 75,
        2, 18, 34, 50, 66, 82, 10, 26, 42, 58, 74,
        1, 17, 33, 49, 65, 81, 9, 25, 41, 57, 73,
        0, 16, 32, 48, 64, 80, 8, 24, 40, 56, 72
    )

    ENABLE_PATTERN = bytes([
        0b01111111, 0b01111111,
        0b01111111, 0b01111111,
        0b01111111, 0b01111111,
        0b01111111, 0b01111111,
        0b01111111, 0b01111111,
        0b01111111, 0b00000000,
        0b00000000, 0b00000000,
        0b00000000, 0b00000000,
        0b00000000, 0b00000000
    ])

    def __init__(self, i2c, address=DEFAULT_I2C_ADDRESS, brightness=1.0):
        '''
        :param i2c:         I2C bus device
        :param address:     I2C address
        :param brightness:  a value between 0.0 and 1.0 (default 1.0/100%)
        '''
        self.i2c = i2c
        self.address = address
        self.brightness = max(0.0, min(1.0, float(brightness)))
        self.buf = bytearray(145)

    def init(self):
        '''
        Initialise the device.
        '''
        self._write_reg(self.REG_BANK, self.CONFIG_BANK)
        self._write_reg(self.REG_SHUTDOWN, 0b00000000)
        self.clear()
        self.update(0)
        self._write_reg(self.REG_SHUTDOWN, 0b00000001)
        self._write_reg(self.REG_MODE, self.MODE_PICTURE)
        self._write_reg(self.REG_AUDIOSYNC, 0)
        self._write_reg(self.REG_BANK, 0)
        write_buf = bytearray(1 + len(self.ENABLE_PATTERN))
        write_buf[0] = self.ENABLE_OFFSET
        write_buf[1:] = self.ENABLE_PATTERN
        self.i2c.writeto(self.address, write_buf)
        self._write_reg(self.REG_BANK, self.CONFIG_BANK)
        self._write_reg(self.REG_FRAME, 0)
        return True

    def set_brightness(self, brightness):
        '''
        Set the brightness between 0.0 (0%) and 1.0 (100%).
        '''
        self.brightness = max(0.0, min(1.0, float(brightness)))

    def clear(self):
        '''
        Clear the internal buffer. Note that the update() method
        must be called to actually affect the display.
        '''
        for i in range(len(self.buf)):
            self.buf[i] = 0

    def set_pixel(self, x, y, b):
        '''
        Set the specified x,y pixel value to the brightness argument.
        '''
        if x < 0 or x >= self.WIDTH or y < 0 or y >= self.HEIGHT:
            return
        idx = self.LOOKUP_TABLE[y * self.WIDTH + x]
        scaled_b = int(b * self.brightness)
        self.buf[idx + 1] = self.GAMMA_8BIT[scaled_b]

    def update(self, frame=0):
        '''
        Update the display to match the contents of the buffer.
        '''
        self._write_reg(self.REG_BANK, frame)
        self.buf[0] = self.COLOR_OFFSET
        self.i2c.writeto(self.address, self.buf)
        self._write_reg(self.REG_BANK, self.CONFIG_BANK)
        self._write_reg(self.REG_FRAME, frame)

    def _write_reg(self, reg, value):
        self.i2c.writeto_mem(self.address, reg, bytes([value]))

#EOF

