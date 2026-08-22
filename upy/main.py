#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-08-20

import sys

# force module reload
for mod in ['main', 'rros']:
    if mod in sys.modules:
        del sys.modules[mod]

import os, gc
import time
import asyncio
from colorama import Fore, Style

from component import Component
from colors import COLOR_DARK_CYAN, COLOR_BLACK
from logger import Logger, Level
from component import Component
from dip_switch import DipSwitch
from pixel import Pixel
from touch_sensor import TouchSensor

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

RELAY_SETUP = True # use ESP-NOW relay for remote control
START_COUNT = 3    # how many times to blink before starting

log = Logger('main', Level.INFO)

def pre_blink():
    global _pixel
    for i in range(START_COUNT):
        log.info('[{}/{}] starting…'.format(i + 1, START_COUNT))
        _pixel.set_color(color=COLOR_DARK_CYAN)
        time.sleep_ms(50)
        _pixel.set_color(color=COLOR_BLACK)
        time.sleep_ms(950)

def print_sysinfo():
    gc.collect()
    s = os.statvfs('/')
    log.info('RAM free: {:.1f}KB; used: {:.1f}KB; FS total: {:.1f}KB; used: {:.1f}KB; free: {:.1f}KB'.format(
        gc.mem_free()  / 1024,
        gc.mem_alloc() / 1024,
        (s[2] * s[1]) / 1024,
        ((s[2] * s[1]) - (s[4] * s[1])) / 1024,
        (s[4] * s[1]) / 1024
    ))

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def touch1_callback():
    global log, _enabled
    log.info('touch 1 callback triggered…')
    import touch1

    asyncio.create_task(touch1.test())
#   _enabled = False # exit main after execution?
    pass

def touch2_callback():
    global log, _enabled
    log.info('touch 2 callback triggered…')
    import touch2

    asyncio.create_task(touch2.test())

#   _enabled = False # exit main after execution?
    pass

async def main():
    global log, _pixel

    _config  = None
    _rros    = None
    _pixel   = None
    _enabled = True
    _relay_setup = None

    _dip_switch = DipSwitch()
    _touch_enabled = _dip_switch.get_switch(3) # if switch 3 is ON, use touch triggered scripts instead of RROS

    try:

        if _touch_enabled:
            from machine import I2C
            from eyeballs import Eyeballs

            registry = Component.get_registry()
            eyeballs = registry.get(Eyeballs.NAME)
            if eyeballs is None:
                log.info('creating eyeballs…')
                i2c = I2C(id=1, scl=38, sda=18, freq=400000)
                eyeballs = Eyeballs(i2c)

            eyeballs.blush()

            touch_1 = TouchSensor(pin_num=7, label='1', calibrate=False)
            touch_1.set_callback(touch1_callback)
            touch_1.start()

            touch_2 = TouchSensor(pin_num=5, label='2', calibrate=False)
            touch_2.set_callback(touch2_callback)
            touch_2.start()

            while _enabled:
                await asyncio.sleep(5)

        else:
            from rros import RROS

            # onboard NeoPixel
            _pixel = Pixel(pin=48, pixel_count=1, color_order='GRB', brightness=0.5)

            pre_blink()
            print_sysinfo()

            log.info('instantiating RROS…')
            _rros = RROS(pixel=_pixel)

            if RELAY_SETUP:

                from config_loader import ConfigLoader
                from relay_setup import RelaySetup

                _config = ConfigLoader.configure('relay.yaml')
                _relay_setup = RelaySetup(_config, _rros.message_bus, _rros.message_factory, _rros.pixel, level=Level.INFO);

                log.info('relay ready.')

            # blocks until completion
            _rros_task = _rros.enable()
            if _rros_task:
                await _rros_task

    except KeyboardInterrupt:
        log.info('interrupted.')
        if _rros:
            _rros.close()
    except Exception as e:
        log.error('{} raised: {}'.format(type(e), e))
        sys.print_exception(e)
    finally:
        if _rros:
            # show eyeballs closing
            _rros.indicate_shutdown()
            if not _rros.closed:
                _rros.close()
            Component.close_registry()
            log.info('closed component registry.')
        _config      = None
        _rros        = None
        _relay_setup = None
        if _pixel:
            _pixel.close()
            _pixel   = None
        log.info("complete.")
        log          = None

#if __name__ == "__main__":
asyncio.run(main())

#EOF
