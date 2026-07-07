#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-07-04
# modified: 2026-07-04

from machine import Pin

from logger import Logger, Level
from component import Component

class DipSwitch(Component):
    NAME = 'dip-switch'
    '''
    Manages a 3-position hardware DIP switch used for runtime configuration profiles.
    Exposes switches logically as 1, 2, and 3.

    Mapping:
        Switch 1 -> GPIO47
        Switch 2 -> GPIO37
        Switch 3 -> GPIO36

    The get_switch() method returns True when a switch is closed.
    '''
    def __init__(self, level=Level.INFO):
        Component.__init__(self, DipSwitch.NAME, suppressed=False, enabled=True, level=level)
        self._switches = {
            1: Pin(47, Pin.IN, Pin.PULL_UP),
            2: Pin(37, Pin.IN, Pin.PULL_UP),
            3: Pin(36, Pin.IN, Pin.PULL_UP),
        }
        self._log.info('ready.')

    def get_switch(self, number):
        '''
        Returns the boolean state of switch (1, 2, or 3).
        Returns False if open (OFF), or True if closed (ON).
        '''
        return not self._switches[number].value()

    def __repr__(self):
        return "DipSwitch(s1={}, s2={}, s3={})".format(
            self._switches[1].value(),
            self._switches[2].value(),
            self._switches[3].value()
        )

#EOF
