#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-06-06

from logger import Level
from event import TOF_DISTANCES
from subscriber import Subscriber
from colorama import *

class ToFSubscriber(Subscriber):
    '''
    A subscriber that logs received ToF distance messages.
    '''
    def __init__(self, message_bus, level=Level.INFO):
        Subscriber.__init__(self, 'tof', message_bus, level)
        self._count = 0
        self.add_event(TOF_DISTANCES)

    async def process_message(self, message):
        '''
        This prints the first 50 messages and then after that, every 10th.
        '''
        if self._count < 50 or self._count % 10 == 0:
            self._log.info('rx: event={},{} value={},{} age={}ms'.format(
                    message.event.label, 
                    Fore.GREEN,
                    message.value, 
                    Fore.BLACK,
                    message.age_ms))
        self._count += 1

#EOF
