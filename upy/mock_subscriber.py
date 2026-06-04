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

from logger import Level
from event import TOF_DISTANCES
from subscriber import Subscriber

class MockSubscriber(Subscriber):
    '''
    A mock subscriber that logs received ToF distance messages.
    '''
    def __init__(self, message_bus, level=Level.INFO):
        Subscriber.__init__(self, 'mock-sub', message_bus, level)
        self.add_event(TOF_DISTANCES)

    async def process_message(self, message):
        self._log.info('received: event={}, value={}, age={}ms'.format(
                message.event.label, message.value, message.age_ms))

#EOF
