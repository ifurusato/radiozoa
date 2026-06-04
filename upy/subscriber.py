#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2021-03-10
# modified: 2026-06-04

from component import Component
from logger import Logger, Level

class Subscriber(Component):
    '''
    A base subscriber that receives messages from the message bus.
    Registers itself with the bus on construction.

    :param name:         the subscriber name
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, name, message_bus, level=Level.INFO):
        Component.__init__(self, name)
        self._log         = Logger('sub:{}'.format(name), level)
        self._message_bus = message_bus
        self._events      = []
        message_bus.add_subscriber(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def message_bus(self):
        return self._message_bus

    def add_event(self, event):
        self._events.append(event)

    def add_events(self, events):
        for _event in events:
            self._events.append(_event)

    @property
    def events(self):
        return self._events

    def acceptable(self, message):
        '''
        Returns True if this subscriber accepts the message's event type,
        or if no event filter has been set (accepts all).
        '''
        return not self._events or message.event in self._events

    async def process_message(self, message):
        '''
        Process a received message. Override in subclass.
        '''
        pass

#EOF
