#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-07
# modified: 2026-06-20

import asyncio

from colorama import Fore, Style

from logger import Level
from component import Component
from orientation import Orientation
from pixel import Pixel
from motor import Motor
from pid import PID

class MotorController(Component):
    NAME = 'motor-ctrl'
    '''
    Owns the two drive motors (port and starboard) and their PID controllers.
    Blends registered intent vectors from Behaviours by priority weighting,
    applies slew limiting, folds lateral intent (vx) into rotation via
    lateral_gain, then drives the motors.

    In closed loop mode, blended normalised values are scaled to mm/s and
    fed to per-motor PID controllers whose output is passed to Motor.set_power().
    In open loop mode, normalised values are passed directly to Motor.set_power().

    Velocity is measured from encoder step deltas each tick. SI unit commands
    and odometry queries are available via set_linear_velocity() and
    get_distance_mm() using Orientation to select port, starboard, or both.

    Intended to be run as an asyncio task via _run(), registered by RROS.

    :param config:       the configuration dict
    :param visualiser:   optional NeoPixel ring for motor speed visualisation
    :param level:        the logging level
    '''
    # wheel geometry and encoder constants (must match Motor)
    _WHEEL_DIAMETER_MM = 59.0
    _ENCODER_CPR       = 121.12
    _CIRCUMFERENCE     = 3.14159265 * _WHEEL_DIAMETER_MM
    _MM_PER_TICK       = _CIRCUMFERENCE / _ENCODER_CPR
    _TICKS_PER_MM      = _ENCODER_CPR / _CIRCUMFERENCE
    # closed-loop operating boundaries in cps
    _MIN_CPS           = 50.0
    _MAX_CPS           = 520.0
    # maximum operational velocity in mm/s (corresponds to normalised 1.0)
    _MAX_VELOCITY_MMS  = _MAX_CPS * _MM_PER_TICK
    # integral clamp
    _INTEGRAL_LIMIT    = 15.0

    def __init__(self, config=None, visualiser=None, level=Level.INFO):
        Component.__init__(self, MotorController.NAME)
        if config is None:
            raise TypeError('no configuration provided.')
        _cfg = config['rros']['motor_controller']
        self._visualiser           = visualiser
        self._deadband             = config['rros']['analog_control']['deadband']
        # configuration ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._visualise_hue        = True
        self._hue_angle            = 0.875
        self._period_ms            = _cfg['period_ms']
        # ring pixels for motor speed visualisation ┈┈┈┈┈┈┈┈
        self._pin_port_pix1        = _cfg['pin_port_pix1']
        self._pin_port_pix2        = _cfg['pin_port_pix2']
        self._pin_stbd_pix1        = _cfg['pin_stbd_pix1']
        self._pin_stbd_pix2        = _cfg['pin_stbd_pix2']
        # motor pins ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._pin_in1              = _cfg['pin_in1']
        self._pin_in2              = _cfg['pin_in2']
        self._pin_in3              = _cfg['pin_in3']
        self._pin_in4              = _cfg['pin_in4']
        self._log.info(Fore.WHITE + 'motor pins: in1={}; in2={}; in3={}; in4={}'.format(
                self._pin_in1, self._pin_in2, self._pin_in3, self._pin_in4))
        self._pin_enc1a            = _cfg['pin_enc1A']
        self._pin_enc1b            = _cfg['pin_enc1B']
        self._pin_enc2a            = _cfg['pin_enc2A']
        self._pin_enc2b            = _cfg['pin_enc2B']
        self._log.info(Fore.WHITE + 'motor encoders: enc1A={}; enc1B={}; enc2A={}; enc2B={}'.format(
                self._pin_enc1a, self._pin_enc1b, self._pin_enc2a, self._pin_enc2b))
        # motors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._motor_port = Motor(
                Orientation.PORT,
                in1_pin=self._pin_in1,
                in2_pin=self._pin_in2,
                enc_a_pin=self._pin_enc1a,
                enc_b_pin=self._pin_enc1b,
                level=level)
        self._motor_stbd = Motor(Orientation.STBD,
                in1_pin=self._pin_in3,
                in2_pin=self._pin_in4,
                enc_a_pin=self._pin_enc2a,
                enc_b_pin=self._pin_enc2b,
                reverse_encoder=True,
                level=level)
        # PID controllers ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        _pid_cfg = _cfg['pid']
        _kp                        = _pid_cfg['kp']      # 0.25
        _ki                        = _pid_cfg['ki']      # 0.18
        _kd                        = _pid_cfg['kd']      # 0.003
        self._pid_port             = PID(name=Orientation.PORT.name, kp= _kp, ki=_ki, kd=_kd)
        self._pid_stbd             = PID(name=Orientation.STBD.name, kp= _kp, ki=_ki, kd=_kd)
        self._callback             = None
        self._condition            = True # or a lambda function
        self._one_shot             = False
        self._stopping             = False
        # feed-forward gain ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._kff                  = _pid_cfg['kff']     # 0.6, was 0.175
        # PID setpoints in mm/s ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._setpoint_port        = 0.0
        self._setpoint_stbd        = 0.0
        # intent vectors registry ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._intent_vectors       = {}
        # lateral gain ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._lateral_gain         = 0.5
        # step tracking for velocity measurement ┈┈┈┈┈┈┈┈┈┈┈┈
        self._last_steps_port      = 0
        self._last_steps_stbd      = 0
        # measured velocities in mm/s ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._velocity_port        = 0.0
        self._velocity_stbd        = 0.0
        # visualiser ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        _registry = Component.get_registry()
        if _registry and self._visualiser is None:
            self._visualiser = _registry.get('visualiser')
        if self._visualiser:
            self._log.info(Fore.WHITE + 'ring visualiser available.')
        else:
            self._log.warn('no ring visualiser available.')
        # slew limits ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        _slew_cfg = _cfg['slew']
        self._slew_vy              = _slew_cfg['vy']   # 0.20
        self._slew_omega           = _slew_cfg['omega']   # 0.20
