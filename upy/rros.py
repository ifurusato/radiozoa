#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-07-13

import asyncio
import time
from machine import I2C

from colorama import Fore, Style

from colors import *
from pixel import Pixel
from eyeball import Eyeball
from eyeballs import Eyeballs
from orientation import Orientation
from config_loader import ConfigLoader
from component import Component
from dip_switch import DipSwitch
from logger import Logger, Level
from message_bus import MessageBus
from message_factory import MessageFactory
from motor_controller import MotorController
from drive import Drive

from radiozoa_config import RadiozoaConfig
from radiozoa_sensor import RadiozoaSensor
from tof_publisher import ToFPublisher
from radiozoa import Radiozoa

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class RROS(Component):
    NAME = 'rros'
    '''
    Radiozoa Robot Operating System. Configures sensors, constructs and wires
    all system components, and provides the main async run loop.

    :param pixel:      optional RGB LED instance for status indication
    :param ring:       optional NeoPixel ring for sensor visualisation
    :param level:      the logging level
    '''
    def __init__(self, pixel=None, ring=None, level=Level.INFO):
        self._level  = level
        Component.__init__(self, RROS.NAME, suppressed=False, enabled=False, level=self._level)
        self._config = ConfigLoader.configure('config.yaml')
        self._radiozoa_enabled = self._config['rros']['radiozoa']['enabled']
        self._roam_enabled     = self._config['rros']['roam']['enabled']
        self._drive_enabled    = self._config['rros']['drive']['enabled']
        self._eyeballs_enabled = self._config['rros']['eyeballs']['enabled']
        self._motor_controller_enabled = self._config['rros']['motor_controller']['enabled']
        self._remote_control_enabled   = self._config['rros']['remote_control']['enabled']
        self._log.info(Fore.WHITE + 'radiozoa enabled? {}; roam enabled? {}; drive enabled? {}'.format(
            self._radiozoa_enabled, self._roam_enabled, self._drive_enabled) + Style.RESET_ALL)
        self._closing = False
        # create I2C bus ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._log.info('configuring I2C bus…')
        _i2c_cfg = self._config['rros']['i2c']
        _i2c_id  = _i2c_cfg['id']
        _scl     = _i2c_cfg['scl']
        _sda     = _i2c_cfg['sda']
        _i2c_baud_rate = _i2c_cfg['baud_rate'] # 400_000
        self._i2c = I2C(_i2c_id, scl=_scl, sda=_sda, freq=_i2c_baud_rate)
        # visual indicators ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        if self._eyeballs_enabled:
            self._log.info('creating eyeballs…')
            self._eyeballs = Eyeballs(self._i2c)
            self._log.info('😨 showing OPENING 1…')
            self._eyeballs.show_eyeball(Orientation.ALL, Eyeball.OPENING_1)
            time.sleep_ms(200)
        else:
            self._eyeballs = None
        if pixel:
            self._pixel = pixel
        else:
            self._pixel = Pixel(pin=48, pixel_count=1, color_order='GRB', brightness=0.1)
        if ring:
            self._ring  = ring
        else:
            self._ring  = Pixel(pin=21, pixel_count=24, color_order='GRB', brightness=0.1)
        # message bus ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._message_bus = MessageBus(level=self._level)
        self._message_factory = MessageFactory(message_bus=self._message_bus, level=self._level)
        # objects ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self.devices        = []
        self._sensor        = None
        self._visualiser    = None
        self._tof_publisher = None
        self._radiozoa      = None
        self._roam          = None
        self._motor_ctrl    = None
        self._dip_switch    = DipSwitch()
        if self._ring is not None:
            from ring_visualiser import RingVisualiser
            self._log.info('creating ring visualiser…')
            self._visualiser = RingVisualiser(self._ring, self._message_bus, level=self._level)
            self._visualiser.set_brightness(0.2)
