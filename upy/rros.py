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
from logger import Logger, Level
from event import TOF_DISTANCES
from message import Message
from message_bus import MessageBus
from mock_publisher import MockPublisher
from mock_subscriber import MockSubscriber

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class RROS:
    '''
    Radiozoa Robot Operating System. Constructs and wires all system components,
    and provides the main async run loop.

    :param level:  the logging level
    '''
    def __init__(self, level=Level.INFO):
        self._log        = Logger('rros', level)
        self._bus        = MessageBus(level=level)
        self._publisher  = MockPublisher(self._bus, level=level)
        self._subscriber = MockSubscriber(self._bus, level=level)
        self._log.info('ready.')

    async def run(self):
        self._bus.enable()
        self._publisher.enable()
        self._subscriber.enable()
        asyncio.create_task(self._bus.consume_loop())
        asyncio.create_task(self._publisher.poll_loop())
        self._log.info('running…')
        while True:
            await asyncio.sleep_ms(100)

    def start(self):
        asyncio.run(self.run())

#EOF
