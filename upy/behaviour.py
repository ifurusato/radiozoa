#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-07
# modified: 2026-06-08

from logger import Level
from subscriber import Subscriber

class Behaviour(Subscriber):
    '''
    Base class for all Behaviours. Maintains an intent vector and priority,
    both of which are read by the MotorController to compute motor outputs.
    Subclasses implement process_message() to update the intent vector.

    :param name:         the behaviour name
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, name, message_bus, _init_base=True, level=Level.INFO):
#       Subscriber.__init__(self, name if ':' in name else 'beh:{}'.format(name), message_bus, level)
        Subscriber.__init__(
            self,
            name=name if ':' in name else 'beh:{}'.format(name),
            message_bus=message_bus,
            level=level,
            _init_base=_init_base
        )
        self._intent_vector = (0.0, 0.0, 0.0)
        self._priority      = 0.0

    @property
    def intent_vector(self):
        return self._intent_vector

    @property
    def priority(self):
        return self._priority

    def clear_intent_vector(self):
        self._intent_vector = (0.0, 0.0, 0.0)

    def close(self):
        self.clear_intent_vector()
        Subscriber.close(self)

#EOF
