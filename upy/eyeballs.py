#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2024-10-23
# modified: 2026-07-04

from logger import Level, Logger
from component import Component
from orientation import Orientation
from rgbmatrix import RgbMatrix
from colors import *
from eyeball import Eyeball

class PalpebralMovement:

    def __init__(self, num, name, method):
        self._index = num
        self._name = name
        self._method = method

    @property
    def name(self):
        return self._name

    @property
    def method(self):
        return self._method

    @classmethod
    def from_name(cls, name: str):
        '''
        Return the PalpebralMovement instance for a given name string.
        '''
        name = name.strip().lower()
        for member in cls._ALL:
            if member.name == name:
                return member
        raise ValueError("'{:s}' is not a valid PalpebralMovement name.".format(name))

PalpebralMovement.CLEAR     = PalpebralMovement( 1, "clear", "clear")
PalpebralMovement.NORMAL    = PalpebralMovement( 2, "normal", "normal")
PalpebralMovement.HAPPY     = PalpebralMovement( 3, "happy", "happy")
PalpebralMovement.WINK      = PalpebralMovement( 4, "wink", "wink")
PalpebralMovement.BLUSH     = PalpebralMovement( 5, "blush", "blush")
PalpebralMovement.LOOP_PORT = PalpebralMovement( 6, "look-port", "look_port")
PalpebralMovement.LOOK_STBD = PalpebralMovement( 7, "look-stbd", "look_stbd")
PalpebralMovement.LOOK_UP   = PalpebralMovement( 8, "look-up", "look_up")
PalpebralMovement.LOOK_DOWN = PalpebralMovement( 9, "look-down", "look_down")
PalpebralMovement.CONFUSED  = PalpebralMovement(10, "confused", "confused")
PalpebralMovement.SLEEPY    = PalpebralMovement(11, "sleepy", "sleepy")
PalpebralMovement.SAD       = PalpebralMovement(12, "sad", "sad")
PalpebralMovement.BLANK     = PalpebralMovement(13, "blank", "blank")
PalpebralMovement.DEAD      = PalpebralMovement(14, "dead", "dead")

PalpebralMovement._ALL = [
    PalpebralMovement.CLEAR, PalpebralMovement.NORMAL, PalpebralMovement.HAPPY,
    PalpebralMovement.WINK, PalpebralMovement.BLUSH, PalpebralMovement.LOOP_PORT,
    PalpebralMovement.LOOK_STBD, PalpebralMovement.LOOK_UP, PalpebralMovement.LOOK_DOWN,
    PalpebralMovement.CONFUSED, PalpebralMovement.SLEEPY, PalpebralMovement.SAD,
    PalpebralMovement.BLANK, PalpebralMovement.DEAD
]

