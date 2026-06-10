#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-07
# modified: 2026-06-10

import asyncio

from colorama import Fore, Style

from logger import Level
from component import Component
from pixel import Pixel
from motor import Motor
from pid import PID

class MotorController(Component):
    NAME = 'motor-ctrl'
    '''
    Owns the two drive motors (port and starboard) and their PID controllers.
    Blends registered intent vectors from Behaviours by priority weighting,
    applies slew limiting, folds lateral intent (vx) into rotation via
    lateral_gain, then drives the motors using differential kinematics:

        V_port = vy + omega_final
        V_stbd = vy - omega_final
        omega_final = omega + lateral_gain × vx

    When _closed_loop is False (default until encoders are calibrated), encoder
    feedback is bypassed and target speed is mapped directly to motor power.

    Intended to be run as an asyncio task via _run(), registered by RROS.

    :param ring:   optional NeoPixel ring for motor speed visualisation
    :param level:  the logging level
    '''
    def __init__(self, config=None, ring=None, level=Level.INFO):
        Component.__init__(self, MotorController.NAME)
        if config is None:
            raise TypeError('no configuration provided.')
        _cfg = config['rros']['motor_controller']
        self._ring           = ring
        self._deadband       = config['rros']['analog_control']['deadband'] # 0.05
        # configuration ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._visualise_hue  = True # permit hue to be set
        self._hue_angle      = 0.875 # red=0.0; orange=0.083; magenta=0.833; fuchsia=0.875, etc.
        self._period_ms      = _cfg['period_ms']    # control loop period in ms (20Hz)
        # ring pixels for motor speed visualisation: free pixels between cardinal positions
        self._pin_port_pix1  = _cfg['pin_port_pix1'] # 5
        self._pin_port_pix2  = _cfg['pin_port_pix2'] # 7
        self._pin_stbd_pix1  = _cfg['pin_stbd_pix1'] # 17
        self._pin_stbd_pix2  = _cfg['pin_stbd_pix2'] # 19
        # motor pins ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._pin_in1        = _cfg['pin_in1'] # 14 (WeAct ESP32)
        self._pin_in2        = _cfg['pin_in2'] # 12
        self._pin_in3        = _cfg['pin_in3'] #  6
        self._pin_in4        = _cfg['pin_in4'] #  4
        # IN1: 43; IN2: 5; IN3: 21; IN4: 0
        self._log.info(Fore.WHITE + 'IN1: {}; IN2: {}; IN3: {}; IN4: {}'.format(
            self._pin_in1, self._pin_in2, self._pin_in3, self._pin_in4) + Style.RESET_ALL)
        self._pin_enc1a      = _cfg['pin_enc1A'] # 16 (WeAct ESP32)
        self._pin_enc1b      = _cfg['pin_enc1B'] # 17
        self._pin_enc2a      = _cfg['pin_enc2A'] #  2
        self._pin_enc2b      = _cfg['pin_enc2B'] #  1
        self._log.info(Fore.WHITE + 'ENC1A: {}; ENC1B: {}; ENC2A: {}; ENC2B: {}'.format(
            self._pin_enc1a, self._pin_enc1b, self._pin_enc2a, self._pin_enc2b) + Style.RESET_ALL)
        # motors: port uses IN1/IN2 and ENC1; stbd uses IN3/IN4 and ENC2
        self._motor_port     = Motor('port', self._pin_in1, self._pin_in2, self._pin_enc1a, self._pin_enc1b, level=level)
        self._motor_stbd     = Motor('stbd', self._pin_in3, self._pin_in4, self._pin_enc2a, self._pin_enc2b, level=level)
        # PID controllers — gains are initial estimates pending tuning with hardware
        self._pid_port       = PID('port', kp=0.8, ki=0.1, kd=0.05)
        self._pid_stbd       = PID('stbd', kp=0.8, ki=0.1, kd=0.05)
        # intent vectors registry: name → (vx, vy, omega, priority)
        self._intent_vectors = {}
        # lateral gain: scales vx contribution into omega correction
        self._lateral_gain   = 0.5  # tune empirically
        # slew limits: max change per tick at 20Hz (≈ 1.0/sec for vy, 2.0/sec for omega)
        self._slew_vy        = 0.05
        self._slew_omega     = 0.10
        self._last_vy        = 0.0
        self._last_omega     = 0.0
        # when False, bypasses PID and maps target speed directly to motor power
        self._closed_loop    = False
        self._stop           = False
