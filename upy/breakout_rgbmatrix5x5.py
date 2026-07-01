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

class BreakoutRgbMatrix5x5:
    '''
    Provides MicroPython support for the Pimoroni 5x5 RGB Matrix display,
    based on the C code. Also includes an HSV-to-RGB utility method.
    '''

    WIDTH  = 5
    HEIGHT = 5
    DEFAULT_I2C_ADDRESS   = 0x74
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
        (118, 69, 85), (117, 68, 101), (116, 84, 100), (115, 83, 99), (114, 82, 98),
        (113, 81, 97), (112, 80, 96), (134, 21, 37), (133, 20, 36), (132, 19, 35),
        (131, 18, 34), (130, 17, 50), (129, 33, 49), (128, 32, 48), (127, 47, 63),
        (121, 41, 57), (122, 25, 58), (123, 26, 42), (124, 27, 43), (125, 28, 44),
        (126, 29, 45), (15, 95, 111), (8, 89, 105), (9, 90, 106), (10, 91, 107),
        (11, 92, 108), (12, 76, 109), (13, 77, 93)
    )

    ENABLE_PATTERN = bytes([
        0b00000000, 0b10111111,
        0b00111110, 0b00111110,
        0b00111111, 0b10111110,
        0b00000111, 0b10000110,
        0b00110000, 0b00110000,
        0b00111111, 0b10111110,
        0b00111111, 0b10111110,
        0b01111111, 0b11111110,
        0b01111111, 0b00000000
    ])

    def __init__(self, i2c, address=DEFAULT_I2C_ADDRESS, brightness=1.0):
        '''
        :param i2c:         I2C bus device
        :param address:     I2C address
        :param brightness:  a value between 0.0 and 1.0 (default 1.0/100%)
        '''
        if i2c is None:
            raise TypeException('no I2C device provided.')
        self._i2c = i2c
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
        self._i2c.writeto(self.address, write_buf)
        self._write_reg(self.REG_BANK, self.CONFIG_BANK)
        self._write_reg(self.REG_FRAME, 0)
        return True

    def set_brightness(self, brightness):
        '''
        Set the brightness between 0.0 (0%) and 1.0 (100%).
        Note that altering the brightness may also affect the hue.
        '''
        self.brightness = max(0.0, min(1.0, float(brightness)))

    def clear(self):
        '''
        Clear the internal buffer. Note that the update() method
        must be called to actually affect the display.
        '''
        for i in range(len(self.buf)):
            self.buf[i] = 0

    def set_pixel(self, x, y, r, g, b):
        '''
        Set the specified pixel value to the RGB value.
        '''
        if x < 0 or x >= self.WIDTH or y < 0 or y >= self.HEIGHT:
            return

        # Rotate 90 degrees counterclockwise to correct the physical orientation
        orig_x = x
        x = 4 - y
        y = orig_x

        if y == 1 or y == 3:
            x = 4 - x
        index = x + (y * 5)
        rgb = self.LOOKUP_TABLE[index]
        scaled_r = int(r * self.brightness)
        scaled_g = int(g * self.brightness)
        scaled_b = int(b * self.brightness)
        self.buf[rgb[0] + 1] = self.GAMMA_8BIT[scaled_r]
        self.buf[rgb[1] + 1] = self.GAMMA_8BIT[scaled_g]
        self.buf[rgb[2] + 1] = self.GAMMA_8BIT[scaled_b]

    def set_pixel_180(self, x, y, r, g, b):
        '''
        Set the specified pixel value to the RGB value, rotated
        180 degrees.
        '''
        if x < 0 or x >= self.WIDTH or y < 0 or y >= self.HEIGHT:
            return

        # Rotate 90 degrees clockwise to compensate for 90 CCW physical orientation
        orig_x = x
        x = y
        y = 4 - orig_x

        if y == 1 or y == 3:
            x = 4 - x
        index = x + (y * 5)
        rgb = self.LOOKUP_TABLE[index]
        scaled_r = int(r * self.brightness)
        scaled_g = int(g * self.brightness)
        scaled_b = int(b * self.brightness)
        self.buf[rgb[0] + 1] = self.GAMMA_8BIT[scaled_r]
        self.buf[rgb[1] + 1] = self.GAMMA_8BIT[scaled_g]
        self.buf[rgb[2] + 1] = self.GAMMA_8BIT[scaled_b]

    def set_pixel_90(self, x, y, r, g, b):
        '''
        Set the specified pixel value to the RGB value, rotated
        90 degrees counter-clockwise.
        '''
        if x < 0 or x >= self.WIDTH or y < 0 or y >= self.HEIGHT:
            return
        if y == 1 or y == 3:
            x = 4 - x
        index = x + (y * 5)
        rgb = self.LOOKUP_TABLE[index]
        scaled_r = int(r * self.brightness)
        scaled_g = int(g * self.brightness)
        scaled_b = int(b * self.brightness)
        self.buf[rgb[0] + 1] = self.GAMMA_8BIT[scaled_r]
        self.buf[rgb[1] + 1] = self.GAMMA_8BIT[scaled_g]
        self.buf[rgb[2] + 1] = self.GAMMA_8BIT[scaled_b]

    def show(self):
        '''
        An alias for update().
        '''
        self.update()

    def update(self, frame=0):
        '''
        Update the display to match the contents of the buffer.
        '''
        self._write_reg(self.REG_BANK, frame)
        self.buf[0] = self.COLOR_OFFSET
        self._i2c.writeto(self.address, self.buf)
        self._write_reg(self.REG_BANK, self.CONFIG_BANK)
        self._write_reg(self.REG_FRAME, frame)

    def _write_reg(self, reg, value):
        self._i2c.writeto_mem(self.address, reg, bytes([value]))

    @staticmethod
    def hsv_to_rgb(h, s, v):
        '''
        Convert HSV color space to RGB values.
        h: 0.0 to 360.0, s: 0.0 to 1.0, v: 0.0 to 1.0
        '''
        h_i = int(h / 60.0) % 6
        f = (h / 60.0) - int(h / 60.0)
        p = v * (1.0 - s) 
        q = v * (1.0 - (f * s))
        t = v * (1.0 - ((1.0 - f) * s))
        if h_i == 0:
            r, g, b = v, t, p
        elif h_i == 1:
            r, g, b = q, v, p
        elif h_i == 2:
            r, g, b = p, v, t
        elif h_i == 3:
            r, g, b = p, q, v
        elif h_i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        return int(r * 255), int(g * 255), int(b * 255)

#EOF
