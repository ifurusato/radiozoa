#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-08-21
# modified: 2026-08-21

import asyncio
import time
from machine import Pin, TouchPad
from colorama import Fore, Style

from logger import Logger, Level

class TouchSensor:

    def __init__(self, pin_num=None, label=None, margin=5000, poll_ms=50, calibrate=True):
        self._log = Logger('touch-{}'.format(label), level=Level.INFO)
        self.touch_pin = TouchPad(Pin(pin_num))
        self._poll_ms  = poll_ms
        self._touched  = False
        self._task     = None
        self._callback = None
        if calibrate:
            self._log.info('calibrating…')
            _baseline = self._get_average(20)
        else:
            _baseline = 30000
            self._log.info('using fixed baseline of {}.'.format(_baseline))
        self._threshold = _baseline + margin
        self._log.info("baseline: {}; threshold: {}".format(_baseline, self._threshold))
        self._log.info('ready.')

    @property
    def is_touched(self):
        return self._touched

    def set_callback(self, callback):
        self._callback = callback

    def _get_average(self, samples):
        total = 0
        for _ in range(samples):
            total += self.touch_pin.read()
            time.sleep_ms(10)
        return total // samples

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._poll_task())

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _poll_task(self):
        while True:
            value = self.touch_pin.read()
            if value > self._threshold:
                if not self._touched:
                    self._touched = True
                    self._log.info(Fore.GREEN + "touch detected; value: {}".format(value))
            else:
                if self._touched:
                    self._log.info(Fore.BLUE + "touch released; value: {}".format(value))
                    if self._callback:
                        self._callback()
                self._touched = False
            await asyncio.sleep_ms(self._poll_ms)

#EOF
