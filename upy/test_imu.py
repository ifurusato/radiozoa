#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-08-06
# modified: 2026-08-06

import sys

# force module reload
for mod in ['icm20948', 'lis2mdl', 'imu', 'test_imu2']:
    if mod in sys.modules:
        del sys.modules[mod]

from machine import Pin, I2C
from utime import sleep_ms

from imu import IMU
from logger import Logger, Level
from config_loader import ConfigLoader

config = ConfigLoader.configure()
i2c = I2C(1, scl=38, sda=18, freq=400000)
imu = IMU(config, i2c)

log = Logger('test', Level.INFO)
log.info('starting…')

try:
    while True:
        heading, pitch, roll = imu.heading_pitch_roll
        log.info('heading: {:7.3f}; pitch: {:7.3f}; roll: {:7.3f}'.format(heading, pitch, roll))
        sleep_ms(250)

except KeyboardInterrupt:
    log.info('Ctrl-C caught, exiting…')
except Exception as e:
    log.error('{} raised: {}'.format(type(e), e))
    sys.print_exception(e)

#EOF
