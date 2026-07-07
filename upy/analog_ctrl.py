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
    def __init__(self, config=None, reverse=True):
        '''
        Initialize the ADC pin with 11dB attenuation and 12-bit width.
        Depending on how the pot is wired, the reverse argument may be
        necessary to set the positive/negative rotational direction.
        '''
        if config is None:
            raise TypeError('no configuration provided.')
        _cfg = config['rros']['analog_control']
        _pin = _cfg['pin']
        self._deadband = _cfg.get("deadband", 0.0)
        self._adc = ADC(Pin(_pin))
        self._adc.atten(ADC.ATTN_11DB)
        self._adc.width(ADC.WIDTH_12BIT)
        self._reverse = reverse

    @property
    def raw_value(self):
        '''
        Return the 12-bit ADC value (0 - 4095), accounting for polarity.
        '''
        raw_val = self._adc.read()
        if self._reverse:
            return 4095 - raw_val
        return raw_val

    @property
    def percentage_value(self):
        '''
        Return the scaled ADC value as an integer between 0 and 100.
        '''
        raw_val = self.raw_value
        return int(raw_val / 40.95)

    @property
    def value(self):
        '''
        Return the biased float value (-1.0 to 1.0) with deadband applied.

            map 0 -> 4095 onto -1.0 -> 1.0
            formula: (raw / 2047.5) - 1.0
        '''
        val = (self.raw_value / 2047.5) - 1.0
        # apply deadband around the 0.0 center point
        if abs(val) <= self._deadband:
            return 0.0
        return val

#EOF
