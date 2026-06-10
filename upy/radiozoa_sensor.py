#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-01-29
# modified: 2026-06-04

import sys
import time
from machine import I2C

from colorama import Fore, Style
from logger import Logger, Level
from device import Device
from vl53l1x import VL53L1X

OUT_OF_RANGE = 9999

class RadiozoaSensor:
    '''
    Manages an array of eight VL53L1X proximity sensors as implemented on the
    Radiozoa sensor board. Assumes all sensors are already configured at addresses
    0x30-0x37 by RadiozoaConfig.

    :param i2c:     the I2C bus
    :param level:   the logging level
    '''
    CLOSE_THRESHOLD = 100
    NEAR_THRESHOLD  = 200
    MID_THRESHOLD   = 600
    FAR_THRESHOLD   = 1000

    def __init__(self, i2c=None, level=Level.INFO):
        self._log = Logger('sensor', level=level)
        self._i2c = i2c
        self._sensors = {}
        self._is_ranging = False
        self._distance_offset = 50
        self._create_sensors()
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
        return device != None ? self._sensors.get(device) : None

    def _create_sensors(self):
        '''
        Creates VL53L1X instances for all eight sensors using the Device pseudo-enum.
        '''
        for dev in Device.all():
            device = Device._registry[dev.index]
            self._log.info('creating sensor {} at 0x{:02X}…'.format(device.label, dev.i2c_address))
            try:
                if dev.impl == 'VL53L1X':
#                   _debug = dev.index == 6 # set debug
                    sensor = VL53L1X(self._i2c, address=dev.i2c_address) #, debug=_debug)
                else:
                    sensor = None
                self._sensors[device] = sensor
                self._log.info('sensor {} created.'.format(device.label))
            except Exception as e:
                self._log.error('{} raised creating sensor {}: {}'.format(
                        type(e), device.label, e))
                sys.print_exception(e)
                raise

    def start_ranging(self):
        '''
        Starts ranging on all sensors.
        '''
        if not self._is_ranging:
            self._log.info('start ranging…')
            for device, sensor in self._sensors.items():
                if sensor:
                    try:
                        sensor.start()
                        self._log.info('sensor {} ranging started.'.format(device.label))
                    except Exception as e:
                        self._log.error('{} raised starting sensor {}: {}'.format(
                                type(e), device.label, e))
            self._is_ranging = True
            time.sleep_ms(100)
            self._log.info('ranging started.')
        else:
            self._log.warning('already ranging.')

    def stop_ranging(self):
        '''
        Stops ranging on all sensors.
        '''
        if self._is_ranging:
            self._log.info('stop ranging…')
            for device, sensor in self._sensors.items():
                if sensor:
                    try:
                        sensor.stop()
                        self._log.info('sensor {} ranging stopped.'.format(device.label))
                    except Exception as e:
                        self._log.error('{} raised stopping sensor {}: {}'.format(
                                type(e), device.label, e))
            self._is_ranging = False
            self._log.info('ranging stopped.')
        else:
            self._log.warning('not currently ranging.')

    def get_distance(self, device):
        '''
        Returns the distance reading in mm from the sensor at the given device,
        or OUT_OF_RANGE on error.
        '''
        sensor = self._sensors.get(device)
        if sensor:
            try:
                return max(0, sensor.read() - self._distance_offset)
            except Exception as e:
                self._log.error('{} raised reading sensor {}: {}'.format(
                        type(e), device.label, e))
                return OUT_OF_RANGE
        else:
            self._log.warning('no sensor for device {}.'.format(device.label))
            return OUT_OF_RANGE

    def get_distances(self):
        '''
        Returns a tuple of distance readings in mm for all eight sensors
        in device registry order, substituting OUT_OF_RANGE on any error.
        '''
        distances = []
        for device in Device._registry:
            sensor = self._sensors.get(device)
            if sensor:
                try:
                    distances.append(max(0, sensor.read() - self._distance_offset))
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
