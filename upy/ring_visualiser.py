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
from pixel import Pixel
from device import Device
from colors import *

class RingVisualiser(Subscriber):
    '''
    A subscriber that receives TOF_DISTANCES messages and maps each sensor
    distance to a colour on the NeoPixel ring using the device pixel positions
    and RadiozoaSensor distance thresholds.

    :param ring:         a Pixel instance for the 24-pixel ring
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, ring, message_bus, level=Level.INFO):
        Subscriber.__init__(self, 'ring-vis', message_bus, level)
        self._ring = ring
        self.add_event(TOF_DISTANCES)
        self._use_enumerated_colors = False
        self._color_at_limit = 0.833 # 0.75 indigo; 0.833 magenta
        self._color           = [0, 0, 0]
        self._brightness      = 1.0
        self._brightness_step = 0.01
        self._brighten        = False
        # clear ring on startup
        self._ring.off()

    def set_brightness(self, multiplier):
        self._brightness = multiplier
        pass

    def set_brighten(self, brighten):
        self._brighten = brighten

    async def process_message(self, message):
        distances = message.value
        for device in Device._registry:
            distance = distances[device.index]
            if self._use_enumerated_colors:
                raw_color = self._distance_to_enumerated_color(distance)
            else:
                raw_color = self._distance_to_color(distance)
            self.set_color(device.pixel, raw_color)
            if self._brighten and self._brightness < 1.0:
                self._brightness += self._brightness_step
                if self._brightness == 1.0:
                    self._brighten = False

    def off(self, pixel):
        self._ring.set_color(pixel, (0, 0, 0))

    def set_color(self, pixel, color):
        self._color[0] = int(color[0] * self._brightness)
        self._color[1] = int(color[1] * self._brightness)
        self._color[2] = int(color[2] * self._brightness)
        self._ring.set_color(pixel, self._color)

    def _distance_to_enumerated_color(self, distance):
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
        elif distance <= 2000:
            return COLOR_CYAN
        elif distance <= 4000:
            return COLOR_INDIGO
        else:
            return COLOR_BLACK

    def _distance_to_color(self, distance):
        if distance >= OUT_OF_RANGE:
            return COLOR_BLACK
        d = min(max(distance, 0), 4000)
        hue = (d / 4000) * self._color_at_limit # 0.0=red through to 0.75=indigo
        # 0.0=red through to limit
        return Pixel.hsv_to_rgb(hue)

    def close(self):
        self._ring.off()
        Subscriber.close(self)

#EOF
