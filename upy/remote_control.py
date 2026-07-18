#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-07-10
# modified: 2026-07-18

import asyncio
from colorama import Fore, Style

from component import Component
from event import TOUCH
from colors import *
from logger import Logger, Level
from orientation import Orientation
from behaviour import Behaviour
from explorer_button import ExplorerButton

class RemoteControl(Behaviour):
    NAME     = 'remote'
    PRIORITY = 0.6
    STEP     = 0.1
    PORT     = 1
    STBD     = 2
    UP       = 3
    DOWN     = 4
    '''
    Behaviour that responds to discrete gamepad messages to:

    * enable/disable the Radiozoa sensor
    * enable/disable the motor controller
    * update the intent vector (vy for forward/back, omega for 
      rotation) of the MotorController
    * shut down RROS

    :param rros:    the RROS instance
    :param level:   the log level
    '''
    def __init__(self, rros, level=Level.INFO):
        self._rros = rros
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
        self.add_event(TOUCH)
        # handlers for Explorer buttons
        self._button_handlers = {
            0:  self._handle_button_3,   # shut down RROS
            1:  self._handle_button_2,   # enable/disable motor controller
            2:  self._handle_button_1,   # enable/disable radiozoa
            3:  self._handle_button_dn,  # slow down
            4:  self._handle_button_lt,  # rotate left
            5:  self._handle_button_rt,  # rotate right
            6:  self._handle_button_4,   # zero motors
            7:  self._handle_button_up,  # speed up
            8:  self._handle_button_b,   #
            9:  self._handle_button_a,   #
            10: self._handle_button_y,   #
            11: self._handle_button_x    #
        }
        self._led_task = None
        # intent vector ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._vx    = 0.0
        self._vy    = 0.0
        self._omega = 0.0
        self._intent_vector = (self._vx, self._vy, self._omega)
        self._priority = self.PRIORITY
        # components ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        _registry = Component.get_registry()
        self._roam = _registry.get('beh:roam')
        self._eyeballs = _registry.get('eyeballs')
        self._tof_publisher = _registry.get('pub:tof-pub')
        self._log.info('ready.')

    def _update_vector(self, name):
        self._intent_vector = (self._vx, self._vy, self._omega)
        self._log.info('intent updated by {}: '.format(name) + Fore.GREEN + '{}'.format(self._intent_vector))

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
                self._led_task = asyncio.create_task(self._flash_led(color=button.color, eyeball=button.eyeball, duration_ms=1000))
        else:
            self._log.debug('unrecognised button ID: {}'.format(button.id))

    # button handlers ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _handle_button_1(self):
        '''
        Enable/disable the ring visualiser, the motor controller's and roam's
        visualiser settings, and the eyeballs display.
        '''
        self._log.info('button 1: toggle radiozoa')
        if self._led_task is not None:
            self._led_task.cancel()
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

        if self._eyeballs:
            if _enabled:
                self._eyeballs.off();
            else:
                self._eyeballs.normal();

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
        if self._tof_publisher:
            if _enabled:
                self._tof_publisher.disable()
            else:
                self._tof_publisher.enable()
        else:
            self._log.warn('no tof publisher available.')
        return True

    def _handle_button_2(self):
        self._log.info('button 2: toggle motor controller.')
        _motor_controller = self._rros.motor_controller
        if _motor_controller.enabled:
            _motor_controller.disable()
        else:
            _motor_controller.enable()
        return True

    def _handle_button_3(self):
        self._log.info('button 3: close rros.')
        self._rros.close()
        return True

    def _handle_button_4(self):
        self._log.info('button 4: zero intent vector')
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0
        self._update_vector('zero')
        return True

    def _handle_button_up(self):
        self._log.info('button UP')
        self._vy = min(1.0, self._vy + self.STEP)
        self._update_vector('up')
        return True

    def _handle_button_dn(self):
        self._log.info('button DN')
        self._vy = max(-1.0, self._vy - self.STEP)
        self._update_vector('down')
        return True

    def _handle_button_lt(self):
        self._log.info('button LT')
        self._omega = max(-1.0, self._omega - self.STEP)
        self._update_vector('left')
        return True

    def _handle_button_rt(self):
        self._log.info('button RT')
        self._omega = min(1.0, self._omega + self.STEP)
        self._update_vector('right')
        return True

    def _handle_button_a(self):
        self._log.info('button A')
        return True

    def _handle_button_b(self):
        self._log.info('button B')
        self._vy = 0.8
        self._update_vector('up=0.8')
        return True

    def _handle_button_x(self):
        self._log.info('button X')
        return True

    def _handle_button_y(self):
        self._log.info('button Y')
        return True

    def enable(self):
        if self.disabled:
            if self._motor_controller:
                self._motor_controller.add_intent_vector(
                    RemoteControl.NAME,
                    lambda: self._intent_vector if self.is_active else (0.0, 0.0, 0.0),
                    lambda: self._priority)
            super().enable()
            self._log.info('enabled.')
        else:
            self._log.warn('already enabled.')

    def disable(self):
        if self.enabled:
            if self._motor_controller:
                self._motor_controller.remove_intent_vector(RemoteControl.NAME)
            self.clear_events()
            if self._led_task:
                self._led_task.cancel()
            super().disable()
            self._log.info('disabled.')
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

    async def _flash_led(self, color=None, eyeball=None, duration_ms=1000):
        '''
        Asynchronously set the color of the pixel and the eyeball display
        for a specified period of time, then return to black.
        '''
        try:
            self._show_color(color)
            if self._eyeballs and eyeball:
                self._eyeballs.show_eyeball(Orientation.ALL, eyeball)
            await asyncio.sleep_ms(duration_ms)
        except asyncio.CancelledError:
            pass
        finally:
            self._show_color(COLOR_BLACK)
            if self._eyeballs and eyeball:
                self._eyeballs.off()

#EOF
