#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-18
# modified: 2026-07-03

import asyncio
import itertools
from math import sqrt
from colorama import Fore, Style

from pixel import Pixel
from colors import *
from component import Component
from orientation import Orientation
from logger import Level
from event import STARTUP, TOF_DISTANCES
from analog_ctrl import AnalogControl
from behaviour import Behaviour
from publisher import Publisher

OUT_OF_RANGE = 9999

class Drive(Behaviour, Publisher):
    '''
    A simple Behaviour that after a startup delay publishes a STARTUP message,
    enables the motor controller, then sets the vy intent vector from a value
    obtained from the analog pot.

    vx and omega are always 0.0.

    :param message_bus:      the message bus
    :param message_factory:  the message factory
    :param motor_controller: the MotorController instance
    :param level:            the logging level
    '''
    _D_MIN    = 150.0   # stop threshold in mm
    _D_MAX    = 800.0   # full-speed threshold in mm
    _D_RANGE  = _D_MAX - _D_MIN

    _PRIORITY = 0.4     # fixed; below RadiozoaBehaviour's maximum
    _DEADBAND = 0.02

    def __init__(self, config=None, message_bus=None, message_factory=None, motor_controller=None, level=Level.INFO):
        Behaviour.__init__(self, name='drive', message_bus=message_bus, level=level, _init_base=True)
        Publisher.__init__(self, name='drive', message_bus=message_bus, message_factory=message_factory, level=level, _init_base=False)
        if config is None:
            raise TypeError('configuration argument is null.')
        _cfg = config['rros']['drive']
        self._motor_controller = motor_controller
        self._priority    = self._PRIORITY
        self._verbose     = False
#       self.add_event(TOF_DISTANCES)
        # get pixel ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        _registry = Component.get_registry()
        self._pixel       = _registry.get('pixel:1')
        self._rros        = _registry.get('rros')
        # analog controller ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._pin_analog  = _cfg['pin_analog']
        self._startup_delay = _cfg['startup_delay'] # in seconds
        self._counter     = itertools.count()
        self._control     = AnalogControl(config)
        self._bias        = 0.0
        self._last_bias   = 0.0
        # intent vector ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._vx          = 0.0
        self._vy          = 0.0
        self._omega       = 0.0
        self._last_scaled = 0.0
        # external and limit callbacks ┈┈┈┈┈┈┈┈┈┈┈
        self._ext_callback      = None
        self._enable_task       = None
        self._use_step_limit    = True
        self._step_limit        = 4456 # steps per meter
        self._distance_limit_mm = 4456.0 # 1m
        # motor control ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._intent_vector = (self._vx, self._vy, self._omega)
        if self._motor_controller:
            self._motor_controller.add_intent_vector(
                'drive',
                lambda: self._intent_vector,
                lambda: self._priority)
        else:
            self._log.warn('no motor controller available.')
        self._log.info('ready.')

    def enable(self):
        super().enable()
        if self._enable_task:
            self._enable_task.cancel()
        self._enable_task = asyncio.create_task(self._delayed_enable_task())

    def set_callback(self, callback):
        '''
        Sets a callback executed upon _start.
        '''
        if not callable(callback):
            raise TypeError("cxpected a callback (callable)")
        self._ext_callback = callback

    async def _delayed_enable_task(self):
        self._log.info('starting delayed enable task…')
        await asyncio.sleep(self._startup_delay)
        self._start()

    async def _limit_callback(self):
        '''
        The callback added to MotorController. This is called once upon reaching either the
        step or distance limit.
        '''
        if self._use_step_limit:
            _steps = self._motor_controller.get_steps(Orientation.ALL)
            self._log.info(Fore.WHITE + Style.BRIGHT + "OVER " + Fore.MAGENTA + Style.NORMAL 
                    + 'step limit callback: port={} steps; stbd={} steps'.format(_steps[0], _steps[1]))
        else:
            _distances = self._motor_controller.get_distance_mm(Orientation.ALL)
            self._log.info(Fore.WHITE + Style.BRIGHT + "OVER " + Fore.MAGENTA + Style.NORMAL 
                    + 'limit callback: port={}mm; stbd={}mm'.format(_distances[0], _distances[1]))
        self._motor_controller.coast()
        if self._rros:
            # shut down if limit reached
            self._log.info(Fore.WHITE + 'shutting down…' + Style.RESET_ALL)
            await asyncio.sleep_ms(1000)
            self._rros.close()

    def _step_limit_reached(self):
        _steps = self._motor_controller.get_steps(Orientation.ALL)
        return _steps[0] >= self._step_limit or _steps[1] >= self._step_limit

    def _distance_limit_reached(self):
        _distances = self._motor_controller.get_distance_mm(Orientation.ALL)
        return _distances[0] >= self._distance_limit_mm or _distances[1] >= self._distance_limit_mm

    def _start(self):
        '''
        After the initial delay, this starts the behaviour.
        '''
        self._log.info(Fore.GREEN + 'starting…')
        # publish STARTUP via message bus
        self._message_bus.publish(self._message_factory.create_message(STARTUP))
        # set limit callback on motor controller, either distance in mm or ticks
        if self._use_step_limit:
            _condition = self._step_limit_reached
        else:
            _condition = self._distance_limit_reached
        if self._motor_controller:
            self._motor_controller.set_callback(callback=self._limit_callback, condition=_condition, one_shot=True)
            # enable motor controller and tick loop
            self._log.info('_start: enabled motor controller…')
            self._motor_controller.enable()
            self._log.info('_start: run motor controller loop…')
            asyncio.create_task(self._motor_controller._run())
        if self._ext_callback:
            self._log.info('_start: execute callback…')
            asyncio.create_task(self._ext_callback())
            self._ext_callback = None # one-shot
        # print registry to console
        registry = Component.get_registry()
        registry.print_registry()
        asyncio.create_task(self._tick())
        self._pixel.set_color(color=COLOR_DARK_GREEN)
        self._log.info('_start: complete.')

    async def _tick(self):
        while self.enabled:
            raw        = self._control.raw_value
            percentage = self._control.percentage_value
            scaled     = self._control.value
            # analog bias [-1.0, 1.0] is the requested speed and direction
            self._bias = round(self._control.value, 2)
            if self._verbose and self._last_scaled != scaled:
                if scaled == 0.0:
                    self._log.info(Fore.BLACK + "tick() zero." + Style.RESET_ALL)
                    pass
                else:
                    self._log.info("tick() raw: {}; percentage: {}; ".format(raw, percentage) 
                            + Fore.GREEN + "scaled: {:0.2f}".format(scaled) + Style.RESET_ALL)
            self.set_vy(scaled)
            self._last_scaled  = scaled
            await asyncio.sleep(0.334)

    # ................................................................

    def set_vx(self, vx):
#       self._log.info(Fore.BLACK + 'vx: {}'.format(vx) + Style.RESET_ALL)
        self._vx = vx
        self._intent_vector = (self._vx, self._vy, self._omega)

    def set_vy(self, vy):
#       self._log.info(Fore.BLACK + 'vy: {}'.format(vy) + Style.RESET_ALL)
        self._vy = vy
        self._intent_vector = (self._vx, self._vy, self._omega)

    def set_omega(self, omega):
#       self._log.info(Fore.BLACK + 'omega: {}'.format(omega) + Style.RESET_ALL)
        self._omega = omega
        self._intent_vector = (self._vx, self._vy, self._omega)

#   @property
#   def intent_vector(self):
#       return self._intent_vector

    async def process_message(self, message):
        '''
        A stub method to process an incoming message.
        '''
        self._log.info('🤡 process message: {}'.format(message))

#EOF
