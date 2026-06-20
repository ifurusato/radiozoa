#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-06-18

from machine import I2C
import asyncio

from colorama import Fore, Style

from colors import *
from config_loader import ConfigLoader
from logger import Logger, Level
from message_bus import MessageBus
from message_factory import MessageFactory
from motor_controller import MotorController
from drive import Drive

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class RROS:
    '''
    Radiozoa Robot Operating System. Configures sensors, constructs and wires
    all system components, and provides the main async run loop.

    :param pixel:      the RGB LED instance for status indication
    :param ring:       optional NeoPixel ring for sensor visualisation
    :param level:      the logging level
    '''
    def __init__(self, pixel=None, ring=None, level=Level.INFO):
        self._log    = Logger('rros', level)
        self._level  = level
        self._config = ConfigLoader.configure('config.yaml')
        self._radiozoa_enabled = self._config['rros']['radiozoa']['enabled']
        self._roam_enabled     = self._config['rros']['roam']['enabled']
        self._drive_enabled    = self._config['rros']['drive']['enabled']
        self._log.info(Fore.WHITE + 'radiozoa enabled? {}; roam enabled? {}; drive enabled? {}'.format(
            self._radiozoa_enabled, self._roam_enabled, self._drive_enabled) + Style.RESET_ALL)
        self._pixel = pixel
        self._ring  = ring
        if self._ring:
            self._ring.set_color(3, COLOR_BLUE)
        self._message_bus = MessageBus(level=self._level)
        self._message_factory = MessageFactory(message_bus=self._message_bus, level=self._level)
        # create I2C bus ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._log.info('configuring I2C bus…')
        _i2c_cfg = self._config['rros']['i2c']
        _i2c_id  = _i2c_cfg['id']
        _scl     = _i2c_cfg['scl']
        _sda     = _i2c_cfg['sda']
        _i2c_baud_rate = _i2c_cfg['baud_rate'] # 400_000
        self._i2c = I2C(_i2c_id, scl=_scl, sda=_sda, freq=_i2c_baud_rate)

        self._sensor     = None
        self._visualiser = None
        self._publisher  = None
        self._radiozoa   = None
        self._roam       = None
        self.devices     = []

        if self._ring is not None:
            from ring_visualiser import RingVisualiser
            self._log.info('🐟 creating ring visualiser…')
            self._visualiser = RingVisualiser(self._ring, self._message_bus, level=self._level)
            self._visualiser.set_brightness(0.2)
#           self._visualiser.set_brighten(True)
        else:
            self._log.info('🐟 no ring visualiser.')
            self._visualiser = None


        self._configure_radiozoa = False
        if self._configure_radiozoa:

            from device import Device
            from radiozoa_config import RadiozoaConfig
            from radiozoa_sensor import RadiozoaSensor
            from tof_publisher import ToFPublisher
            from radiozoa_behaviour import Radiozoa

            # create device configurations ┈┈┈┈┈┈┈┈┈┈┈
            for _dev_cfg in self._config['rros']['devices']:
                _device = Device(
                    _dev_cfg['index'],
                    _dev_cfg['impl'],
                    _dev_cfg['label'],
                    _dev_cfg['address'],
                    _dev_cfg['xshut'],
                    _dev_cfg['pixel']
                )
                self.devices.append(_device)
            # configure sensor addresses synchronously before async loop starts
            self._log.info('configuring radiozoa…')
            self._radiozoa_config = RadiozoaConfig(config=self._config, i2c=self._i2c, visualiser=self._visualiser, level=self._level)
            self._radiozoa_config.configure(self.continue_init)
        else:
            self._radiozoa_config = None
            self.continue_init()

    def continue_init(self):
        if self._radiozoa_config and not self._radiozoa_config.configured:
            raise RuntimeError('sensor configuration failed.')
        if self._configure_radiozoa:
            self._log.info('creating radiozoa sensor…')
            self._sensor = RadiozoaSensor(i2c=self._i2c, level=self._level)
            self._log.info('creating publisher…')
            self._publisher = ToFPublisher(self._sensor, self._message_bus, level=self._level)

        self._log.info('creating motor controller…')
        self._motor_ctrl = MotorController(config=self._config, visualiser=self._visualiser, level=self._level)
        if self._radiozoa_enabled:
            self._log.info('creating radiozoa behaviour…')
            self._radiozoa = Radiozoa(self._message_bus, self._motor_ctrl, level=self._level)

            from roam_behaviour import Roam

            self._log.info('creating roam behaviour…')
            self._roam = Roam(self._config, self._message_bus, self._motor_ctrl, self._visualiser, level=self._level)

        # simple test behaviour
        self._drive = Drive(config=self._config, message_bus=self._message_bus, message_factory=self._message_factory, motor_controller=self._motor_ctrl)
        self._log.info(Fore.GREEN + 'ready.' + Style.RESET_ALL)

    # components-as-properties ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def message_bus(self):
        return self._message_bus

    @property
    def motor_controller(self):
        return self._motor_ctrl

    @property
    def drive(self):
        return self._drive

    @property
    def config(self):
        return self._config

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    async def run(self):
        self._message_bus.enable()
        if self._publisher:
            self._publisher.enable()
        if self._radiozoa_enabled:
            self._radiozoa.enable()
        if self._roam_enabled:
            self._roam.enable()
        if self._drive_enabled:
            self._drive.enable() # after delay, drive will enable motor controller
#       self._motor_ctrl.enable()
        if self._visualiser:
            self._log.info('enabling ring visualiser…')
            self._visualiser.enable()
        if self._sensor:
            self._sensor.start_ranging()
        asyncio.create_task(self._message_bus.consume_loop())
        if self._publisher:
            asyncio.create_task(self._publisher.poll_loop())
#       asyncio.create_task(self._motor_ctrl._run())
        self._log.info(Fore.GREEN + 'running…' + Style.RESET_ALL)

        # yield control to the event loop so scheduled tasks can begin execution
#       await asyncio.sleep_ms(0)
        while True:
            await asyncio.sleep_ms(100)

    def start(self):
        asyncio.run(self.run())

    def close(self):
        if self._visualiser:
            self._visualiser.close()
        if self._motor_ctrl:
            self._motor_ctrl.close()
        if self._publisher:
            self._publisher.close()
        if self._roam:
            self._roam.close()
        if self._radiozoa:
            self._radiozoa.close()
        if self._message_bus:
            self._message_bus.close()
        if self._ring:
            self._ring.set_color(3, COLOR_BLACK)

#EOF
