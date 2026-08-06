#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2026-08-06
# modified: 2026-08-06
#
# Ported from the original driver by Jose D. Montoya:
#
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT

import time
import struct
from collections import namedtuple
from micropython import const

try:
    from typing import Tuple
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/jposada202020/MicroPython_LIS2MDL.git"

INT_THS_L_REG = 0x65
_REG_WHO_AM_I = const(0x4F)
_CFG_REG_A = const(0x60)
_CFG_REG_B = const(0x61)
_CFG_REG_C = const(0x62)
_INT_CRTL_REG = const(0x63)
_INT_SOURCE_REG = const(0x64)
_INT_THS = const(0x65)
_DATA = const(0x68)

# auto-increment bit required for multi-byte burst reads on ST devices
_AUTO_INCREMENT = const(0x80)

_GAUSS_TO_UT = 0.15

CONTINUOUS = const(0b00)
ONE_SHOT = const(0b01)
POWER_DOWN = const(0b10)
operation_mode_values = (CONTINUOUS, ONE_SHOT, POWER_DOWN)

RATE_10_HZ = const(0b00)
RATE_20_HZ = const(0b01)
RATE_50_HZ = const(0b10)
RATE_100_HZ = const(0b11)
data_rate_values = (RATE_10_HZ, RATE_20_HZ, RATE_50_HZ, RATE_100_HZ)

LP_DISABLED = const(0b0)
LP_ENABLED = const(0b1)
low_power_mode_values = (LP_DISABLED, LP_ENABLED)

LPF_DISABLED = const(0b0)
LPF_ENABLED = const(0b1)
low_pass_filter_mode_values = (LPF_DISABLED, LPF_ENABLED)

INT_DISABLED = const(0b0)
INT_ENABLED = const(0b1)
interrupt_mode_values = (INT_DISABLED, INT_ENABLED)


AlertStatus = namedtuple(
    "AlertStatus", ["x_high", "x_low", "y_high", "y_low", "z_high", "z_low"]
)


class CBits:
    '''
    changes bits from a byte register
    '''

    def __init__(
        self,
        num_bits: int,
        register_address: int,
        start_bit: int,
        register_width=1,
        lsb_first=True,
    ) -> None:
        self.bit_mask = ((1 << num_bits) - 1) << start_bit
        self.register = register_address
        self.start_bit = start_bit
        self.length = register_width
        self.lsb_first = lsb_first

    def __get__(
        self,
        obj,
        objtype=None,
    ) -> int:
        mem_value = obj._i2c.readfrom_mem(obj._address, self.register, self.length)

        reg = 0
        order = range(len(mem_value) - 1, -1, -1)
        if not self.lsb_first:
            order = reversed(order)
        for i in order:
            reg = (reg << 8) | mem_value[i]

        reg = (reg & self.bit_mask) >> self.start_bit

        return reg

    def __set__(self, obj, value: int) -> None:
        memory_value = obj._i2c.readfrom_mem(obj._address, self.register, self.length)

        reg = 0
        order = range(len(memory_value) - 1, -1, -1)
        if not self.lsb_first:
            order = range(0, len(memory_value))
        for i in order:
            reg = (reg << 8) | memory_value[i]
        reg &= ~self.bit_mask

        value <<= self.start_bit
        reg |= value
        reg = reg.to_bytes(self.length, "big")

        obj._i2c.writeto_mem(obj._address, self.register, reg)


class RegisterStruct:
    '''
    register struct
    '''

    def __init__(self, register_address: int, form: str) -> None:
        self.format = form
        self.register = register_address
        self.length = struct.calcsize(form)

    def __get__(
        self,
        obj,
        objtype=None,
    ):
        if self.length <= 2:
            value = struct.unpack(
                self.format,
                memoryview(
                    obj._i2c.readfrom_mem(obj._address, self.register, self.length)
                ),
            )[0]
        else:
            value = struct.unpack(
                self.format,
                memoryview(
                    obj._i2c.readfrom_mem(obj._address, self.register, self.length)
                ),
            )
        return value

    def __set__(self, obj, value):
        mem_value = struct.pack(self.format, value)
        obj._i2c.writeto_mem(obj._address, self.register, mem_value)