#       self._diag_count     = 0 # temporary telemetry check
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def closed_loop(self):
        return self._closed_loop

    @closed_loop.setter
    def closed_loop(self, value):
        self._closed_loop = value
        self._log.info('{} closed-loop mode.'.format('enabled' if value else 'disabled'))

    @property
    def lateral_gain(self):
        return self._lateral_gain

    @lateral_gain.setter
    def lateral_gain(self, value):
        self._lateral_gain = value

    def add_intent_vector(self, name, vector_lambda, priority_lambda):
        '''
        Registers a behaviour's intent vector and priority lambdas by name.
        The vector lambda returns (vx, vy, omega); the priority lambda returns a float.
        Raises if the name is already registered.
        '''
        if name in self._intent_vectors:
            raise ValueError("intent vector '{}' already registered.".format(name))
        self._intent_vectors[name] = {
            'vector':   vector_lambda,
            'priority': priority_lambda
        }
        self._log.info('added intent vector: {}'.format(name))

    def remove_intent_vector(self, name):
        '''
        Removes a previously registered intent vector by name.
        '''
        if name in self._intent_vectors:
            del self._intent_vectors[name]
            self._log.info('removed intent vector: {}'.format(name))

    def _blend_intent_vectors(self):
        '''
        Priority-weighted blend of all registered intent vectors.
        Entries returning (0.0, 0.0, 0.0) are skipped so that inactive or
        Non-contributing behaviours do not dilute the result.
        Returns a (vx, vy, omega) tuple.
        '''
        if not self._intent_vectors:
            return (0.0, 0.0, 0.0)
        total_p = 0.0
        vx      = 0.0
        vy      = 0.0
        omega   = 0.0
        for entry in self._intent_vectors.values():
            vec = entry['vector']()
            if vec[0] == 0.0 and vec[1] == 0.0 and vec[2] == 0.0:
                continue
            p      = entry['priority']()
            vx    += vec[0] * p
            vy    += vec[1] * p
            omega += vec[2] * p
            total_p += p
        if total_p == 0.0:
            return (0.0, 0.0, 0.0)
        return (vx / total_p, vy / total_p, omega / total_p)

    def _slew(self, current, target, max_change):
        diff = target - current
        if diff >  max_change: return current + max_change
        elif diff < -max_change: return current - max_change
        return target

    def _tick(self):
        '''
        single control iteration: blend intent vectors, apply slew limiting,
        fold vx into omega, apply differential kinematics, drive motors,
        and update ring visualisation.
        '''
        vx, vy, omega = self._blend_intent_vectors()
        # slew limiting
        vy    = self._slew(self._last_vy,    vy,    self._slew_vy)
        omega = self._slew(self._last_omega, omega, self._slew_omega)
        self._last_vy    = vy
        self._last_omega = omega
        # fold lateral intent into rotation: ω_final = ω + lateral_gain × vx
        omega_final = omega + self._lateral_gain * vx
        if omega_final >  1.0: omega_final =  1.0
        elif omega_final < -1.0: omega_final = -1.0
        # differential kinematics
        v_port = vy + omega_final
        v_stbd = vy - omega_final
        if v_port >  1.0: v_port =  1.0
        elif v_port < -1.0: v_port = -1.0
        if v_stbd >  1.0: v_stbd =  1.0
        elif v_stbd < -1.0: v_stbd = -1.0
        # motor drive: closed-loop uses PID with encoder feedback, open-loop passes directly
        if self._closed_loop:
            self._pid_port.setpoint = v_port
            self._pid_stbd.setpoint = v_stbd
            self._pid_port.target   = self._motor_port.velocity
            self._pid_stbd.target   = self._motor_stbd.velocity
            pwr_port = self._pid_port()
            pwr_stbd = self._pid_stbd()
        else:
            pwr_port = v_port
            pwr_stbd = v_stbd
        self._motor_port.set_power(pwr_port)
        self._motor_stbd.set_power(pwr_stbd)

