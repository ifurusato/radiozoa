#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-07
# modified: 2026-07-13

from machine import Pin, PWM
from colorama import Fore, Style

from logger import Level
from component import Component
from orientation import Orientation

class Motor(Component):
    DEFAULT_FREQUENCY = 20000
    '''
    Controls a single brushed DC motor via a DRV8833 H-bridge in fast-decay mode,
    and reads position from a quadrature encoder using a single A-channel interrupt
    with B-channel as direction reference.

    Power is expressed as a float in [-1.0, 1.0]; positive is forward, negative reverse.
    Velocity measurement, PID control, and SI unit conversion are handled externally
    by MotorController.

    Wheel geometry: nominally 59mm diameter (measured at 60mm), 8mm Width (5908 Standard Wheel)
    70:1 gear ratio, N20 motors with encoder resolution: 121.12 Counts Per Revolution (CPR)

    840 ticks per wheel rotation, 188.5mm / wheel revolution, 4454-4456 ticks per meter.

    +--------------------+---------------+---------------+------------------+
    | Metric             | Minimum Limit | Maximum Limit | Hardware Ceiling |
    +--------------------+---------------+---------------+------------------+
    | Internal Frequency |  50.0 cps     |  520.0 cps    |  620.0 cps       |
    | Linear Velocity    |  76.5 mm/s    |  795.8 mm/s   |  948.8 mm/s      |
    | Centimeters Scale  |   7.7 cm/s    |   79.6 cm/s   |   94.9 cm/s      |
    +--------------------+---------------+---------------+------------------+

    :param orientation:      Orientation.PORT or Orientation.STBD
    :param in1_pin:          GPIO number for DRV8833 IN1 (forward PWM)
    :param in2_pin:          GPIO number for DRV8833 IN2 (reverse PWM)
    :param enc_a_pin:        GPIO number for encoder channel A (interrupt source)
    :param enc_b_pin:        GPIO number for encoder channel B (direction reference)
    :param freq:             PWM frequency in Hz (default 20000)
    :param reverse_encoder:  if True, negates encoder count direction
    :param level:            the logging level
    '''
    def __init__(self, orientation,
            in1_pin=None,
            in2_pin=None,
            enc_a_pin=None,
            enc_b_pin=None,
            freq=DEFAULT_FREQUENCY,
            reverse_encoder=False,
            level=Level.INFO):
        self._orientation = orientation
        Component.__init__(self, 'motor:{}'.format(orientation.name), suppressed=False, enabled=False)
        # encoder direction
        self._step_count = -1 if reverse_encoder else 1
        # PWM outputs
        self._pwm1       = PWM(Pin(in1_pin), freq=freq, duty_u16=0)
        self._pwm2       = PWM(Pin(in2_pin), freq=freq, duty_u16=0)
        # encoder pins
        self._enc_a      = None if enc_a_pin is None else Pin(enc_a_pin, Pin.IN, Pin.PULL_UP)
        self._enc_b      = None if enc_b_pin is None else Pin(enc_b_pin, Pin.IN, Pin.PULL_UP)
        if self._enc_a and self._enc_b:
            self._log.info('in1={}, in2={}, encA={}, encB={}, {}Hz (closed loop)'.format(
                    in1_pin, in2_pin, enc_a_pin, enc_b_pin, freq))
        else:
            self._log.info('in1={}, in2={}, {}Hz (open loop)'.format(in1_pin, in2_pin, freq))
        # wheel geometry for odometry
        _wheel_diameter_mm  = 60.0  # was: 59.0
        _motor_encoder_cpr  = 12.0
        _gear_ratio         = 70.0  # 70:1 gear reduction
        # derived geometry for odometry
        _ticks_per_wheel_rev = _motor_encoder_cpr * _gear_ratio  # 840.0
        _circumference       = 3.14159265 * _wheel_diameter_mm
        self._mm_per_tick    = _circumference / _ticks_per_wheel_rev
        self._log.info('odometry: {}mm/tick.'.format(self._mm_per_tick))
        # odometry
        self._steps         = 0
        self._log.info('ready.')

    # encoder ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _enc_irq(self, pin):
        '''
        Interrupt handler for encoder channel A (rising edge only).
        Direction determined by XOR of A and B pin states.
        '''
        if self._enc_a.value() ^ self._enc_b.value():
            self._steps += self._step_count
        else:
            self._steps -= self._step_count

    @property
    def steps(self):
        return self._steps

    def reset_steps(self):
        self._steps = 0

    # odometry ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_distance_mm(self):
        '''
        Returns the net distance traveled in mm since the last reset.
        '''
        return float(self._steps) * self._mm_per_tick

    def reset_odometry(self):
        '''
        Resets encoder steps and distance tracker to zero.
        '''
        self._steps = 0

    # power ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def set_power(self, value):
        '''
        Sets motor power in [-1.0, 1.0]. positive drives forward, negative reverse.
        '''
        if not self.enabled:
            self._execute_hardware_power(0.0)
            return
        if value >  1.0: value =  1.0
        elif value < -1.0: value = -1.0
        self._execute_hardware_power(value)

    def _execute_hardware_power(self, value):
        '''
        Low-level PWM driver. value in [-1.0, 1.0].
        '''
#       self._log.debug('_execute_hardware_power: {}'.format(value))
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

    # braking ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

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
            self._execute_hardware_power(0.0)

    # lifecycle ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def enable(self):
        if not self.enabled:
            if self._enc_a and self._enc_b:
                self._enc_a.irq(trigger=Pin.IRQ_RISING, handler=self._enc_irq)
                self._log.info('enabled (closed loop).')
            else:
                self._log.info('enabled (open loop).')
            super().enable()
        else:
            self._log.warn('already enabled.')

    def disable(self):
        if self.enabled:
            super().disable()
            self._log.debug('disabled.')
        else:
            self._log.warn('already disabled.')

    def close(self):
        if not self.closed:
            self.coast()
            self._pwm1.deinit()
            self._pwm2.deinit()
            super().close()
            self._log.debug('closed.')
        else:
            self._log.warn('already closed.')

#EOF
