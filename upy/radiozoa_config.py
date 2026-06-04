#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-01-27
# modified: 2026-06-04

import sys
import time
from machine import Pin, I2C
from colorama import Fore, Style

from logger import Logger, Level
from i2c_scanner import I2CScanner
from device import Device
from colors import *

class RadiozoaConfig:
    '''
    Configures all VL53 sensors on the Radiozoa sensor board to their unique
    I2C addresses by toggling XSHUT pins and setting addresses as specified
    in the Device pseudo-enum.

    An optional NeoPixel ring may be provided for visual feedback during
    address assignment. If absent, configuration proceeds without it.

    :param i2c:     the I2C bus
    :param ring:    optional NeoPixel ring for visual feedback
    :param level:   the logging level
    '''
    def __init__(self, i2c=None, ring=None, level=Level.INFO):
        self._log = Logger('config', level=level)
        if i2c is None:
            raise TypeError('i2c bus argument is null.')
        self._i2c = i2c
        self._default_i2c_address = 0x29
        self._configured = False
        self._ring = ring
        self._xshut_pins = {}
        self._setup_pins()
        self._i2c_scanner = I2CScanner(i2c=self._i2c)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def configured(self):
        return self._configured

    def set_ring(self, ring):
        self._ring = ring

    def configure(self):
        # check if all sensors are already at their target addresses
        self._i2c_scanner.scan()
        _expected = [device.i2c_address for device in Device.all() if device.impl is not None]
        if all(self._i2c_scanner.has_hex_address(addr) for addr in _expected):
            self._log.info('all sensors already configured, skipping address assignment.')
            self._configured = True
            return
        self._shutdown_all_sensors()
        self._configure_sensor_addresses()
        self._log.info('all sensor addresses configured.')

    def reset(self):
        from device import N0
        device = N0
        self._log.info('reset: temporarily shutting down sensor {} at XSHUT pin {}…'.format(
                device.label, device.xshut))
        self._set_xshut(device.index, False)
        time.sleep_ms(250)
        self._set_xshut(device.index, True)
        self._log.info('radiozoa reset.')

    def _setup_pins(self):
        '''
        Configure all XSHUT pins as outputs based on the Device pseudo-enum.
        Pins are configured even where no sensor is available for a given slot.
        '''
        for device in Device.all():
            if device.impl is not None:
                pin = Pin(device.xshut, Pin.OUT)
                self._xshut_pins[device.index] = pin
                self._log.info('configured XSHUT pin {} for sensor {} on 0x{:02X}.'.format(
                        device.xshut, device.label, device.i2c_address))

    def _shutdown_all_sensors(self):
        '''
        Shuts down all sensors by setting their XSHUT pins LOW.
        '''
        for device in Device.all():
            if device.impl is not None:
                self._set_xshut(device.index, False)
                time.sleep_ms(50)
        self._log.info('all sensors shut down.')

    def _configure_sensor_addresses(self):
        '''
        Sequentially brings up each sensor and sets its I2C address,
        leaving it enabled.
        '''
        from vl53l1x import VL53L1X
#       from vl53l0x import VL53L0X

        _device_delay_ms = 333
        _scan_delay_ms   = 750
        _count = 0
        for device in Device.all():
            if device and device.impl is not None:
                if self._ring:
                    self._ring.set_color(device.index, COLOR_APPLE)
                self._log.info('configuring sensor {} at XSHUT pin {}…'.format(
                        device.label, device.xshut))
                self._set_xshut(device.index, True)
                found = False
                for i in range(5):
                    time.sleep_ms(_scan_delay_ms)
                    self._i2c_scanner.scan()
                    found = self._i2c_scanner.has_hex_address(0x29)
                    if found:
                        self._log.info(Style.DIM + '[{}] sensor appeared at 0x29.'.format(i))
                        break
                    else:
                        self._log.info(Style.DIM + '[{}] waiting for sensor…'.format(i))
                if not found:
                    self._log.warning('sensor {} did not appear at 0x29.'.format(device.label))
                    if self._ring:
                        self._ring.set_color(device.index, COLOR_RED)
                    continue
                try:
                    self._set_i2c_address(device, device.i2c_address)
                    self._log.info('set address for sensor {} to 0x{:02X}.'.format(
                            device.label, device.i2c_address))
                    if self._ring:
                        self._ring.set_color(device.index, COLOR_DARK_GREEN)
                    _count += 1
                except Exception as e:
                    self._log.error('{} raised setting address for sensor {}: {}'.format(
                            type(e), device.label, e))
                    sys.print_exception(e)
                    if self._ring:
                        self._ring.set_color(device.index, COLOR_RED)
                time.sleep_ms(_device_delay_ms)
        if _count == 8:
            self._configured = True
            if self._ring:
                for index in range(8):
                    self._ring.set_color(index, COLOR_BLACK)
        else:
            self._configured = False
            self._log.warning('configured {} of 8 sensors.'.format(_count))

    def _set_xshut(self, device_index, value):
        '''
        Set the XSHUT pin state for a given device index.
        '''
        pin = self._xshut_pins.get(device_index)
        if pin:
            pin.on() if value else pin.off()
        else:
            raise RuntimeError('pin not available for device {}.'.format(device_index))

    def _set_i2c_address(self, device, new_addr):
        '''
        Change the I2C address for a VL53L0X or VL53L1X sensor currently at 0x29.
        '''
        current_addr = 0x29
#       if device.impl == 'VL53L0X':
#           self._i2c.writeto(current_addr, bytearray([0x00, 0x01, new_addr]))
#           time.sleep_ms(50)
        if device.impl == 'VL53L1X':
            self._i2c.writeto(current_addr, bytearray([0x00, 0x01, new_addr]))
            time.sleep_ms(50)
        elif device.impl is None:
            self._log.info('no device at {}.'.format(device.label))
        else:
            raise ValueError('unknown sensor type: {}'.format(device.impl))

    def close(self):
        self._log.info('closed.')

#EOF
