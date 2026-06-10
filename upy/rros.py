#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-06-04

from machine import I2C
import asyncio

from colorama import Fore, Style

from config_loader import ConfigLoader
from logger import Logger, Level
from device import Device
from message_bus import MessageBus
from radiozoa_config import RadiozoaConfig
from radiozoa_sensor import RadiozoaSensor
from tof_publisher import ToFPublisher
from motor_controller import MotorController
from radiozoa_behaviour import Radiozoa
from roam_behaviour import Roam

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
        self._log.info(Fore.WHITE + 'radiozoa enabled? {}; roam enabled? {}'.format(self._radiozoa_enabled, self._roam_enabled) + Style.RESET_ALL)
        self.pixel = pixel
        self._ring = ring
        self._message_bus = MessageBus(level=level)
        # create I2C bus ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._log.info('configuring I2C bus…')
        _i2c_cfg = self._config['rros']['i2c']
        _i2c_id  = _i2c_cfg['id']
        _scl     = _i2c_cfg['scl']
        _sda     = _i2c_cfg['sda']
        _i2c_baud_rate = _i2c_cfg['baud_rate'] # 400_000
        self._i2c = I2C(_i2c_id, scl=_scl, sda=_sda, freq=_i2c_baud_rate)
        # create components ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._sensor     = None
        self._visualiser = None
        self._publisher  = None
        self._radiozoa   = None
        self._roam       = None
        self.devices     = []
        # create device configurations ┈┈┈┈┈┈┈
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
        self._radiozoa_config = RadiozoaConfig(config=self._config, i2c=self._i2c, ring=self._ring, level=self._level)
        self._radiozoa_config.configure(self.continue_init)

    def continue_init(self):
        if not self._radiozoa_config.configured:
            raise RuntimeError('sensor configuration failed.')
        self._log.info('creating radiozoa sensor…')
        self._sensor = RadiozoaSensor(i2c=self._i2c, level=self._level)
        self._log.info('creating publisher…')
        self._publisher = ToFPublisher(self._sensor, self._message_bus, level=self._level)
        self._log.info('creating motor controller…')
        self._motor_ctrl = MotorController(config=self._config, ring=self._ring, level=self._level)
        if self._radiozoa_enabled:
            self._log.info('creating radiozoa behaviour…')
            self._radiozoa = Radiozoa(self._message_bus, self._motor_ctrl, level=self._level)
        self._log.info('creating roam behaviour…')
        self._roam = Roam(self._config, self._message_bus, self._motor_ctrl, self._ring, level=self._level)

        if self._ring is not None:
            from ring_visualiser import RingVisualiser
            self._log.info('creating ring visualiser…')
            self._visualiser = RingVisualiser(self._ring, self._message_bus, level=self._level)
            self._visualiser.set_brightness(0.0)
            self._visualiser.set_brighten(True)
        else:
            self._visualiser = None
        self._log.info(Fore.GREEN + 'ready.' + Style.RESET_ALL)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    async def run(self):
        self._message_bus.enable()
        self._publisher.enable()
        if self._radiozoa_enabled:
            self._radiozoa.enable()
        if self._roam_enabled:
            self._roam.enable()
        self._motor_ctrl.enable()
        if self._visualiser is not None:
            self._log.info('enabling ring visualiser…')
            self._visualiser.enable()
        self._sensor.start_ranging()
        asyncio.create_task(self._message_bus.consume_loop())
        asyncio.create_task(self._publisher.poll_loop())
        asyncio.create_task(self._motor_ctrl._run())
        self._log.info(Fore.GREEN + 'running…' + Style.RESET_ALL)
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

#EOF