class LIS2MDL:
    '''Driver for the LIS2MDL Sensor connected over I2C.

    :param ~machine.I2C i2c: The I2C bus the LIS2MDL is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x1E`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`LIS2MDL` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        from machine import Pin, I2C
        from micropython_lis2mdl import lis2mdl

    Once this is done you can define your `machine.I2C` object and define your sensor object

    .. code-block:: python

        i2c = I2C(1, sda=Pin(2), scl=Pin(3))
        lis = lis2mdl.LIS2MDL(i2c)

    Now you have access to the attributes

    .. code-block:: python

        magx, magy, magz = lis.magnetic

    '''

    _device_id = RegisterStruct(_REG_WHO_AM_I, "B")

    _reset = CBits(1, _CFG_REG_A, 5)
    _low_power_mode = CBits(1, _CFG_REG_A, 4)
    _data_rate = CBits(2, _CFG_REG_A, 2)
    _operation_mode = CBits(2, _CFG_REG_A, 0)

    _low_pass_filter_mode = CBits(1, _CFG_REG_B, 0)

    _xyz_interrupt_enable = CBits(3, _INT_CRTL_REG, 5)
    _int_reg_polarity = CBits(1, _INT_CRTL_REG, 2)
    _int_latched = CBits(1, _INT_CRTL_REG, 1)
    _interrupt_mode = CBits(1, _INT_CRTL_REG, 0)
    _interrupt_pin_inversed = CBits(1, _CFG_REG_C, 6)

    _x_high = CBits(1, _INT_SOURCE_REG, 7)
    _y_high = CBits(1, _INT_SOURCE_REG, 6)
    _z_high = CBits(1, _INT_SOURCE_REG, 5)
    _x_low = CBits(1, _INT_SOURCE_REG, 4)
    _y_low = CBits(1, _INT_SOURCE_REG, 3)
    _z_low = CBits(1, _INT_SOURCE_REG, 2)
    _interrupt_triggered = CBits(1, _INT_SOURCE_REG, 0)

    # multi-byte burst read requires the auto-increment bit set in the sub-address
    _raw_magnetic_data = RegisterStruct(_DATA | _AUTO_INCREMENT, "<hhh")
    _interrupt_threshold = RegisterStruct(INT_THS_L_REG, "<h")

    def __init__(self, i2c, address: int = 0x1E) -> None:
        self._i2c = i2c
        self._address = address

        if self._device_id != 0x40:
            raise RuntimeError("Failed to find the LIS2MDL sensor")

        self._operation_mode = CONTINUOUS
        self._int_latched = True
        self._int_reg_polarity = True
        self._interrupt_pin_inversed = True

    @property
    def operation_mode(self) -> str:
        '''
        sensor operation_mode

        +--------------------------------+------------------+
        | Mode                           | Value            |
        +================================+==================+
        | :py:const:`lis2mdl.CONTINUOUS` | :py:const:`0b00` |
        +--------------------------------+------------------+
        | :py:const:`lis2mdl.ONE_SHOT`   | :py:const:`0b01` |
        +--------------------------------+------------------+
        | :py:const:`lis2mdl.POWER_DOWN` | :py:const:`0b10` |
        +--------------------------------+------------------+
        '''
        values = ("CONTINUOUS", "ONE_SHOT", "POWER_DOWN")
        return values[self._operation_mode]

    @operation_mode.setter
    def operation_mode(self, value: int) -> None:
        if value not in operation_mode_values:
            raise ValueError("Value must be a valid operation_mode setting")
        self._operation_mode = value

    @property
    def data_rate(self) -> str:
        '''
        sensor data_rate

        +---------------------------------+------------------+
        | Mode                            | Value            |
        +=================================+==================+
        | :py:const:`lis2mdl.RATE_10_HZ`  | :py:const:`0b00` |
        +---------------------------------+------------------+
        | :py:const:`lis2mdl.RATE_20_HZ`  | :py:const:`0b01` |
        +---------------------------------+------------------+
        | :py:const:`lis2mdl.RATE_50_HZ`  | :py:const:`0b10` |
        +---------------------------------+------------------+
        | :py:const:`lis2mdl.RATE_100_HZ` | :py:const:`0b11` |
        +---------------------------------+------------------+
        '''
        values = ("RATE_10_HZ", "RATE_20_HZ", "RATE_50_HZ", "RATE_100_HZ")
        return values[self._data_rate]

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        if value not in data_rate_values:
            raise ValueError("Value must be a valid data_rate setting")
        self._data_rate = value

    def reset(self) -> None:
        '''
        reset the sensor
        '''
        self._reset = True
        time.sleep(0.010)

    @property
    def low_power_mode(self) -> str:
        '''
        sensor low_power_mode. Default value: DISABLED

        +---------------------------------+-----------------+
        | Mode                            | Value           |
        +=================================+=================+
        | :py:const:`lis3mdl.LP_DISABLED` | :py:const:`0b0` |
        +---------------------------------+-----------------+
        | :py:const:`lis3mdl.LP_ENABLED`  | :py:const:`0b1` |
        +---------------------------------+-----------------+
        '''
        values = ("LP_DISABLED", "LP_ENABLED")
        return values[self._low_power_mode]

    @low_power_mode.setter
    def low_power_mode(self, value: int) -> None:
        if value not in low_power_mode_values:
            raise ValueError("Value must be a valid low_power_mode setting")
        self._low_power_mode = value

    @property
    def magnetic(self) -> Tuple[float, float, float]:
        '''
        magnetometer values in microteslas
        '''
        rawx, rawy, rawz = self._raw_magnetic_data
        x = rawx * _GAUSS_TO_UT
        y = rawy * _GAUSS_TO_UT
        z = rawz * _GAUSS_TO_UT

        return x, y, z

    @property
    def low_pass_filter_mode(self) -> str:
        '''
        sensor low_pass_filter_mode. Default DISABLED:
        Values:

        * DISABLED : ODR/2
        * ENABLED : ODR/4

        +----------------------------------+-----------------+
        | Mode                             | Value           |
        +==================================+=================+
        | :py:const:`lis2mdl.LPF_DISABLED` | :py:const:`0b0` |
        +----------------------------------+-----------------+
        | :py:const:`lis2mdl.LPF_ENABLED`  | :py:const:`0b1` |
        +----------------------------------+-----------------+
        '''
        values = ("LPF_DISABLED", "LPF_ENABLED")
        return values[self._low_pass_filter_mode]

    @low_pass_filter_mode.setter
    def low_pass_filter_mode(self, value: int) -> None:
        if value not in low_pass_filter_mode_values:
            raise ValueError("Value must be a valid low_pass_filter_mode setting")
        self._low_pass_filter_mode = value

    @property
    def interrupt_mode(self) -> str:
        '''
        sensor interrupt_mode

        +----------------------------------+-----------------+
        | Mode                             | Value           |
        +==================================+=================+
        | :py:const:`lis2mdl.INT_DISABLED` | :py:const:`0b0` |
        +----------------------------------+-----------------+
        | :py:const:`lis2mdl.INT_ENABLED`  | :py:const:`0b1` |
        +----------------------------------+-----------------+
        '''
        values = ("INT_DISABLED", "INT_ENABLED")
        return values[self._interrupt_mode]

    @interrupt_mode.setter
    def interrupt_mode(self, value: int) -> None:
        if value not in interrupt_mode_values:
            raise ValueError("Value must be a valid interrupt_mode setting")
        self._interrupt_mode = value
        if value:
            self._xyz_interrupt_enable = 0b111
        else:
            self._xyz_interrupt_enable = 0

    @property
    def interrupt_threshold(self) -> float:
        '''the threshold (in microteslas) for magnetometer interrupt generation. Given value is
        compared against all axes in both the positive and negative direction'''
        return self._interrupt_threshold * _GAUSS_TO_UT

    @interrupt_threshold.setter
    def interrupt_threshold(self, value: float) -> None:
        if value < 0:
            value = -value
        self._interrupt_threshold = round(value / _GAUSS_TO_UT)

    @property
    def interrupt_triggered(self):
        '''
        return True when an interrupt is triggered
        '''
        return self._interrupt_triggered

    @property
    def alert_status(self):
        '''
        alert status for interrupts
        '''

        return AlertStatus(
            x_high=self._x_high,
            x_low=self._x_low,
            y_high=self._y_high,
            y_low=self._y_low,
            z_high=self._z_high,
            z_low=self._z_low,
        )

#EOF
