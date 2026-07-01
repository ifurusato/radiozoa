#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2024-10-23
# modified: 2026-07-01
#
# The basic idea:
#
#        XXX
#       X   X
#       X   X
#        XXX
#
#         X
#        X X
#       X   X
#
#       X
#         X
#           X
#         X
#       X
#
#       XXXXX
#         X
#         X
#         X
#
#       X   X
#        X X
#         X
#        X X
#       X   X

from colors import *


class Eyeball:

    def __init__(self, index, name, color, array):
        self._index = index
        self._name = name
        self._color = color
        self._array = array

    @property
    def name(self):
        return self._name

    @property
    def color(self):
        return self._color

    @property
    def array(self):
        return self._array


# Class-level Constants
Eyeball.NORMAL = Eyeball(0, 'normal', COLOR_GREEN, [
    [0, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0]
])

Eyeball.HAPPY = Eyeball(1, 'happy', COLOR_YELLOW_GREEN, [
    [0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0],
    [1, 0, 0, 0, 1],
    [0, 0, 0, 0, 0]
])

Eyeball.WINK_PORT = Eyeball(2, 'wink-port', COLOR_YELLOW_GREEN, [
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0],
    [1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0]
])

Eyeball.WINK_STBD = Eyeball(3, 'wink-stbd', COLOR_YELLOW_GREEN, [
    [0, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0]
])

Eyeball.BLUSH = Eyeball(4, 'blush', COLOR_PINK, [
    [0, 0, 0, 0, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0]
])

Eyeball.LOOK_STBD = Eyeball(5, 'look-stbd', COLOR_ORANGE, [
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0]
])

Eyeball.LOOK_PORT = Eyeball(6, 'look-port', COLOR_ORANGE, [
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0]
])

Eyeball.LOOK_UP = Eyeball(7, 'look-up', COLOR_ORANGE, [
    [0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0],
    [1, 0, 0, 0, 1],
    [0, 0, 0, 0, 0]
])

Eyeball.LOOK_DOWN = Eyeball(8, 'look-down', COLOR_ORANGE, [
    [0, 0, 0, 0, 0],
    [1, 0, 0, 0, 1],
    [0, 1, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0]
])

Eyeball.CONFUSED_PORT = Eyeball(9, 'confused-port', COLOR_CORAL, [
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0]
])

Eyeball.CONFUSED_STBD = Eyeball(10, 'confused-stbd', COLOR_CORAL, [
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0]
])

Eyeball.BORED = Eyeball(11, 'bored', COLOR_GREY_ORANGE, [
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0]
])

Eyeball.SLEEPY = Eyeball(12, 'sleepy', COLOR_DARK_GREY, [
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0]
])

Eyeball.DEEP_SLEEP = Eyeball(13, 'deep-sleep', COLOR_VERY_DARK_GREY, [
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0]
])

Eyeball.WOW1 = Eyeball(14, 'wow-1', COLOR_YELLOW, [
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0]
])

Eyeball.WOW2 = Eyeball(15, 'wow-2', COLOR_YELLOW, [
    [0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0],
    [0, 1, 0, 1, 0],
    [0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0]
])

Eyeball.WOW3 = Eyeball(16, 'wow-3', COLOR_YELLOW, [
    [0, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0]
])

Eyeball.BLANK = Eyeball(17, 'blank', COLOR_ORANGE, [
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0]
])

Eyeball.NEUTRAL = Eyeball(18, 'neutral', COLOR_GREY_ORANGE, [
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0]
])

Eyeball.SAD = Eyeball(19, 'sad', COLOR_BLUE_VIOLET, [
    [0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0]
])

Eyeball.DEAD = Eyeball(20, 'dead', COLOR_GREY, [
    [1, 0, 0, 0, 1],
    [0, 1, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0],
    [1, 0, 0, 0, 1]
])

Eyeball.LOOK_STBD_FWD = Eyeball(21, 'look-stbd-fwd', COLOR_BLUE, [
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0]
])

Eyeball.LOOK_PORT_FWD = Eyeball(22, 'look-port-fwd', COLOR_BLUE, [
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0]
])

Eyeball.LOOK_STBD_AFT = Eyeball(23, 'look-stbd-aft', COLOR_YELLOW, [
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0]
])

Eyeball.LOOK_PORT_AFT = Eyeball(24, 'look-port-aft', COLOR_YELLOW, [
    [0, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0]
])

#EOF