#           self._visualiser.set_brighten(True)
            self._visualiser.enable() # default enabled
        else:
            self._log.warn('no ring visualiser.')
            self._visualiser = None
        self._configure_radiozoa = self._radiozoa_enabled
        if self._eyeballs:
            self._eyeballs.show_eyeball(Orientation.ALL, Eyeball.OPENING_2)
            time.sleep_ms(200)
        if self._configure_radiozoa:
            # configure sensor addresses synchronously before async loop starts
            self._log.info('configuring radiozoa…')
            self._radiozoa_config = RadiozoaConfig(config=self._config, i2c=self._i2c, visualiser=self._visualiser, level=self._level)
            self._radiozoa_config.configure(self.continue_init)
        else:
            self._radiozoa_config = None
            self.continue_init()

    def continue_init(self):
        self._log.debug('continuing initialisation…')
        if self._radiozoa_config and not self._radiozoa_config.configured:
            raise RuntimeError('sensor configuration failed.')
        if self._configure_radiozoa:
            self._log.info('creating radiozoa sensor…')
            self._sensor = RadiozoaSensor(i2c=self._i2c, level=self._level)
            self._log.info('initialising device drivers…')
            self._sensor.init_device_drivers()
            self._log.info('creating publisher…')
            self._tof_publisher = ToFPublisher(self._config, self._sensor, self._message_bus, self._message_factory, level=self._level)

        if self._motor_controller_enabled:
            self._log.info('creating motor controller…')
            self._motor_ctrl = MotorController(config=self._config, visualiser=self._visualiser, level=self._level)

        if self._radiozoa_enabled:
            self._log.info('creating radiozoa behaviour…')
            self._radiozoa = Radiozoa(self._message_bus, self._motor_ctrl, level=self._level)

        if self._roam_enabled:
            from roam import Roam

            self._log.info('creating roam behaviour…')
            self._roam = Roam(self._config, self._message_bus, self._motor_ctrl, self._visualiser, level=self._level)

        if self._remote_control_enabled:
            from remote_control import RemoteControl
            from remote_control_subscriber import RemoteControlSubscriber

            self._log.info('creating remote control behaviour…')
            self._remote_control = RemoteControl(self, level=Level.INFO)
            self._remote_control.enable()

            self._log.info('creating remote control subscriber…')
            self._remote_control_subscriber = RemoteControlSubscriber(self, level=Level.INFO)
            self._remote_control_subscriber.enable()

        # simple test behaviour
        self._drive = Drive(config=self._config, message_bus=self._message_bus, message_factory=self._message_factory, motor_controller=self._motor_ctrl)
        if self._pixel:
            self._pixel.set_color(color=COLOR_DARK_CYAN)
        if self._eyeballs:
            self._eyeballs.show_eyeball(Orientation.ALL, Eyeball.OPENING_3)
            time.sleep_ms(200)
        self._log.info(Fore.GREEN + 'ready.' + Style.RESET_ALL)

    # components-as-properties ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def message_bus(self):
        return self._message_bus

    @property
    def message_factory(self):
        return self._message_factory

    @property
    def pixel(self):
        return self._pixel

    @property
    def motor_controller(self):
        return self._motor_ctrl

    @property
    def visualiser(self):
        return self._visualiser

    @property
    def drive(self):
        return self._drive

    @property
    def config(self):
        return self._config

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    async def _start(self):
        self._log.info(Fore.GREEN + 'starting…' + Style.RESET_ALL)
        if self._sensor:
            self._sensor.start_ranging()
        else:
            self._log.warn('no sensor available.')
        if self._tof_publisher:
            self._tof_publisher.enable()
        if self._radiozoa_enabled:
            self._radiozoa.enable()
        if self._roam_enabled:
            self._roam.enable()
        if self._drive_enabled:
            self._drive.enable() # after delay, drive will enable motor controller
        self._motor_ctrl.enable()
        self._pixel.set_color(color=COLOR_DEEP_CYAN)
        registry = Component.get_registry()
        self._log.info('active components:')
        registry.print_registry()
        if self._eyeballs:
            self._eyeballs.normal()
        self._log.info(Fore.GREEN + 'started.' + Style.RESET_ALL)
        self._message_bus.enable() # blocking: start message bus loop

    def enable(self):
        if not self.enabled:
            super().enable()
            asyncio.run(self._start())
        else:
            self._log.warn('already enabled.')

    # closing ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def indicate_shutdown(self):
        '''
        Performs a visual indication of shutdown.
        '''
        self._log.info('indicating shutdown…')
        if self._eyeballs:
            _eyeballs = [ Eyeball.NORMAL, Eyeball.OPENING_3, Eyeball.OPENING_2, Eyeball.OPENING_1 ]
            for _eyeball in _eyeballs:
                self._eyeballs.show_eyeball(Orientation.ALL, _eyeball)
                time.sleep_ms(500)
            self._eyeballs.clear()
            self._eyeballs.update()
        self._log.info('shutdown complete.')

    async def _close_and_execute(self):
        await self._close_open_components()
        self._execute_after_close()

    def _execute_after_close(self):
        super().close()
        registry = Component.get_registry()
        count = registry.count_open_components()
        if count > 1:
            self._log.warn('rros still has {} open components…'.format(count))
            registry.print_registry()
        else:
            self._log.info('all components closed.')
        self._log.info('closing message bus…')
        if self._message_bus:
            self._message_bus.close()
        self._pixel.set_color(color=COLOR_DARK_GREEN)
        self._log.info('message bus closed.')

    async def _close_open_components(self):
        poll_interval_ms = 5
        timeout_ms       = 20
        count = 0
        registry = Component.get_registry()
        total = len(registry.all())
        # create dict of closeable components, ignoring rros, pixel and message bus
        components = {
            key: component
            for key, component in registry.items()
            if (not component.closed
                    and component is not self
                    and component is not self._pixel
                    and component is not self._eyeballs
                    and component is not self._message_bus)
        }
        self._log.info('closing {}/{} open components…'.format(len(components), total))
        for component in components.values():
            count += 1
            name = component.name
            self._log.debug('closing {}…'.format(name))
            component.close()
            # poll closed property with a 50ms timeout
            elapsed_ms = 0
            while not component.closed and elapsed_ms < timeout_ms:
                await asyncio.sleep_ms(poll_interval_ms)
                elapsed_ms += poll_interval_ms
            if not component.closed:
                self._log.warn('timeout: component {} did not close within {}ms'.format(name, timeout_ms))
            else:
                self._log.debug('{} closed.'.format(name))

        await asyncio.sleep_ms(200)
        self._log.info('{} components closed.'.format(count))

    def close(self):
        if not self.closed and not self._closing:
            self._closing = True
            asyncio.create_task(self._close_and_execute())
            self._log.info('application closed.')
            self._closing = False
        else:
            self._log.warn('already closed.')

#EOF
