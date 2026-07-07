#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:    Ichiro Furusato
# created:   2026-01-29
# modified:  2026-07-03

import sys
import asyncio
import time
from machine import I2C

from colorama import Fore, Style
from logger import Logger, Level
from device import Device

OUT_OF_RANGE = 9999

class RadiozoaSensor:
    '''
    Manages an array of eight VL53L1X proximity sensors as implemented on the
    Radiozoa sensor board. Assumes all sensors are already configured at addresses
    0x30-0x37 by RadiozoaConfig.

    :param i2c:     the I2C bus
    :param level:   the logging level
    : public API preserved exactly while delegating driver state to Device.
    '''
    CLOSE_THRESHOLD = 100
    NEAR_THRESHOLD  = 200
    MID_THRESHOLD   = 600
    FAR_THRESHOLD   = 1000

    def __init__(self, i2c=None, level=Level.INFO):
        self._log = Logger('sensor', level=level)
        self._i2c = i2c
        self._is_ranging = False
        self._distance_offset = 50
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def is_ranging(self):
        return self._is_ranging

    def get_sensor(self, label):
        '''
        Return the VL53 sensor corresponding to the device label.
        '''
        device = Device.by_label(label)
        if device:
            return device.driver
        return None

    def init_device_drivers(self):
        for device in Device.all():
            device.init_driver(self._i2c)
        self._log.info('devices initialised.')

    def start_ranging(self):
        '''
        Starts ranging on all sensors.
        '''
        if not self._is_ranging:
            self._log.info('start ranging…')
            for device in Device.all():
                if device.driver:
                    try:
                        device.driver.start()
                        self._log.info('sensor {} ranging started.'.format(device.label))
                    except Exception as e:
                        self._log.error('{} raised starting sensor {}: {}'.format(type(e), device.label, e))
                else:
                    self._log.warn('no driver available for device: {}'.format(device))
            self._is_ranging = True
            time.sleep_ms(100)
            self._log.info('ranging started.')
        else:
            self._log.warn('already ranging.')

    def stop_ranging(self):
        '''
        Starts ranging on all sensors.
        '''
        if self._is_ranging:
            self._log.info('stop ranging…')
            for device in Device.all():
                if device.driver:
                    try:
                        device.driver.stop()
                        self._log.info('sensor {} ranging stopped.'.format(device.label))
                    except Exception as e:
                        self._log.error('{} raised stopping sensor {}: {}'.format(
                                type(e), device.label, e))
            self._is_ranging = False
            self._log.info('ranging stopped.')
        else:
            self._log.warn('not currently ranging.')

    async def get_distance_async(self, device):
        '''
        Asynchronously returns the distance reading in mm from the sensor at
        the given device, or OUT_OF_RANGE on error.
        '''
        if device and device.driver:
            try:
                _raw = await device.driver.read_async()
                return max(0, _raw - self._distance_offset)
            except Exception as e:
                self._log.error('{} raised reading sensor {}: {}'.format(
                        type(e), device.label, e))
                return OUT_OF_RANGE
        else:
            self._log.warn('no sensor for device {}.'.format(device.label if device else 'Unknown'))
            return OUT_OF_RANGE

    async def get_distances_async(self):
        '''
        Asynchronously returns a tuple of distance readings in mm for all eight
        sensors in device registry order, substituting OUT_OF_RANGE on any error.
        '''
        distances = []
        for device in Device.all():
            if device.driver:
                try:
                    _raw = await device.driver.read_async()
                    distances.append(max(0, _raw - self._distance_offset))
                except Exception as e:
                    self._log.error('{} reading sensor {}: {}'.format(
                            type(e), device.label, e))
                    distances.append(OUT_OF_RANGE)
            else:
                distances.append(OUT_OF_RANGE)
        return tuple(distances)

    def get_distance(self, device):
        '''
        Synchronously returns the distance reading in mm from the sensor at the
        given device, or OUT_OF_RANGE on error.
        '''
        if device and device.driver:
            try:
                return max(0, device.driver.read() - self._distance_offset)
            except Exception as e:
                self._log.error('{} raised reading sensor {}: {}'.format(
                        type(e), device.label, e))
                return OUT_OF_RANGE
        else:
            self._log.warn('no sensor for device {}.'.format(device.label if device else 'Unknown'))
            return OUT_OF_RANGE

    def get_distances(self):
        '''
        Synchronously returns a tuple of distance readings in mm for all eight
        sensors in device registry order, substituting OUT_OF_RANGE on any error.
        '''
        distances = []
        for device in Device.all():
            if device.driver:
                try:
                    distances.append(max(0, device.driver.read() - self._distance_offset))
                except Exception as e:
                    self._log.error('{} reading sensor {}: {}'.format(
                            type(e), device.label, e))
                    distances.append(OUT_OF_RANGE)
            else:
                distances.append(OUT_OF_RANGE)
        return tuple(distances)

    def close(self):
        self._log.info('closing…')
        if self._is_ranging:
            self.stop_ranging()
        self._log.info('closed.')

#EOF