#       self._slew_vy              = 0.20
#       self._slew_omega           = 0.20
        self._last_vy              = 0.0
        self._last_omega           = 0.0
        # closed loop mode from config ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._closed_loop          = _cfg['closed_loop']
        self._stop                 = False
        self._log.info('{} closed-loop mode.'.format('enabled' if self._closed_loop else 'disabled'))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

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

    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._motor_port
        elif orientation is Orientation.STBD:
            return self._motor_stbd
        else:
            raise ValueError('unsupported orientation: use PORT or STBD.')

    def set_callback(self, callback=None, condition=True, one_shot=False):
        '''
        Sets a callback executed upon each tick.
        If the condition is passed (as a lambda) it will be evaluated as a filter.
        If one_shot is True it will only be executed once.
        '''
        if not callable(callback):
            raise TypeError("cxpected a callback (callable)")
        self._callback = callback
        self._condition = condition
        self._one_shot = one_shot

    # intent vectors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

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
        non-contributing behaviours do not dilute the result.
        Returns a (vx, vy, omega) tuple.

        Returns zeroes if the stopping flag is True. If it would return
        zeroes, sets the stopping flag to False. This keeps the robot
        stopped until all intent vectors stop trying to move the robot.
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
            if self._stopping:
                self.reset_odometry(Orientation.ALL)
                self._stopping = False
            return (0.0, 0.0, 0.0)
        elif self._stopping:
            return (0.0, 0.0, 0.0)
        return (vx / total_p, vy / total_p, omega / total_p)

    def _slew(self, current, target, max_change):
        diff = target - current
        if diff >  max_change: return current + max_change
        elif diff < -max_change: return current - max_change
        return target

    # SI unit interface ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def set_linear_velocity(self, orientation, velocity_mms):
        '''
        Sets the target velocity in mm/s for the specified motor(s).
        Use Orientation.PORT, Orientation.STBD, or Orientation.ALL.
        '''
        _normalised = float(velocity_mms) / self._MAX_VELOCITY_MMS
        if _normalised >  1.0: _normalised =  1.0
        elif _normalised < -1.0: _normalised = -1.0
        if orientation is Orientation.PORT or orientation is Orientation.ALL:
            self._pid_port.setpoint = _normalised
        if orientation is Orientation.STBD or orientation is Orientation.ALL:
            self._pid_stbd.setpoint = _normalised

    def get_velocity(self, orientation):
        '''
        Returns the most recently measured velocity in mm/s for the specified motor.
        '''
        if orientation is Orientation.PORT:
            return self._velocity_port
        elif orientation is Orientation.STBD:
            return self._velocity_stbd
        else:
            raise ValueError('unsupported orientation: use PORT or STBD.')

    def get_steps(self, orientation):
        '''
        Returns the step count since last reset for the specified motor. Use Orientation.PORT,
        Orientation.STBD, or Orientation.ALL (returns a tuple of both values).
        '''
        if orientation is Orientation.PORT:
            return self._motor_port.steps
        elif orientation is Orientation.STBD:
            return self._motor_stbd.steps
        elif orientation is Orientation.ALL:
            return self._motor_port.steps, self._motor_stbd.steps
        else:
            raise ValueError('unsupported orientation: {}'.format(orientation.name))

    def get_distance_mm(self, orientation):
        '''
        Returns the net distance traveled in mm since last reset for the specified motor. Use
        Orientation.PORT, Orientation.STBD, or Orientation.ALL (returns a tuple of both values).
        '''
        if orientation is Orientation.PORT:
            return self._motor_port.get_distance_mm()
        elif orientation is Orientation.STBD:
            return self._motor_stbd.get_distance_mm()
        elif orientation is Orientation.ALL:
            return self._motor_port.get_distance_mm(), self._motor_stbd.get_distance_mm()
        else:
            raise ValueError('unsupported orientation: {}'.format(orientation.name))

    def reset_odometry(self, orientation):
        '''
        Resets the odometry for the specified motor(s).
        Use Orientation.PORT, Orientation.STBD, or Orientation.ALL.
        '''
        self._stopping = False
        if orientation is Orientation.PORT or orientation is Orientation.ALL:
            self._motor_port.reset_odometry()
            self._last_steps_port = 0
        if orientation is Orientation.STBD or orientation is Orientation.ALL:
            self._motor_stbd.reset_odometry()
            self._last_steps_stbd = 0

    # control loop ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _tick(self):
        '''
        Single control iteration: blend intent vectors, apply slew limiting,
        fold vx into omega, apply differential kinematics, measure velocity,
        drive motors via PID (closed loop) or direct power (open loop),
        and update ring visualisation.

        If a callback has been set it is executed at the end of this method.
        If it is a one shot it is executed a single time.
        '''
