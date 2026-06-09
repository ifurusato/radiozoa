#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-09
# modified: 2026-06-09

from machine import ADC, Pin

class AnalogControl:
    '''
    A class to interface with an analog potentiometer on the ESP32-S3.
    '''
    def __init__(self, pin_num, reverse=False):
        '''
        Initialize the ADC pin with 11dB attenuation and 12-bit width.
        '''
        self._adc = ADC(Pin(pin_num))
        self._adc.atten(ADC.ATTN_11DB)
        self._adc.width(ADC.WIDTH_12BIT)
        self._reverse = reverse

    def read_raw(self):
        '''
        Return the 12-bit ADC value (0 - 4095), accounting for polarity.
        '''
        raw_val = self._adc.read()
        if self._reverse:
            return 4095 - raw_val
        return raw_val

    def read_scaled(self):
        '''
        Return the scaled ADC value as an integer between 0 and 100.
        '''
        raw_val = self.read_raw()
        return int(raw_val / 40.95)

#EOF
