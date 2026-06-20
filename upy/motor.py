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

from machine import Pin, PWM

from logger import Level
from component import Component

class Motor(Component):
    '''
    Controls a single brushed DC motor via a DRV8833 H-bridge in fast-decay mode,
    and reads position from a quadrature encoder using a single A-channel interrupt
    with B-channel as direction reference.

    Power is expressed as a float in [-1.0, 1.0]; positive is forward, negative reverse.
    The velocity property is stubbed as 0.0 pending encoder calibration with hardware.

    The encoder pins are optional. If either is not supplied this will operate the motor
    in open loop mode with no feedback.

    :param orientation:  Orientation.PORT or Orientation.STBD
    :param in1_pin:      GPIO number for DRV8833 IN1 (forward PWM)
    :param in2_pin:      GPIO number for DRV8833 IN2 (reverse PWM)
    :param enc_a_pin:    GPIO number for encoder channel A (interrupt source)
    :param enc_b_pin:    GPIO number for encoder channel B (direction reference)
    :param freq:         PWM frequency in Hz (default 20000)
    :param level:        the logging level
    '''
    def __init__(self, orientation, in1_pin, in2_pin, enc_a_pin=None, enc_b_pin=None, freq=20000, level=Level.INFO):
        self._orientation = orientation
        Component.__init__(self, 'motor:{}'.format(orientation.name), suppressed=False, enabled=False)
        self._steps = 0
        self._pwm1  = PWM(Pin(in1_pin),  freq=freq, duty_u16=0)
        self._pwm2  = PWM(Pin(in2_pin),  freq=freq, duty_u16=0)
        self._enc_a = None if enc_a_pin is None else Pin(enc_a_pin, Pin.IN, Pin.PULL_UP)
        self._enc_b = None if enc_b_pin is None else Pin(enc_b_pin, Pin.IN, Pin.PULL_UP)
        if self._enc_a and self._enc_b:
            self._enc_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._enc_irq)
            self._log.info('in1={}, in2={}, encA={}, encB={}; {}Hz'.format(
                    in1_pin, in2_pin, enc_a_pin, enc_b_pin, freq))
        else:
            self._log.info('in1={}, in2={}, {}Hz (open loop)'.format(in1_pin, in2_pin, freq))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def enable(self):
        if not self.enabled:
            super().enable()
            self._log.info('enabled.')
        else:
            self._log.warning('already enabled.')

    def disable(self):
        if self.enabled:
            super().disable()
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    def _enc_irq(self, pin):
        '''
        Interrupt handler for encoder channel A (both edges).
        Direction determined by XOR of A and B pin states: when A≠B forward (+1), else reverse (-1).
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
        Returns normalised velocity in [-1.0, 1.0].
        Stubbed as 0.0 pending encoder calibration.
        '''
        return 0.0

    def reset_steps(self):
        self._steps = 0

    def set_power(self, value):
        '''
        Sets motor power in [-1.0, 1.0]. positive drives forward, negative reverse.
        '''
        if not self.enabled:
            self._pwm1.duty_u16(0)
            self._pwm2.duty_u16(0)
#           self._log.warning('disabled: unable to set power.')
            return
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
        Active braking: both IN pins driven high.
        '''
        if self.enabled:
            self._pwm1.duty_u16(65535)
            self._pwm2.duty_u16(65535)

    def coast(self):
        '''
        Coast to stop: both IN pins low.
        '''
        if self.enabled:
            self._pwm1.duty_u16(0)
            self._pwm2.duty_u16(0)

    def close(self):
        if not self.closed:
            self.coast()
            self._pwm1.deinit()
            self._pwm2.deinit()
            Component.close(self)
            self._log.info('closed.')
        else:
            self._log.warning('already closed.')


#EOF
