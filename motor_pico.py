#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:    Ichiro Furusato
# created:   2026-06-07
# modified:  2026-06-17

import errno
import time
from machine import Pin, PWM, Timer
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

    Velocity tracks the measured counts per second.
    The encoder pins are optional. If either is not supplied this will operate the motor
    in open loop mode with no feedback.

    CLOSED-LOOP OPERATION REFERENCE

    Wheel Geometry: 59mm Diameter, 8mm Width (5908 Standard Wheel)
    Encoder Resolution: 121.12 Counts Per Revolution (CPR)

    +--------------------+---------------+---------------+------------------+
    | Metric             | Minimum Limit | Maximum Limit | Hardware Ceiling |
    +--------------------+---------------+---------------+------------------+
    | Internal Frequency |  50.0 cps     |  520.0 cps    |  620.0 cps       |
    | Linear Velocity    |  76.5 mm/s    |  795.8 mm/s   |  948.8 mm/s      |
    | Centimeters Scale  |   7.7 cm/s    |   79.6 cm/s   |   94.9 cm/s      |
    +--------------------+---------------+---------------+------------------+

    :param orientation:  orientation: 'PORT' or 'STBD'
    :param timer_id:     ESP32-S3 hardware timer ID (0-3)
    :param in1_pin:      GPIO number for DRV8833 IN1 (forward PWM)
    :param in2_pin:      GPIO number for DRV8833 IN2 (reverse PWM)
    :param enc_a_pin:    GPIO number for encoder channel A (interrupt source)
    :param enc_b_pin:    GPIO number for encoder channel B (direction reference)
    :param freq:         PWM frequency in Hz (default 10000)
    :param level:        the logging level
    '''
    def __init__(self,
            orientation,
            timer_id = 0,
            in1_pin=None,
            in2_pin=None,
            enc_a_pin=None,
            enc_b_pin=None,
            freq=DEFAULT_FREQUENCY,
            reverse_encoder=False,
            level=Level.INFO):
        self._orientation = orientation
        self._timer_id = timer_id
        self._name    = orientation.name.lower()
        self._freq    = freq
        self._color   = Fore.RED if orientation is Orientation.PORT else Fore.GREEN
        Component.__init__(self, 'motor:{}'.format(self._name))
        self._step_count = -1 if reverse_encoder else 1
        self._speed   = 0
        self._in1_pin = in1_pin
        self._in2_pin = in2_pin
        self._pwm1    = None if in1_pin is None   else PWM(Pin(in1_pin),  freq=freq, duty_u16=0)
        self._pwm2    = None if in2_pin is None   else PWM(Pin(in2_pin),  freq=freq, duty_u16=0)
        self._enc_a   = None if enc_a_pin is None else Pin(enc_a_pin, Pin.IN, Pin.PULL_UP)
        self._enc_b   = None if enc_b_pin is None else Pin(enc_b_pin, Pin.IN, Pin.PULL_UP)
        if self._enc_a and self._enc_b:
            self._log.info('{}{} motor pins: in1={}, in2={}, encA={}, encB={} (closed loop)'.format(
                    self._color, self._name, in1_pin, in2_pin, enc_a_pin, enc_b_pin) + Style.RESET_ALL)
        else:
            self._log.info('{}{} motor pins: in1={}, in2={} (open loop)'.format(
                    self._color, self._name, in1_pin, in2_pin, freq))

        # odometry
        self._steps   = 0
        self._last_steps = 0

        # velocity and Closed-Loop Control Attributes
        self._velocity = 0.0
        self._target_velocity = 0.0

        # physical Wheel Geometry (5908 Standard Wheel: 59mm x 8mm)
        self._wheel_diameter_mm = 59.0
        self._encoder_cpr = 121.12
        # calculate circumference: pi * diameter
        _circumference = 3.14159265 * self._wheel_diameter_mm
        # conversion factor: ticks per mm
        self._ticks_per_mm = self._encoder_cpr / _circumference
        self._mm_per_tick = _circumference / self._encoder_cpr

        # closed-loop operating boundaries (encoder counts per second)
        self._min_cps  = 50.0
        self._max_cps  = 520.0

        # PID tuning and Feed-Forward Profile for 30:1 Motors
        self._kp       = 0.06
        self._ki       = 0.08
        self._kd       = 0.0
        self._kff      = 0.175
        self._integral = 0.0
        self._last_error = 0.0

        # Sample interval configuration (50ms)
        self._sample_ms = 50
        self._timer = None
        self._log.info('{}{} motor ready.'.format(self._color, self._name))

    def enable(self):
        if self.enabled:
            self._log.warning('already enabled.')
            return
        if self._enc_a and self._enc_b:
            self._enc_a.irq(trigger=Pin.IRQ_RISING, handler=self._enc_irq)
            self._timer = Timer(self._timer_id)
            self._timer.init(period=self._sample_ms, mode=Timer.PERIODIC, callback=self._tick)
            self._log.info('enable {}{} motor: timer={} (closed loop)'.format(
                    self._color, self._name, self._timer_id) + Style.RESET_ALL)
        else:
            self._log.info('enable {}{} motor: timer={} (open loop)'.format(
                    self._color, self._name, self._timer_id))
        super().enable()
        self._log.info('enabled.')

    def disable(self):
        if not self.enabled:
            self._log.warning('already disabled.')
            return
        if self._timer:
            self._timer.deinit()
        super().disable()
        self._log.info('enabled.')

    # odometry ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_distance_mm(self):
        '''
        Returns the net distance traveled by the wheel in millimeters (mm)
        since the last reset. Supports both forward and reverse tracking.
        '''
        return float(self._steps) * self._mm_per_tick

    def reset_odometry(self):
        '''
        Resets the physical distance tracker and underlying encoder steps to zero.
        '''
        self._steps = 0
        self._last_steps = 0
        self._integral = 0.0

    # velocity ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def set_linear_velocity(self, velocity_mms):
        '''
        Sets the target velocity of the motor in millimeters per second (mm/s).
        Automatically converts to internal counts per second and applies safety limits.
        '''
        if velocity_mms == 0:
            self._target_velocity = 0.0
            self._integral = 0.0
            self._last_error = 0.0
            self._execute_hardware_speed(0)
            return

        target_cps = float(velocity_mms) * self._ticks_per_mm
        abs_cps = abs(target_cps)

        if abs_cps < self._min_cps:
            target_cps = self._min_cps if target_cps > 0 else -self._min_cps
        elif abs_cps > self._max_cps:
            target_cps = self._max_cps if target_cps > 0 else -self._max_cps

        self._target_velocity = float(target_cps)

    # encoders ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _enc_irq(self, pin):
        '''
        Interrupt handler for encoder channel A.
        Direction determined by XOR of A and B pin states.
        '''
        if self._enc_a.value() ^ self._enc_b.value():
            self._steps += self._step_count
        else:
            self._steps -= self._step_count

    @property
    def steps(self):
        return self._steps

    @property
    def velocity(self):
        '''
        Returns velocity in encoder counts per second.
        '''
        return self._velocity

    def reset_steps(self):
        self._steps = 0
        self._last_steps = 0

    def _tick(self, timer):
        '''
        Periodic background update handler for calculating velocity and execution of PID step.
        '''
        current_steps = self._steps
        delta_steps = current_steps - self._last_steps
        self._last_steps = current_steps
        self._velocity = float(delta_steps * (1000 // self._sample_ms))

        error = self._target_velocity - self._velocity
        self._integral += error * (self._sample_ms / 1000.0)
        derivative = (error - self._last_error) / (self._sample_ms / 1000.0)
        self._last_error = error

        self._integral = max(min(self._integral, 15.0), -15.0)

        ff_output = self._kff * self._target_velocity
        pid_output = (self._kp * error) + (self._ki * self._integral) + (self._kd * derivative)
        output = ff_output + pid_output

        adjusted_speed = int(max(min(output, 100.0), -100.0))
        self._execute_hardware_speed(adjusted_speed)
        self._log.info('{}{} motor : {} steps.'.format(self._color, self._name, self.steps))

    # speed ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def speed(self):
        '''
        Return the last speed value set for this motor.
        '''
        return self._speed

    def set_speed(self, speed):
        '''
        Set the speed percentage of this motor. Argument must be in [-100, 100].
        '''
        if speed is None:
            raise TypeError("null speed argument.")
        elif not isinstance(speed, int):
            raise TypeError("speed must be an int, but got {}".format(type(speed)))
        if not -100 <= speed <= 100:
            raise ValueError("speed must be between -100 and 100, but got {}".format(speed))

        self._target_velocity = (speed / 100.0) * self._max_cps
        self._execute_hardware_speed(speed)

    def _execute_hardware_speed(self, speed):
        '''
        Internal low-level driver interface execution mapped directly to local PWM outputs.
        '''
        if self._pwm1 is None or self._pwm2 is None:
            self._log.warning('no hardware PWM available.')
            return

        self._speed = speed

        hw_speed = -speed if self._orientation is Orientation.STBD else speed

        duty = int((abs(hw_speed) / 100.0) * 65535)
        if hw_speed > 0:
#           print('>: {} on pin {}'.format(duty, self._in1_pin))
            self._pwm1.duty_u16(duty)
            self._pwm2.duty_u16(0)
        elif hw_speed < 0:
#           print('<: {} on pin {}'.format(duty, self._in2_pin))
            self._pwm1.duty_u16(0)
            self._pwm2.duty_u16(duty)
        else:
#           print('0: {}'.format(duty))
            self._pwm1.duty_u16(0)
            self._pwm2.duty_u16(0)

    def brake(self):
        '''
        active braking: both IN pins driven high instantly.
        '''
        self._target_velocity = 0.0
        self._integral = 0.0
        self._last_error = 0.0
        self._pwm1.duty_u16(65535)
        self._pwm2.duty_u16(65535)
        self._speed = 0

    def coast(self):
        '''
        coast to stop: both IN pins low.
        '''
        self._target_velocity = 0.0
        self._integral = 0.0
        self._last_error = 0.0
        self._execute_hardware_speed(0)

    def __str__(self):
        return "Motor(orientation={})".format(self._name)


    def close(self):
        if not self.closed:
            if self._timer:
                self._timer.deinit()
            self.coast()
            if self._pwm1:
                self._pwm1.deinit()
            if self._pwm2:
                self._pwm2.deinit()
            Component.close(self)
            self._log.info('closed.')

#EOF
