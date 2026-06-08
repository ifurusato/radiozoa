#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-06-04

import asyncio

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

    def __init__(self, sensor, message_bus, poll_ms=DEFAULT_POLL_MS, level=Level.INFO):
        Publisher.__init__(self, 'tof-pub', message_bus, level)
        self._sensor  = sensor
        self._poll_ms = poll_ms

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def poll_ms(self):
        return self._poll_ms

    @poll_ms.setter
    def poll_ms(self, value):
        self._poll_ms = value

    async def poll_loop(self):
        '''
        Async poll loop: reads all eight sensors and publishes distances while enabled.
        '''
        self._log.info('poll loop started.')
        while self.enabled:
            try:
                _distances = self._sensor.get_distances()
                _message = Message(TOF_DISTANCES, _distances)
                print("MSG: " + _message)
                self.publish(_message)
            except Exception as e:
                self._log.error('{} raised in poll loop: {}'.format(type(e), e))
            await asyncio.sleep_ms(self._poll_ms)
        self._log.info('poll loop ended.')

#EOF
