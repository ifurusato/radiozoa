#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-07
# modified: 2026-06-07

from machine import Pin, PWM

from logger import Logger, Level
from component import Component

class Motor(Component):
    '''
    Controls a single brushed DC motor via a DRV8833 H-bridge in fast-decay mode,
    and reads position from a quadrature encoder using a single A-channel interrupt
    with B-channel as direction reference.

    Power is expressed as a float in [-1.0, 1.0]; positive is forward, negative reverse.
    The velocity property is stubbed as 0.0 pending encoder calibration with hardware.

    :param name:       identifier: 'port' or 'stbd'
    :param in1_pin:    GPIO number for DRV8833 IN1 (forward PWM)
    :param in2_pin:    GPIO number for DRV8833 IN2 (reverse PWM)
    :param enc_a_pin:  GPIO number for encoder channel A (interrupt source)
    :param enc_b_pin:  GPIO number for encoder channel B (direction reference)
    :param freq:       PWM frequency in Hz (default 20000)
    :param level:      the logging level
    '''
    def __init__(self, name, in1_pin, in2_pin, enc_a_pin, enc_b_pin, freq=20000, level=Level.INFO):
        Component.__init__(self, 'motor:{}'.format(name))
        self._log   = Logger('motor:{}'.format(name), level)
        self._pwm1  = PWM(Pin(in1_pin),  freq=freq, duty_u16=0)
        self._pwm2  = PWM(Pin(in2_pin),  freq=freq, duty_u16=0)
        self._enc_a = Pin(enc_a_pin, Pin.IN, Pin.PULL_UP)
        self._enc_b = Pin(enc_b_pin, Pin.IN, Pin.PULL_UP)
        self._steps = 0
        self._enc_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._enc_irq)
        self._log.info('in1={}, in2={}, encA={}, encB={}; {}Hz'.format(
                in1_pin, in2_pin, enc_a_pin, enc_b_pin, freq))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _enc_irq(self, pin):
        '''
        interrupt handler for encoder channel A (both edges).
        direction determined by XOR of A and B pin states: when A≠B forward (+1), else reverse (-1).
        '''
        if self._enc_a.value() ^ self._enc_b.value():
            self._steps += 1
        else:
            self._steps -= 1

    @property
    def steps(self):
        return self._steps

    @property
    def velocity(self):
        '''
        returns normalised velocity in [-1.0, 1.0].
        stubbed as 0.0 pending encoder calibration.
        '''
        return 0.0

    def reset_steps(self):
        self._steps = 0

    def set_power(self, value):
        '''
        sets motor power in [-1.0, 1.0]. positive drives forward, negative reverse.
        '''
        if value >  1.0: value =  1.0
        elif value < -1.0: value = -1.0
        duty = int(abs(value) * 65535)
        if value > 0.0:
            self._pwm1.duty_u16(duty)
            self._pwm2.duty_u16(0)
        elif value < 0.0:
            self._pwm1.duty_u16(0)
            self._pwm2.duty_u16(duty)
        else:
            self._pwm1.duty_u16(0)
            self._pwm2.duty_u16(0)

    def brake(self):
        '''
        active braking: both IN pins driven high.
        '''
        self._pwm1.duty_u16(65535)
        self._pwm2.duty_u16(65535)

    def coast(self):
        '''
        coast to stop: both IN pins low.
        '''
        self._pwm1.duty_u16(0)
        self._pwm2.duty_u16(0)

    def close(self):
        if not self.closed:
            self.coast()
            self._pwm1.deinit()
            self._pwm2.deinit()
            Component.close(self)
            self._log.info('closed.')

#EOF