class Eyeballs(Component):
    NAME = 'eyeballs'
    '''
    A display of eyes on a pair of 5x5 RGB LED matrix displays.

    :param level:   the logging Level
    $$
    '''
    def __init__(self, i2c=None, level=Level.INFO):
        Component.__init__(self, Eyeballs.NAME, suppressed=False, enabled=True)
        enable_port = True
        enable_stbd = True
        self._rgbmatrix = RgbMatrix(i2c, enable_port, enable_stbd, Level.INFO)
        self._port_rgbmatrix = self._rgbmatrix.get_rgbmatrix(Orientation.PORT)
        self._stbd_rgbmatrix = self._rgbmatrix.get_rgbmatrix(Orientation.STBD)
        self._thread = None
        self._movements = {
            "clear": self.clear,
            "normal": self.normal,
            "happy": self.happy,
            "wink": self.wink,
            "blush": self.blush,
            "look_port": self.look_port,
            "look_stbd": self.look_stbd,
            "look_up": self.look_up,
            "look_down": self.look_down,
            "confused": self.confused,
            "sleepy": self.sleepy,
            "sad": self.sad,
            "blank": self.blank,
            "dead": self.dead
        }
        self._log.info('ready.')

    def enable(self):
        if not self.enabled:
            super().enable()
        else:
            self._log.debug('already enabled.')

    def show(self, movement: PalpebralMovement):
        '''
        Call the method on Eyeballs matching the enum name.
        '''
        if movement is None:
            raise ValueError('no palpebral movement specified.')
        method_name = movement.method
        if method_name in self._movements:
            return self._movements[method_name]()
        raise AttributeError("'{:s}' has no method '{:s}()'".format(self.__class__.__name__, method_name))

    def clear(self):
        self._rgbmatrix.clear_all()

    def set_matrix(self, array, matrix, color=COLOR_ORANGE):
        for y in range(0, 5):
            for x in range(0, 5):
                if array[x][y] == 1:
                    _color = color
                else:
                    _color = COLOR_BLACK
                matrix.set_pixel(x, y, _color.red, _color.green, _color.blue)

    def _show(self):
        self._port_rgbmatrix.show()
        self._stbd_rgbmatrix.show()

    def normal(self):
        self._log.debug('normal…')
        _eyeball = Eyeball.NORMAL
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def happy(self):
        self._log.debug('happy…')
        _eyeball = Eyeball.HAPPY
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def wink(self):
        self._log.debug('wink…')
        self.set_matrix(Eyeball.WINK_PORT.array, self._port_rgbmatrix, Eyeball.WINK_PORT.color)
        self.set_matrix(Eyeball.WINK_STBD.array, self._stbd_rgbmatrix, Eyeball.WINK_PORT.color)
        self._show()

    def blush(self):
        self._log.debug('blush…')
        _eyeball = Eyeball.BLUSH
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def look_port(self):
        self._log.debug('look port…')
        _eyeball = Eyeball.LOOK_PORT
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def look_stbd(self):
        self._log.debug('look starboard…')
        _eyeball = Eyeball.LOOK_STBD
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def look_up(self):
        self._log.debug('look up…')
        _eyeball = Eyeball.LOOK_UP
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def look_down(self):
        self._log.debug('look down…')
        _eyeball = Eyeball.LOOK_DOWN
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def confused(self):
        self._log.debug('confused…')
        self.set_matrix(Eyeball.CONFUSED_STBD.array, self._port_rgbmatrix, Eyeball.CONFUSED_STBD.color)
        self.set_matrix(Eyeball.CONFUSED_PORT.array, self._stbd_rgbmatrix, Eyeball.CONFUSED_PORT.color)
        self._show()

    def sleepy(self):
        self._log.debug('sleepy…')
        _eyeball = Eyeball.SLEEPY
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def sad(self):
        self._log.debug('sad…')
        _eyeball = Eyeball.SAD
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def blank(self):
        self._log.debug('blank…')
        _eyeball = Eyeball.BLANK
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def dead(self):
        self._log.debug('dead…')
        _eyeball = Eyeball.DEAD
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._rgbmatrix.show()

    def look_port_fwd(self):
        self._log.debug('look forward to port…')
        _eyeball = Eyeball.LOOK_PORT_FWD
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def look_stbd_fwd(self):
        self._log.debug('look forward to starboard…')
        _eyeball = Eyeball.LOOK_STBD_FWD
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def look_port_aft(self):
        self._log.debug('look aft to port…')
        _eyeball = Eyeball.LOOK_PORT_AFT
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def look_stbd_aft(self):
        self._log.debug('look aft to starboard…')
        _eyeball = Eyeball.LOOK_STBD_AFT
        self.set_matrix(_eyeball.array, self._port_rgbmatrix, _eyeball.color)
        self.set_matrix(_eyeball.array, self._stbd_rgbmatrix, _eyeball.color)
        self._show()

    def close(self):
        if not self.closed:
            self._rgbmatrix.clear_all()
            self._rgbmatrix.close()
            super().close()
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')

#EOF
