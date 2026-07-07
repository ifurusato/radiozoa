#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2020-03-16
# modified: 2026-07-04: simplified and removed all references to time, for asyncio compatibility

from colors import *
from logger import Logger, Level
from component import Component
from orientation import Orientation
from breakout_rgbmatrix5x5 import BreakoutRgbMatrix5x5

class RgbMatrix(Component):
    NAME = 'rgbmatrix'

    def __init__(self, i2c, enable_port=True, enable_stbd=True, level=Level.INFO):
        Component.__init__(self, RgbMatrix.NAME, suppressed=False, enabled=True)
        self._i2c = i2c
        self._has_port_rgbmatrix = False
        self._has_stbd_rgbmatrix = False
        self._port_rgbmatrix = None
        self._stbd_rgbmatrix = None
        if enable_port:
            self._port_rgbmatrix = BreakoutRgbMatrix5x5(self._i2c, address=0x77)
            self._port_rgbmatrix.init()
            self._log.info('port rgbmatrix at 0x77.')
            self._port_rgbmatrix.set_brightness(0.8)
            self._has_port_rgbmatrix = True
        else:
            self._log.debug('no port rgbmatrix found.')
        if enable_stbd:
            self._stbd_rgbmatrix = BreakoutRgbMatrix5x5(self._i2c, address=0x74)
            self._stbd_rgbmatrix.init()
            self._log.info('starboard rgbmatrix at 0x74.')
            self._stbd_rgbmatrix.set_brightness(0.8)
            self._has_stbd_rgbmatrix = True
        else:
            self._log.debug('no starboard rgbmatrix found.')
        self._log.info('rgbmatrix width,height: {},{}'.format(5, 5))
        self._enable_threading = False
        self._color = COLOR_RED
        self._max_value = 0.0
        self._buf = [[0.0 for _ in range(5)] for _ in range(5)]
        self._colors = [COLOR_GREEN, COLOR_YELLOW_GREEN, COLOR_YELLOW, COLOR_ORANGE, COLOR_RED]
        self._log.info('ready.')

    @property
    def name(self):
        return RgbMatrix.NAME

    @staticmethod
    def hsv_to_rgb(h, s, v):
        """Pure Python alternative to colorsys.hsv_to_rgb."""
        if s == 0.0:
            return v, v, v
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6
        if i == 0:
            return v, t, p
        if i == 1:
            return q, v, p
        if i == 2:
            return p, v, t
        if i == 3:
            return p, q, v
        if i == 4:
            return t, p, v
        if i == 5:
            return v, p, q

    def set_solid_color(self, color):
        self._color = color

    def show(self, orientation=None):
        if orientation is None or orientation is Orientation.PORT or orientation is Orientation.CNTR and self._port_rgbmatrix:
            self._port_rgbmatrix.update()
        if orientation is None or orientation is Orientation.STBD or orientation is Orientation.CNTR:
            self._stbd_rgbmatrix.update()

    def show_color(self, color, orientation):
        self.set_solid_color(color)
        if orientation is Orientation.PORT or orientation is Orientation.CNTR and self._port_rgbmatrix:
            self._set_color(self._port_rgbmatrix, self._color)
        if orientation is Orientation.STBD or orientation is Orientation.CNTR:
            self._set_color(self._stbd_rgbmatrix, self._color)

    def get_rgbmatrix(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_rgbmatrix
        if orientation is Orientation.STBD:
            return self._stbd_rgbmatrix
        return None

    def show_hue(self, hue, orientation):
        rgb = RgbMatrix.hsv_to_rgb(abs(hue), 1.0, 1.0)
        r = int(rgb[0] * 255.0)
        g = int(rgb[1] * 255.0)
        b = int(rgb[2] * 255.0)
        if orientation is Orientation.PORT or orientation is Orientation.CNTR and self._port_rgbmatrix:
            self._port_rgbmatrix.set_all(r, g, b)
            self._port_rgbmatrix.update()
        if orientation is Orientation.STBD or orientation is Orientation.CNTR:
            self._stbd_rgbmatrix.set_all(r, g, b)
            self._stbd_rgbmatrix.update()

    def set_color(self, color, show=True):
        if self._port_rgbmatrix:
            self._set_color(self._port_rgbmatrix, color, show)
        if self._stbd_rgbmatrix:
            self._set_color(self._stbd_rgbmatrix, color, show)

    @staticmethod
    def set_all(rgbmatrix5x5, red, green, blue, show=True):
        for y in range(5):
            for x in range(5):
                rgbmatrix5x5.set_pixel(x, y, red, green, blue)
        if show:
            rgbmatrix5x5.update()

    def set_rgb_color(self, rgbmatrix5x5, red, green, blue, show=True):
        rgbmatrix5x5.set_all(red, green, blue)
        if show:
            rgbmatrix5x5.update()

    def _set_color(self, rgbmatrix5x5, color, show=True):
        for y in range(5):
            for x in range(5):
                rgbmatrix5x5.set_pixel(x, y, color.red, color.green, color.blue)
        if show:
            rgbmatrix5x5.update()

    def clear_all(self):
        self.clear(Orientation.CNTR)

    def clear(self, orientation, show=True):
        if self._port_rgbmatrix and (orientation is Orientation.PORT or orientation is Orientation.CNTR):
            self._clear(self._port_rgbmatrix, show)
        if self._stbd_rgbmatrix and (orientation is Orientation.STBD or orientation is Orientation.CNTR):
            self._clear(self._stbd_rgbmatrix, show)

    def _clear(self, rgbmatrix5x5, show=True):
        self._set_color(rgbmatrix5x5, COLOR_BLACK, show)

#EOR
