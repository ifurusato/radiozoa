#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-06-05

from logger import Level
from event import TOF_DISTANCES
from subscriber import Subscriber
from radiozoa_sensor import RadiozoaSensor, OUT_OF_RANGE
from cardinal import Cardinal
from colors import *

class RingVisualiser(Subscriber):
    '''
    A subscriber that receives TOF_DISTANCES messages and maps each sensor
    distance to a colour on the NeoPixel ring using the cardinal pixel positions
    and RadiozoaSensor distance thresholds.

    :param ring:         a Pixel instance for the 24-pixel ring
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, ring, message_bus, level=Level.INFO):
        Subscriber.__init__(self, 'ring-vis', message_bus, level)
        self._ring = ring
        self.add_event(TOF_DISTANCES)
        # clear ring on startup
        self._ring.off()

    async def process_message(self, message):
        distances = message.value
        for cardinal in Cardinal._registry:
            distance = distances[cardinal.id]
            color = self._distance_to_color(distance)
            self._ring.set_color(cardinal.pixel, color)

    def _distance_to_color(self, distance):
        if distance >= OUT_OF_RANGE:
            return COLOR_BLACK
        elif distance <= RadiozoaSensor.CLOSE_THRESHOLD:
            return COLOR_RED
        elif distance <= RadiozoaSensor.NEAR_THRESHOLD:
            return COLOR_ORANGE
        elif distance <= RadiozoaSensor.MID_THRESHOLD:
            return COLOR_YELLOW
        elif distance <= RadiozoaSensor.FAR_THRESHOLD:
            return COLOR_GREEN
        else:
            return COLOR_DARK_GREEN

#EOF