#       self._log.info('steps port={}, stbd={}, vel_port={:.1f}, vel_stbd={:.1f}'.format(self._motor_port.steps, self._motor_stbd.steps, self._velocity_port, self._velocity_stbd))
        vx, vy, omega = self._blend_intent_vectors()
        # slew limiting
        vy    = self._slew(self._last_vy,    vy,    self._slew_vy)
        omega = self._slew(self._last_omega, omega, self._slew_omega)
        self._last_vy    = vy
        self._last_omega = omega
        # fold lateral intent into rotation
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
        # velocity measurement from step deltas
        _steps_port           = self._motor_port.steps
        _steps_stbd           = self._motor_stbd.steps
        _delta_port           = _steps_port - self._last_steps_port
        _delta_stbd           = _steps_stbd - self._last_steps_stbd
        self._last_steps_port = _steps_port
        self._last_steps_stbd = _steps_stbd
        _ticks_per_sec        = 1000.0 / self._period_ms
        self._velocity_port   = _delta_port * _ticks_per_sec * self._MM_PER_TICK
        self._velocity_stbd   = _delta_stbd * _ticks_per_sec * self._MM_PER_TICK
#       self._log.info(Fore.MAGENTA + 'delta port={}, stbd={}, vel_port={:.1f}, vel_stbd={:.1f}'.format(_delta_port, _delta_stbd, self._velocity_port, self._velocity_stbd))
        # motor drive
        if self._closed_loop:
            _norm_vel_port          = self._velocity_port / self._MAX_VELOCITY_MMS
            _norm_vel_stbd          = self._velocity_stbd / self._MAX_VELOCITY_MMS
            self._pid_port.setpoint = v_port
            self._pid_stbd.setpoint = v_stbd
            ff_port  = self._kff * v_port
            ff_stbd  = self._kff * v_stbd
            pid_port = self._pid_port(_norm_vel_port)
            pid_stbd = self._pid_stbd(_norm_vel_stbd)
            pwr_port = ff_port + pid_port
            pwr_stbd = ff_stbd + pid_stbd
            if pwr_port >  1.0: pwr_port =  1.0
            elif pwr_port < -1.0: pwr_port = -1.0
            if pwr_stbd >  1.0: pwr_stbd =  1.0
            elif pwr_stbd < -1.0: pwr_stbd = -1.0
        else:
            pwr_port = v_port
            pwr_stbd = v_stbd
        self._motor_port.set_power(pwr_port)
        self._motor_stbd.set_power(pwr_stbd)
        # odometry ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._log.info('port: {:.1f}mm/s {:.1f}mm | stbd: {:.1f}mm/s {:.1f}mm; '.format(
                self._velocity_port, self._motor_port.get_distance_mm(), 
                self._velocity_stbd, self._motor_stbd.get_distance_mm()) 
                + Fore.BLUE + 'port: {} steps, stbd: {} steps.'.format(self._motor_port.steps, self._motor_stbd.steps))
        # ring visualisation ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        if self._visualiser:
            if abs(v_port) < self._deadband:
                rgb_port = (0, 0, 0)
            else:
                hue_port = (v_port + 1.0) / 4.0
                rgb_port = Pixel.hsv_to_rgb(hue_port, 1.0, abs(v_port))
            if abs(v_stbd) < self._deadband:
                rgb_stbd = (0, 0, 0)
            else:
                hue_stbd = (v_stbd + 1.0) / 4.0
                rgb_stbd = Pixel.hsv_to_rgb(hue_stbd, 1.0, abs(v_stbd))
            if self._pin_port_pix1:
                self._visualiser.set_color(self._pin_port_pix1, rgb_port)
            if self._pin_port_pix2:
                self._visualiser.set_color(self._pin_port_pix2, rgb_port)
            if self._pin_stbd_pix1:
                self._visualiser.set_color(self._pin_stbd_pix1, rgb_stbd)
            if self._pin_stbd_pix2:
                self._visualiser.set_color(self._pin_stbd_pix2, rgb_stbd)
        if self._callback and self._condition():
            self._log.info(Fore.WHITE + Style.BRIGHT + 'execute callback…')
            if self._one_shot:
                _callback = self._callback
                self._callback = None
                asyncio.create_task(_callback()) # asynchronous
