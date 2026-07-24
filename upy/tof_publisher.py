#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-07-13

import sys
import asyncio
import time
from colorama import Fore, Style

from logger import Level
from event import TOF_DISTANCES
from message import Message
from publisher import Publisher

class ToFPublisher(Publisher):
    '''
    Polls the RadiozoaSensor at a fixed interval and publishes the eight
    distance readings as a TOF_DISTANCES message on the bus.

    :param sensor:       the RadiozoaSensor instance
    :param message_bus:  the message bus
    :param poll_ms:      the polling interval in milliseconds (default 50ms = 20Hz)
    :param level:        the logging level
    '''
    DEFAULT_POLL_MS = 50

    def __init__(self, config=None, sensor=None, message_bus=None, message_factory=None, poll_ms=DEFAULT_POLL_MS, level=Level.INFO):
        Publisher.__init__(self, 'tof-pub', message_bus, message_factory, suppressed=False, enabled=False, level=level)
        _cfg = config['rros']['tof_publisher']
        self._verbose = True # _cfg['verbose']
        self._sensor  = sensor
        self._poll_ms = poll_ms
        self._poll_loop_task = None
        self._log.info('ready')

    def enable(self):
        if not self.enabled:
            super().enable()
            self._poll_loop_task = asyncio.create_task(self._poll_loop())
            self._log.debug('enabled.')
        else:
            self._log.warn('already enabled.')

    def disable(self):
        if self.enabled:
            super().disable()
            if self._poll_loop_task:
                self._poll_loop_task.cancel()
            self._log.debug('disabled.')
        else:
            self._log.warn('already disabled.')

    @property
    def poll_ms(self):
        return self._poll_ms

    @poll_ms.setter
    def poll_ms(self, value):
        self._poll_ms = value


    def _get_color(self, value):
        if value <= 50:
            return Fore.RED
        elif value <= 100:
            return Fore.YELLOW
        elif value <= 200:
            return Fore.GREEN
        elif value <= 300:
            return Fore.CYAN
        elif value <= 500:
            return Fore.MAGENTA
        else:
            return Fore.BLACK

    def _formatter(self, distances):
        parts = []
        for distance in distances:
            parts.append("{}{:4d}{}".format(self._get_color(distance), distance, Style.RESET_ALL))
        return " ".join(parts)

    async def _poll_loop(self):
        '''
        Async poll loop: reads all eight sensors and publishes distances while enabled.
        '''
        self._log.info('starting poll loop…')
        while self.enabled:
            try:
                _distances = await self._sensor.get_distances_async()
                if self._verbose:
                    self._log.info("dist: {}".format(self._formatter(_distances)))
                _message = self._message_factory.create_message(TOF_DISTANCES, _distances)
                self.publish(_message)
            except Exception as e:
                self._log.error('{} raised in poll loop: {}'.format(type(e), e))
                sys.print_exception(e)
            await asyncio.sleep_ms(self._poll_ms)
        self._log.info('poll loop ended.')

#EOF
