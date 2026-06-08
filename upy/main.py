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

import sys, os, gc, sys
import time

from colors import *
from logger import Logger, Level
from rros import RROS

IS_TINYS3 = True # otherwise TinyPICO

START_COUNT = 3

log = Logger('main', Level.INFO)

# force module reload
for mod in ['main']:
    if mod in sys.modules:
        del sys.modules[mod]

def pre_blink():
    for i in range(START_COUNT):
        log.info('[{}/{}] starting…'.format(i + 1, START_COUNT))
        _pixel.show_color(COLOR_DARK_CYAN)
        time.sleep_ms(50)
        _pixel.show_color(COLOR_BLACK)
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

_pixel = None
if IS_TINYS3:
    from s3_pixel import S3Pixel
    _pixel = S3Pixel()
else: # otherwise TinyPICO
    from pico_pixel import PicoPixel
    _pixel = PicoPixel()

_rros = None
try:
    pre_blink()
    print_sysinfo()

    from pixel import Pixel
    _ring = Pixel(pin=44, pixel_count=24, color_order='GRB', brightness=0.1)
    _rros = RROS(_pixel, ring=_ring, level=Level.INFO)
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
    _pixel.close()

#EOF
