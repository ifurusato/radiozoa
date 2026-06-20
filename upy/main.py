#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-06-20

import sys, os, gc, sys
import asyncio
import time
from machine import Pin
from colorama import Fore, Style

from colors import *
from logger import Logger, Level
from pixel import Pixel
from rros import RROS

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

USE_ENCODERS = False

if USE_ENCODERS:
    # Pin configuration
    p2  = Pin(2, Pin.IN, Pin.PULL_UP)
    p1  = Pin(1, Pin.IN, Pin.PULL_UP)
    p16 = Pin(16, Pin.IN, Pin.PULL_UP)
    p17 = Pin(17, Pin.IN, Pin.PULL_UP)

    def callback_2(p):
        print(Fore.GREEN + "IRQ triggered on Pin 2" + Style.RESET_ALL)

    def callback_1(p):
        print(Fore.GREEN + "IRQ triggered on Pin 1" + Style.RESET_ALL)

    def callback_16(p):
        print(Fore.RED + "IRQ triggered on Pin 16" + Style.RESET_ALL)

    def callback_17(p):
        print(Fore.RED + "IRQ triggered on Pin 17" + Style.RESET_ALL)

    # Attach interrupts for both falling and rising edges
    p2.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=callback_2)
    p1.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=callback_1)
    p16.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=callback_16)
    p17.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=callback_17)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

START_COUNT = 3

log = Logger('main', Level.INFO)

# force module reload
for mod in ['main']:
    if mod in sys.modules:
        del sys.modules[mod]

def pre_blink():
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

async def drive_callback():
    log.info('drive callback…')

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

_priority   = 0.5
_drive      = None
_rros       = None
_ring  = Pixel(pin=21, pixel_count=24, color_order='GRB', brightness=0.1)
_pixel = Pixel(pin=48, pixel_count=1, color_order='GRB', brightness=0.1)
# _pixel.rainbow_cycle(delay=0.01, steps=512)

try:

    pre_blink()
    print_sysinfo()

    _rros  = RROS(_pixel, ring=_ring, level=Level.INFO)
#   _drive = _rros.drive
#   _drive.set_ready_callback(drive_callback)
    # blocks until completion
    _rros.start()

except KeyboardInterrupt:
    log.info('interrupted.')
except Exception as e:
    log.error('{} raised: {}'.format(type(e), e))
    sys.print_exception(e)
finally:
    if _rros:
        _rros.close()
    _ring.close()
    _pixel.close()
    if USE_ENCODERS:
        p2.irq(handler=None)
        p1.irq(handler=None)
        p16.irq(handler=None)
        p17.irq(handler=None)
    print("complete.")

#EOF
