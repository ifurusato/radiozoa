#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-18
# modified: 2026-06-20

import asyncio
import itertools
from math import sqrt
from colorama import Fore, Style

from analog_ctrl import AnalogControl
from component import Component
from behaviour import Behaviour
from publisher import Publisher
from event import STARTUP, TOF_DISTANCES
from logger import Level
from pixel import Pixel
#from radiozoa_sensor import OUT_OF_RANGE

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
#       Behaviour.__init__(self, 'drive', message_bus, level)
#       Publisher.__init__(self, 'drive', message_bus, message_factory, level)
        Behaviour.__init__(
            self,
            name='drive',
            message_bus=message_bus,
            level=level,
            _init_base=True
        )
        Publisher.__init__(
            self,
            name='drive',
            message_bus=message_bus,
            message_factory=message_factory,
            level=level,
            _init_base=False
        )
        if config is None:
            raise TypeError('configuration argument is null.')
        _cfg = config['rros']['drive']
        self._motor_controller = motor_controller
        self._priority   = self._PRIORITY
#       self.add_event(TOF_DISTANCES)
        # analog controller ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._pin_analog = _cfg['pin_analog']
        self._startup_delay = _cfg['startup_delay'] # in seconds
        self._counter    = itertools.count()
        self._control    = AnalogControl(config)
        self._bias       = 0.0
        self._last_bias  = 0.0
        self._vx         = 0.0
        self._vy         = 0.0
        self._omega      = 0.0
        # startup callback
        self._ready_callback = None
        self._enable_task = None
        # motor control
        self._intent_vector = (self._vx, self._vy, self._omega)
        if self._motor_controller is not None:
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

    def set_ready_callback(self, callback):
        if not callable(callback):
            raise TypeError("cxpected a callback (callable)")
        self._ready_callback = callback

    async def _delayed_enable_task(self):
        self._log.info('starting delayed enable task…')
        await asyncio.sleep(self._startup_delay)
        self._start()

    def _start(self):
        '''
        After the initial delay, this starts the behaviour.
        '''
        self._log.info('😡 A. _start.')
        # publish STARTUP via message bus
        self._message_bus.publish(self._message_factory.create_message(STARTUP))
        # enable motor controller and tick loop
        self._log.info('😡 B. _start: enabled motor controller…')
        self._motor_controller.enable()
        self._log.info('😡 C. _start: start motor controller…')
        asyncio.create_task(self._motor_controller._run())
        if self._ready_callback:
            self._log.info('😡 D. _start: execute callback…')
            asyncio.create_task(self._ready_callback())
            self._ready_callback = None
        # print registry to console
        registry = Component.get_registry()
        registry.print_registry()
        asyncio.create_task(self._tick())
        self._log.info('😡 E. _start: complete.')

    async def _tick(self):
        while self.enabled:
            raw        = self._control.raw_value
            percentage = self._control.percentage_value
            scaled     = self._control.value
            # analog bias [-1.0, 1.0] is the requested speed and direction
            self._bias = round(self._control.value, 2)
            if scaled == 0.0:
#               self._log.info(Fore.BLACK + "tick() zero." + Style.RESET_ALL)
                pass
            else:
                self._log.info("tick() raw: {}; percentage: {}; ".format(raw, percentage) 
                        + Fore.GREEN
                        + "scaled: {:0.2f}".format(scaled) 
                        + Style.RESET_ALL)
            self.set_vy(scaled)
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
