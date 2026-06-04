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

import time
import os, gc, sys
from machine import SoftSPI, Pin
import tinypico as TinyPICO
from dotstar import DotStar

from colors import *
from logger import Logger, Level
from rros import RROS

START_COUNT = 3

log = Logger('main', Level.INFO)

# force module reload
for mod in ['main']:
    if mod in sys.modules:
        del sys.modules[mod]

# dotstar ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

spi      = SoftSPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO))
_dotstar = DotStar(spi, 1, brightness=0.3)
TinyPICO.set_dotstar_power(True)

def show_color(color):
    _dotstar[0] = color

def pre_blink():
    for i in range(START_COUNT):
        log.info('[{}/{}] starting…'.format(i + 1, START_COUNT))
        show_color(COLOR_DARK_CYAN)
        time.sleep_ms(50)
        show_color(COLOR_BLACK)
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

try:
    pre_blink()
    print_sysinfo()
    _rros = RROS(level=Level.INFO)
    # blocks until completion
    _rros.start()
#   asyncio.run(_rros.run())

except KeyboardInterrupt:
    log.info('interrupted.')
except Exception as e:
    log.error('{} raised: {}'.format(type(e), e))
finally:
    show_color(COLOR_BLACK)
    _dotstar.deinit()

#EOF