#       # telemetry check
#       self._diag_count += 1
#       if self._diag_count % 10 == 0:
#           self._log.info(
#               Fore.YELLOW
#               + "KINEMATICS -> vy: {0:.2f} | v_port: {1:.2f} | v_stbd: {2:.2f}".format(vy, v_port, v_stbd)
#               + Style.RESET_ALL
#           )

        # ring visualisation: hue encodes direction/type, value encodes power magnitude
        if self._ring:
            # PORT visualisation ┈┈┈┈┈┈┈┈┈┈┈┈
            if abs(v_port) < self._deadband:
                rgb_port = (0, 0, 0)
            else:
                # map [-1.0, 1.0] to [0.0, 0.5] (Red -> Green -> Cyan)
                hue_port = (v_port + 1.0) / 4.0
                brightness_port = abs(v_port)
                rgb_port = Pixel.hsv_to_rgb(hue_port, 1.0, brightness_port)
            # STBD visualisation ┈┈┈┈┈┈┈┈┈┈┈┈
            if abs(v_stbd) < self._deadband:
                rgb_stbd = (0, 0, 0)
            else:
                # map [-1.0, 1.0] to [0.0, 0.5] (Red -> Green -> Cyan)
                hue_stbd = (v_stbd + 1.0) / 4.0
                brightness_stbd = abs(v_stbd)
                rgb_stbd = Pixel.hsv_to_rgb(hue_stbd, 1.0, brightness_stbd)
            # apply to pixels ┈┈┈┈┈┈┈┈┈┈┈┈
            if self._pin_port_pix1:
                self._ring.set_color(self._pin_port_pix1, rgb_port)
            if self._pin_port_pix2:
                self._ring.set_color(self._pin_port_pix2, rgb_port)
            if self._pin_stbd_pix1:
                self._ring.set_color(self._pin_stbd_pix1, rgb_stbd)
            if self._pin_stbd_pix2:
                self._ring.set_color(self._pin_stbd_pix2, rgb_stbd)

    async def _run(self):
        '''
        main asyncio coroutine, to be added as a task by RROS.
        runs _tick() at period_ms intervals while enabled and not suppressed.
        '''
        while not self._stop:
            if self.enabled and not self.suppressed:
                self._tick()
            await asyncio.sleep_ms(self._period_ms)

    def brake(self):
        '''
        applies active braking to both motors and resets PID and slew state.
        '''
        self._motor_port.brake()
        self._motor_stbd.brake()
        self._pid_port.reset()
        self._pid_stbd.reset()
        self._last_vy    = 0.0
        self._last_omega = 0.0

    def coast(self):
        '''
        coasts both motors to a stop.
        '''
        self._motor_port.coast()
        self._motor_stbd.coast()

    def enable(self):
        if not self.enabled:
            Component.enable(self)
            self._log.info('enabled.')

    def disable(self):
        if self.enabled:
            self.coast()
            Component.disable(self)
            self._log.info('disabled.')

    def close(self):
        if not self.closed:
            self._stop = True
            self.coast()
            self._motor_port.close()
            self._motor_stbd.close()
            if self._ring:
                # clear pixels
                self._ring.set_color(self._pin_port_pix1, (0, 0, 0))
                self._ring.set_color(self._pin_port_pix2, (0, 0, 0))
                self._ring.set_color(self._pin_stbd_pix1, (0, 0, 0))
                self._ring.set_color(self._pin_stbd_pix2, (0, 0, 0))
            Component.close(self)
            self._log.info('closed.')

#EOF
