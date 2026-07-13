#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-07-08
# modified: 2026-07-10

import asyncio
from colorama import Fore, Style

from colors import *
from logger import Level
from component import Component
from touch_subscriber import TouchSubscriber
from explorer_button import ExplorerButton

class RemoteControlSubscriber(TouchSubscriber):
    NAME = 'remote-ctrl'
    '''
    A subscriber that receives TOUCH event messages and decodes their string value
    back into ExplorerButton pseudo-enum instances for further action.

    Note that this does not perform any function for the buttons used by the
    RemoteControl Behaviour.

    This is meant to be installed on both the initiator and endpoint nodes.
    '''
    def __init__(self, rros, level=Level.INFO):
        self._rros = rros
        TouchSubscriber.__init__(self,
                name        = RemoteControlSubscriber.NAME,
                config      = rros.config,
                message_bus = rros.message_bus,
                pixel       = rros.pixel,
                level       = level)
        # pay attention to all buttons except those used by Remote Control behaviour
        self._button_handlers = {
            0: self._handle_button_3,
            1: self._handle_button_2,
            2: self._handle_button_1,
            3: None,
            4: None,
            5: None,
            6: None,
            7: None,
            8: self._handle_button_b,
            9: self._handle_button_a,
            10: self._handle_button_y,
            11: self._handle_button_x,
        }
        _registry = Component.get_registry()
        self._roam = _registry.get('beh:roam')
        self._tof_publisher = _registry.get('pub:tof-pub')
        # ready.

    async def handle_button_press(self, button, message):
        '''
        Calls the corresponding button handler.
        '''
        handler = self._button_handlers.get(button.id)
        if handler is not None:
            if handler():
                # if setting pixel is desired, call superclass
                await super().handle_button_press(button, message)
        else:
            self._log.debug('unrecognised button ID: {}'.format(button.id))

    # button handlers ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _handle_button_1(self):
        '''
        Enable/disable the ring visualiser, the motor controller's and roam's
        visualiser settings.
        '''
        self._log.info('button 1: toggle radiozoa')
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
        if self._tof_publisher:
            if _enabled:
                self._tof_publisher.disable()
            else:
                self._tof_publisher.enable()
        else:
            self._log.warn('no tof publisher available.')
        return False

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
        return False

    def _handle_button_a(self):
        self._log.info('button A')
        self._rros.indicate_shutdown()
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

    # utility ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

#   def _show_color(self, color):
#   async def _flash_led(self, color, duration_ms=1000):

#EOF
