#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-07-10
# modified: 2026-07-13

import asyncio
from colorama import Fore, Style

from logger import Logger, Level
from event import TOUCH
from colors import *
from behaviour import Behaviour
from explorer_button import ExplorerButton

class RemoteControl(Behaviour):
    NAME      = 'remote'
    _PRIORITY = 0.6
    _STEP     = 0.1
    '''
    Behaviour that responds to discrete gamepad messages to update the intent
    vector (vy for forward/back, omega for rotation) of the MotorController.

    :param rros:    the RROS instance
    :param level:   the log level
    '''
    def __init__(self, rros, level=Level.INFO):
        self._motor_controller = rros.motor_controller
        self._pixel = rros.pixel
        Behaviour.__init__(
                self,
                name=RemoteControl.NAME,
                message_bus=rros.message_bus,
                suppressed=False,
                enabled=False,
                level=level,
                _init_base=True)
        _cfg = rros.config['rros']['remote_control']
        self._vx    = 0.0
        self._vy    = 0.0
        self._omega = 0.0
        self._intent_vector = (self._vx, self._vy, self._omega)
        self.add_event(TOUCH)
        # only pay attention to UP, DN, LT, RT and 4.
        self._button_handlers = {
            0: None,                    1: None,                    2: None,
            3: self._handle_button_dn,  4: self._handle_button_lt,  5: self._handle_button_rt,
            6: self._handle_button_4,   7: self._handle_button_up,  8: None,
            9: None,                   10: None,                   11: None
        }
        if self._motor_controller:
            self._motor_controller.add_intent_vector(
                RemoteControl.NAME,
                lambda: self._intent_vector,
                lambda: self._PRIORITY
            )
        self._led_task = None
        self._log.info('ready.')

    def _update_vector(self):
        self._intent_vector = (self._vx, self._vy, self._omega)
        self._log.info('intent updated: {}'.format(self._intent_vector))

    async def process_message(self, message):
        '''
        Decodes the message payload back into an ExplorerButton instance.
        '''
        self._log.info('process message: ' 
                + Fore.GREEN + '{}'.format(message.id)
                + Fore.CYAN + '; value; '
                + Fore.GREEN + '{}'.format(message.value)
            )
        button_name = message.value
        button = ExplorerButton.by_name(button_name)
        if button is not None:
            await self.handle_button_press(button, message)
        else:
            self._log.error('received unknown button name payload: {}'.format(button_name))

    async def handle_button_press(self, button, message):
        '''
        Calls the corresponding button handler, which returns True or False
        for each handler, if True flashes the pixel.
        '''
        handler = self._button_handlers.get(button.id)
        if handler is not None:
            if handler():
                if self._led_task:
                    self._led_task.cancel()
                self._led_task = asyncio.create_task(self._flash_led(button.color, 1000))
        else:
            self._log.debug('unrecognised button ID: {}'.format(button.id))

    # button handlers ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _handle_button_1(self):
        '''
        Enable/disable the ring visualiser, the motor controller's and roam's
        visualiser settings.
        '''
        self._log.info('button 1')
        if self._led_task is not None:
            self._led_task.cancel()
        self._led_task = asyncio.create_task(self._flash_led(COLOR_PEAR, 2000))
        _visualiser = self._rros.visualiser
        _enabled = _visualiser.enabled
        if _visualiser:
            if _enabled:
                _visualiser.disable()
                self._log.info('button 1: visualiser disabled.')
            else:
                _visualiser.enable()
                self._log.info('button 1: visualiser enabled.')
        else:
            self._log.warn('no visualiser available.')
        # disable the motor controller's visualiser
        _motor_controller = self._rros.motor_controller
        if _motor_controller:
            _motor_controller.visualise = not _enabled
            self._log.info('button 1: motor controller visualiser {}.'.format('disabled' if _enabled else 'enabled'))
        else:
            self._log.warn('no motor controller available.')
        # disable roam's visualiser
        if self._roam:
            self._roam.visualise = not _enabled
            self._log.info('button 1: roam visualiser {}.'.format('disabled' if _enabled else 'enabled'))
        else:
            self._log.warn('no roam behaviour available.')
        return False

    def _handle_button_2(self):
        self._log.info('button 2')
        return True

    def _handle_button_3(self):
        self._log.info('button 3')
        return True

    def _handle_button_4(self):
        self._log.info('button 4')
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0
        self._update_vector()
        return True

    def _handle_button_up(self):
        self._log.info('button UP')
        self._vy = min(1.0, self._vy + self._STEP)
        self._update_vector()
        return True

    def _handle_button_dn(self):
        self._log.info('button DN')
        self._vy = max(-1.0, self._vy - self._STEP)
        self._update_vector()
        return True

    def _handle_button_lt(self):
        self._log.info('button LT')
        self._omega = max(-1.0, self._omega - self._STEP)
        self._update_vector()
        return True

    def _handle_button_rt(self):
        self._log.info('button RT')
        self._omega = min(1.0, self._omega + self._STEP)
        self._update_vector()
        return True

    def _handle_button_a(self):
        self._log.info('button A')
        return True

    def _handle_button_b(self):
        self._log.info('button B')
        return True

    def _handle_button_x(self):
        self._log.info('button X')
        return True

    def _handle_button_y(self):
        self._log.info('button Y')
        return True

    def disable(self):
        if self.enabled:
            self.clear_events()
            if self._led_task:
                self._led_task.cancel()
            self._log.debug('disabled.')
            super().disable()
        else:
            self._log.warn('already disabled.')

    def close(self):
        if not self.closed:
            super().close()
            self._log.debug('closed.')
        else:
            self._log.warn('already closed.')

    # utility ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _show_color(self, color):
        '''
        Set the color of the pixel.
        '''
        if self._pixel:
            self._pixel.show_color(color)

    async def _flash_led(self, color, duration_ms=1000):
        '''
        Asynchronously set the color of the pixel for a specified
        period of time, then return to black.
        '''
        try:
            self._show_color(color)
            await asyncio.sleep_ms(duration_ms)
        except asyncio.CancelledError:
            pass
        finally:
            self._show_color(COLOR_BLACK)

#EOF
