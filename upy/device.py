#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created:  2026-01-27
# modified: 2026-07-19

class Device:
    _registry = []
    '''
    A container for VL53L0X or VL53L1X sensor configurations that holds its own registry.

    The value for impl() will either be 'VL53L0X', 'VL53L1X' or None (if no sensor is available in that slot).

    Usage:

      Iterate like an enum:

          for dev in Device.all():
              print(dev.label, hex(dev.i2c_address), dev.xshut)

      Lookup by label:

          d = Device.by_label("sw5")
          print(d.i2c_address)

      Lookup by index:

          d = Device.by_index(3)
    '''
    def __init__(self, index, impl, label, address, xshut, pixel_8, pixel_24):
        self._index    = index
        self._impl     = impl
        self._label    = label
        self._address  = address
        self._xshut    = xshut
        self._pixel_8  = pixel_8
        self._pixel_24 = pixel_24
        self._driver = None

        # instantiate the pin even if impl is None to maintain structural symmetry
        from machine import Pin
        self._pin = Pin(xshut, Pin.OUT)

        Device._registry.append(self)

    @property
    def index(self):
        return self._index

    @property
    def impl(self):
        return self._impl

    @property
    def label(self):
        return self._label

    @property
    def i2c_address(self):
        return self._address

    @property
    def pixel_8(self):
        return self._pixel_8

    @property
    def pixel_24(self):
        return self._pixel_24

    @property
    def xshut(self):
        return self._xshut

    @property
    def driver(self):
        return self._driver

    @driver.setter
    def driver(self, value):
        self._driver = value

    def set_xshut(self, state):
        '''
        Sets the hardware XSHUT pin state using explicit pin.on() and pin.off().
        '''
        if self._pin is not None:
            self._pin.on() if state else self._pin.off()

    def init_driver(self, i2c):
        '''
        Instantiates the matching MicroPython driver for this sensor at its configured address.
        '''
        if self._impl == 'VL53L1X':
            from vl53l1x import VL53L1X
            self._driver = VL53L1X(i2c, address=self._address)
        elif self._impl == 'VL53L0X':
            from vl53l0x import VL53L0X
            self._driver = VL53L0X(i2c, address=self._address)
        else:
            self._driver = None

    def __int__(self):
        return self._index

    def __repr__(self):
        return "Device({}, {}, 0x{:02X}, xshut={}, pixel_8={}, pixel_24={})".format(
            self._index, self._label, self.i2c_address, self._xshut, self._pixel_8, self._pixel_24
        )

    def __eq__(self, other):
        if isinstance(other, Device):
            return self._index == other._index
        return False

    def __hash__(self):
        return hash(self._index)

    # ---- class helpers ----

    @classmethod
    def all(cls):
        return cls._registry

    @classmethod
    def by_index(cls, index):
        for d in cls._registry:
            if d._index == index:
                return d
        return None

    @classmethod
    def by_label(cls, label):
        key = label.upper()
        for d in cls._registry:
            if d._label.upper() == key:
                return d
        return None

    @classmethod
    def by_i2c(cls, address):
        for d in cls._registry:
            if d._address == address:
                return d
        return None

#EOF
