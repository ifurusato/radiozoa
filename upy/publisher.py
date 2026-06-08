#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2019-12-23
# modified: 2026-06-08

from component import Component
from logger import Level

class Publisher(Component):
    '''
    A base publisher that pushes messages onto the message bus.

    :param name:         the publisher name
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, name, message_bus, level=Level.INFO):
        Component.__init__(self, 'pub:{}'.format(name))
        self._message_bus = message_bus

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def message_bus(self):
        return self._message_bus

    def publish(self, message):
        '''
        Publish a message to the bus if this publisher is active.
        '''
        if self.is_active:
            self._message_bus.publish(message)
        else:
            self._log.warning('ignored: publisher not active.')

#EOF