#               _callback() # synchronous
            else:
                asyncio.create_task(self._callback()) # asynchronous
#               self._callback() # synchronous

    async def _run(self):
        '''
        main asyncio coroutine, to be added as a task by RROS.
        runs _tick() at period_ms intervals while enabled and not suppressed.
        '''
        while not self._stop:
            if self.enabled and not self.suppressed:
                self._tick()
            await asyncio.sleep_ms(self._period_ms)

    # motor commands ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def brake(self):
        '''
        Applies active braking to both motors and resets PID and slew state.
        '''
        if self.enabled:
            self._stopping = True
            self._motor_port.brake()
            self._motor_stbd.brake()
            self._pid_port.reset()
            self._pid_stbd.reset()
            self._last_vy    = 0.0
            self._last_omega = 0.0

    def coast(self):
        '''
        Coasts both motors to a stop.
        '''
        if self.enabled:
            self._stopping = True
            self._motor_port.coast()
            self._motor_stbd.coast()

    def enable(self):
        if not self.enabled:
            self._motor_port.enable()
            self._motor_stbd.enable()
            Component.enable(self)
            self._log.info('enabled.')

    def disable(self):
        if self.enabled:
            self.coast()
            self._motor_port.disable()
            self._motor_stbd.disable()
            Component.disable(self)
            self._log.info('disabled.')

    def close(self):
        if not self.closed:
            self._stop = True
            self.coast()
            self._motor_port.close()
            self._motor_stbd.close()
            if self._visualiser:
                self._visualiser.off(self._pin_port_pix1)
                self._visualiser.off(self._pin_port_pix2)
                self._visualiser.off(self._pin_stbd_pix1)
                self._visualiser.off(self._pin_stbd_pix2)
            Component.close(self)
            self._log.info('closed.')

#EOF
