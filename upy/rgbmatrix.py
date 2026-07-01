#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2020-03-16
# modified: 2026-07-01

import sys
import time
import math
import random

from colors import *
from logger import Logger, Level
from component import Component
from orientation import Orientation
from breakout_rgbmatrix5x5 import BreakoutRgbMatrix5x5

class DisplayType:
    BLINKY     = 1
    DARK       = 3
    RAINBOW    = 4
    RANDOM     = 5
    SCAN       = 6
    SWORL      = 7
    SOLID      = 8
    WIPE_UP    = 9
    WIPE_DOWN  = 10
    WIPE_LEFT  = 11
    WIPE_RIGHT = 12

class WipeDirection:
    LEFT  = 0
    RIGHT = 1
    UP    = 2
    DOWN  = 3

class Ranger:
    def __init__(self, in_min, in_max, out_min, out_max):
        self.in_min = in_min
        self.in_max = in_max
        self.out_min = out_min
        self.out_max = out_max

    def convert(self, value):
        span_in = self.in_max - self.in_min
        span_out = self.out_max - self.out_min
        scaled = float(value - self.in_min) / float(span_in)
        return int(self.out_min + (scaled * span_out))

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
        self._display_type = DisplayType.DARK
        self._percent_to_column = Ranger(0, 100, 0, 9)
        self._random_delay_sec = 0.05
        self._wipe_color = COLOR_CORAL
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

    @staticmethod
    def make_gaussian(fwhm):
        """Replaces numpy spatial calculations with plain mathematical lists."""
        gauss = [[0.0 for _ in range(5)] for _ in range(5)]
        x0, y0 = 2, 2
        ln2 = 0.6931471805599453
        for y in range(5):
            for x in range(5):
                gauss[x][y] = math.exp(-4 * ln2 * ((x - x0) ** 2 + (y - y0) ** 2) / (fwhm ** 2))
        return gauss

    def _set_graph(self, rgbmatrix5x5, values, low=None, high=None, x=0, y=0):
        _width = 4
        _height = 5
        if low is None:
            low = min(values)
        if high is None:
            high = max(values)
        span = high - low
        for p_y in range(0, _height):
            try:
                _value = values[p_y]
                _value -= low
                if span != 0:
                    _value /= float(span)
                _value *= _width * 10.0
                _value = min(_value, _height * 12.0)
                _value = max(_value, 0.0)
                if _value > 5.0:
                    _value = 50.0
                for p_x in range(0, _width):
                    _r = self._colors[p_x].red
                    _g = self._colors[p_x].green
                    _b = self._colors[p_x].blue
                    if _value <= 10.0:
                        _r = int((_value / 10.0) * _r)
                        _g = int((_value / 10.0) * _g)
                        _b = int((_value / 10.0) * _b)
                    _x = x + (_width - p_x)
                    _y = y + p_y
                    rgbmatrix5x5.set_pixel(_x, _y, _r, _g, _b)
                    _value -= 10.0
                    if _value < 0.0:
                        _value = 0.0
            except IndexError:
                return

    def _rainbow(self, rgbmatrix5x5, arg, is_enabled):
        self._log.info('starting rainbow…')
        _spacing = 360.0 / 5.0
        while is_enabled():
            for x in range(5):
                for y in range(5):
                    _hue = int(time.time() * 100) % 360
                    offset = (x * y) / 25.0 * _spacing
                    h = ((_hue + offset) % 360) / 360.0
                    r, g, b = [int(c * 255) for c in RgbMatrix.hsv_to_rgb(h, 1.0, 1.0)]
                    rgbmatrix5x5.set_pixel(x, y, r, g, b)
                if not is_enabled():
                    break
            rgbmatrix5x5.update()
            time.sleep(0.01)
        self._clear(rgbmatrix5x5)
        self._log.info('rainbow ended.')

    def _sworl(self, rgbmatrix5x5, arg, is_enabled):
        self._log.info('starting sworl…')
        try:
            for r in range(0, 10, 1):
                self.set_all(rgbmatrix5x5, r, 0, 0, show=True)
                time.sleep(0.003)
            for i in range(0, 5):
                for r in range(10, 250, 10):
                    _blue = r - 128 if r > 128 else 0
                    self.set_all(rgbmatrix5x5, r, _blue, 0, show=True)
                    time.sleep(0.01)
                if not is_enabled():
                    break
                for r in range(250, 10, -10):
                    _blue = r - 128 if r > 128 else 0
                    self.set_all(rgbmatrix5x5, r, _blue, 0, show=True)
                    time.sleep(0.01)
                if not is_enabled():
                    break
            self._log.info('sworl ended.')
        except KeyboardInterrupt:
            self._log.info('sworl interrupted.')
        finally:
            self.set_color(COLOR_BLACK)

    def _wipe(self, rgbmatrix5x5, direction, is_enabled):
        if direction is WipeDirection.LEFT or direction is WipeDirection.RIGHT:
            self._wipe_horizontal(rgbmatrix5x5, direction, is_enabled)
        if direction is WipeDirection.UP or direction is WipeDirection.DOWN:
            self._wipe_vertical(rgbmatrix5x5, direction, is_enabled)

    def _wipe_horizontal(self, rgbmatrix5x5, direction, is_enabled):
        raise NotImplementedError()

    def set_wipe_color(self, color):
        self._wipe_color = color

    def _wipe_vertical(self, rgbmatrix, direction, is_enabled):
        if not rgbmatrix:
            self._log.debug('null RGB matrix argument.')
            return
        if direction is WipeDirection.DOWN:
            xra = [[0, 5, 1], [4, -1, -1]]
            yra = [[0, 5, 1], [4, -1, -1]]
            self._log.info('starting wipe DOWN…')
        elif direction is WipeDirection.UP:
            xra = [[4, -1, -1], [0, 5, 1]]
            yra = [[4, -1, -1], [0, 5, 1]]
            self._log.info('starting wipe UP…')
        else:
            raise ValueError('unrecognised direction argument.')
        _delay = 0.05
        self.set_color(COLOR_BLACK)
        time.sleep(0.1)
        colors = [self._wipe_color, COLOR_BLACK]
        try:
            for i in range(0, 2, 1):
                xr = xra[i]
                yr = yra[i]
                r, g, b = colors[i].rgb
                for x in range(xr[0], xr[1], xr[2]):
                    for y in range(yr[0], yr[1], yr[2]):
                        rgbmatrix.set_pixel(x, y, r, g, b)
                    rgbmatrix.update()
                    time.sleep(_delay)
                if not is_enabled():
                    break
            self._log.info('wipe ended.')
        except KeyboardInterrupt:
            self._log.info('wipe interrupted.')
        finally:
            self.set_color(COLOR_BLACK)

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

    def _solid(self, rgbmatrix5x5, arg, is_enabled):
        if self._port_rgbmatrix:
            self._set_color(self._port_rgbmatrix, self._color)
        if self._stbd_rgbmatrix:
            self._set_color(self._stbd_rgbmatrix, self._color)
        self._log.info('starting solid color to {}…'.format(str.lower(self._color.name)))
        while is_enabled():
            time.sleep(0.2)

    def _dark(self, rgbmatrix5x5, arg, is_enabled):
        self._log.info('starting dark…')
        self.set_color(COLOR_BLACK)
        while is_enabled():
            time.sleep(0.2)

    def percent(self, value):
        self.column(self._percent_to_column.convert(value))

    def column(self, col):
        if col < 5:
            if self._port_rgbmatrix:
                self.clear(Orientation.PORT, False)
            if self._stbd_rgbmatrix:
                self._column(Orientation.STBD, col, blank=True)
        else:
            if self._stbd_rgbmatrix:
                self.clear(Orientation.STBD, False)
            if self._port_rgbmatrix:
                self._column(Orientation.PORT, col - 5, blank=True)
        if self._stbd_rgbmatrix:
            self._stbd_rgbmatrix.update()
        if self._port_rgbmatrix:
            self._port_rgbmatrix.update()

    def _column(self, orientation, col, blank=True):
        _rgbmatrix = self._port_rgbmatrix if orientation is Orientation.PORT else self._stbd_rgbmatrix
        if not _rgbmatrix:
            return
        if col < 0 or col > 10:
            raise ValueError('column argument \'{:d}\' out of range (0-10)'.format(col))
        _color = COLOR_RED if orientation is Orientation.PORT else COLOR_GREEN
        _rgbmatrix.set_brightness(1.0)
        if blank:
            self.clear(orientation, False)
        x = col
        rows = 5
        for y in range(0, rows):
            _rgbmatrix.set_pixel(y, x, _color.red, _color.green, _color.blue)
        _rgbmatrix.update()

    def _blinky(self, rgbmatrix5x5, arg, is_enabled):
        self._log.info('starting blinky…')
        while is_enabled():
            for z in list(range(1, 10)[::-1]) + list(range(1, 10)):
                fwhm = 5.0 / z
                gauss = RgbMatrix.make_gaussian(fwhm)
                start = time.time()
                for y in range(5):
                    for x in range(5):
                        h = 0.5
                        s = 0.8
                        v = gauss[x][y]
                        rgb = RgbMatrix.hsv_to_rgb(h, s, v)
                        r = int(rgb[0] * 255.0)
                        g = int(rgb[1] * 255.0)
                        b = int(rgb[2] * 255.0)
                        rgbmatrix5x5.set_pixel(x, y, r, g, b)
                rgbmatrix5x5.update()
                t = time.time() - start
                if t < 0.04:
                    time.sleep(0.04 - t)
            if not is_enabled():
                break
        self._clear(rgbmatrix5x5)
        self._log.info('blinky ended.')

    def _scan(self, rgbmatrix5x5, arg, is_enabled):
        self._log.info('starting scan…')
        r, g, b = 255, 64, 0
        x = 2
        _delay = 0.25
        while is_enabled():
            for y in range(0, 5):
                rgbmatrix5x5.clear()
                rgbmatrix5x5.set_pixel(x, y, r, g, b)
                rgbmatrix5x5.update()
                time.sleep(_delay)
            for y in range(4, 0, -1):
                rgbmatrix5x5.clear()
                rgbmatrix5x5.set_pixel(x, y, r, g, b)
                rgbmatrix5x5.update()
                time.sleep(_delay)
            if not is_enabled():
                break
        self._clear(rgbmatrix5x5)
        self._log.debug('scan ended.')

    def random_update(self):
        rand_hue = random.random() * 0.8 + 0.1
        for y in range(5):
            for x in range(5):
                val = random.random()
                h = rand_hue * val
                s = 0.8
                rgb = RgbMatrix.hsv_to_rgb(h, s, val)
                r = int(rgb[0] * 255.0)
                g = int(rgb[1] * 255.0)
                b = int(rgb[2] * 255.0)
                self._stbd_rgbmatrix.set_pixel(x, y, r, g, b)
        self._stbd_rgbmatrix.update()

    def set_random_delay_sec(self, delay_sec):
        if delay_sec > 0.0:
            self._random_delay_sec = delay_sec

    def _random(self, rgbmatrix5x5, arg, is_enabled):
        self._log.info('starting random…')
        while is_enabled():
            rand_hue = random.random() * 0.8 + 0.1
            for y in range(5):
                for x in range(5):
                    val = random.random()
                    h = rand_hue * val
                    s = 0.8
                    rgb = RgbMatrix.hsv_to_rgb(h, s, val)
                    r = int(rgb[0] * 255.0)
                    g = int(rgb[1] * 255.0)
                    b = int(rgb[2] * 255.0)
                    rgbmatrix5x5.set_pixel(x, y, r, g, b)
            if not is_enabled():
                break
            rgbmatrix5x5.update()
            time.sleep(self._random_delay_sec)
        self._clear(rgbmatrix5x5)
        self._log.info('random ended.')

    def set_color(self, color, show=True):
        if self._port_rgbmatrix:
            self._set_color(self._port_rgbmatrix, color, show)
        if self._stbd_rgbmatrix:
            self._set_color(self._stbd_rgbmatrix, color, show)

    @staticmethod
    def set_column(rgbmatrix5x5, column, color, brightness, blank=True):
        if column < 0 or column > 5:
            raise ValueError('column argument \'{:d}\' out of range (0-5)'.format(column))
        if blank:
            rgbmatrix5x5.clear()
        rows = 5
        for y in range(0, rows):
            rgbmatrix5x5.set_pixel(y, column, color.red, color.green, color.blue)
        rgbmatrix5x5.update()

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

    def set_display_type(self, display_type):
        self._display_type = display_type


#EOR
