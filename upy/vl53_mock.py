#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-08-20
# modified: 2026-08-20

from logger import Logger, Level

class VL53Mock:

    def __init__(self, device):
        self._i2c_address = device.i2c_address
        self._log = Logger('vl53-mock-{}'.format(device.label), Level.INFO)
        self._distance_mm = -1
        self._log.info('ready.')

    def init(self):
        pass

    def start(self):
        self._log.info('start.')

    def stop(self):
        self._log.info('stop.')

    async def read_async(self):
        return self._distance_mm

    def read(self):
        return self._distance_mm

    def get_distance(self):
        return self._distance_mm

    def set_i2c_address(self, new_address):
        self._i2c_address = new_address
        self._log.info('new address set to: 0x{:2X}.'.format(new_address))

    def start_ranging(self):
        self._log.info('start ranging.')
        pass

    def stop_ranging(self):
        self._log.info('stop ranging.')
        pass

    def check_for_data_ready(self):
        return 1

#EOF
