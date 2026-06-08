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
from logger import Logger, Level
from message_bus import MessageBus
from radiozoa_config import RadiozoaConfig
from radiozoa_sensor import RadiozoaSensor
from tof_publisher import ToFPublisher
from tof_subscriber import ToFSubscriber
from motor_controller import MotorController
from radiozoa_behaviour import RadiozoaBehaviour

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
        self._level = level
        self._log  = Logger('rros', level)
        self.pixel = pixel
        self._ring = ring
        self._message_bus = MessageBus(level=level)
        # create I2C bus ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._log.info('configuring I2C bus…')
        _i2c_id    = 1
        _scl       =  9  # 22 on TinyPICO
        _sda       =  8  # 21 on TinyPICO
        _i2c_baud_rate = 400_000
        self._i2c = I2C(_i2c_id, scl=_scl, sda=_sda, freq=_i2c_baud_rate)
        # create components ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._sensor     = None
        self._visualiser = None
        self._publisher  = None
        self._subscriber = None
        self._behaviour  = None
        # configure sensor addresses synchronously before async loop starts
        self._log.info('configuring sensors…')
        self._config = RadiozoaConfig(i2c=self._i2c, ring=self._ring, level=self._level)
        self._config.configure(self.continue_init)

    def continue_init(self):
        if not self._config.configured:
            raise RuntimeError('sensor configuration failed.')
        self._log.info('configuring radiozoa sensor…')
        self._sensor = RadiozoaSensor(i2c=self._i2c, level=self._level)
        self._sensor.start_ranging()
        self._log.info('creating motor controller…')
        self._motor_controller = MotorController(ring=self._ring, level=self._level)
        self._log.info('creating publisher…')
        self._publisher = ToFPublisher(self._sensor, self._message_bus, level=self._level)
        self._log.info('creating behaviour…')
#       self._behaviour = RadiozoaBehaviour(self._message_bus, self._motor_controller, level=self._level)
        self._subscriber = ToFSubscriber(self._message_bus, level=self._level)

        if self._ring is not None:
            from ring_visualiser import RingVisualiser
            self._log.info('creating ring visualiser…')
            self._visualiser = RingVisualiser(self._ring, self._message_bus, level=self._level)
#           self._visualiser.set_brightness(0.0)
#           self._visualiser.set_brighten(True)
        else:
            self._visualiser = None
        self._log.info(Fore.GREEN + 'ready.' + Style.RESET_ALL)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    async def run(self):
        self._message_bus.enable()
        self._publisher.enable()
        self._subscriber.enable()
#       self._behaviour.enable()
        self._motor_controller.enable()
        if self._visualiser is not None:
            self._log.info(Fore.MAGENTA + 'enabling ring visualiser…' + Style.RESET_ALL)
            self._visualiser.enable()
        asyncio.create_task(self._message_bus.consume_loop())
        asyncio.create_task(self._publisher.poll_loop())
        asyncio.create_task(self._motor_controller._run())
        self._log.info(Fore.MAGENTA + 'running…' + Style.RESET_ALL)
        while True:
            await asyncio.sleep_ms(100)

    def start(self):
        asyncio.run(self.run())

    def close(self):
        if self._visualiser:
            self._visualiser.close()
        if self._motor_controller:
            self._motor_controller.close()
        if self._publisher:
            self._publisher.close()
        if self._subscriber:
            self._subscriber.close()
        if self._behaviour:
            self._behaviour.close()
        if self._message_bus:
            self._message_bus.close()

#EOF
