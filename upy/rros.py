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
from logger import Logger, Level
from message_bus import MessageBus
from radiozoa_config import RadiozoaConfig
from radiozoa_sensor import RadiozoaSensor
from tof_publisher import ToFPublisher
from mock_subscriber import MockSubscriber

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
        # configure sensor addresses synchronously before async loop starts
        self._log.info('configuring sensors…')
        _config = RadiozoaConfig(i2c=self._i2c, ring=ring, level=level)
        _config.configure()
        if not _config.configured:
            raise RuntimeError('sensor configuration failed.')
        # create and start ranging
        self._sensor = RadiozoaSensor(i2c=self._i2c, level=level)
        self._sensor.start_ranging()
        # publisher and subscriber
        self._publisher  = ToFPublisher(self._sensor, self._message_bus, level=level)
        self._subscriber = MockSubscriber(self._message_bus, level=level)
        if self._ring is not None:
            from ring_visualiser import RingVisualiser
            self._visualiser = RingVisualiser(self._ring, self._message_bus, level=level)
        else:
            self._visualiser = None
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    async def run(self):
        self._message_bus.enable()
        self._publisher.enable()
        self._subscriber.enable()
        if self._visualiser is not None:
            self._visualiser.enable()
        asyncio.create_task(self._message_bus.consume_loop())
        asyncio.create_task(self._publisher.poll_loop())
        self._log.info('running…')
        while True:
            await asyncio.sleep_ms(100)

    def start(self):
        asyncio.run(self.run())

    def close(self):
        if self._visualiser is not None:
            self._visualiser.close()
        self._publisher.close()
        self._subscriber.close()
        self._message_bus.close()

#EOF
