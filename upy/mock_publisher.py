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

class MockPublisher(Publisher):

    PUBLISH_INTERVAL_MS = 1000

    '''
    A mock publisher that generates fake ToF distance readings at a fixed interval.
    '''
    def __init__(self, message_bus, level=Level.INFO):
        Publisher.__init__(self, 'mock-pub', message_bus, level)

    async def poll_loop(self):
        self._log.info('poll loop started.')
        _count = 0
        while self.enabled:
            _distances = (400, 350, 600, 800, 750, 500, 300, 450)
            _message = Message(TOF_DISTANCES, _distances)
            self.publish(_message)
            self._log.debug('published message {:d}: {}'.format(_count, _distances))
            _count += 1
            await asyncio.sleep_ms(MockPublisher.PUBLISH_INTERVAL_MS)
        self._log.info('poll loop ended.')

#EOF
