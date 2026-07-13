#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-06-21

import sys, os, gc
import time
from colorama import Fore, Style

from colors import *
from logger import Logger, Level
from orientation import Orientation
from pixel import Pixel
from rros import RROS

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

RELAY_SETUP = True
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

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

_rros = None
_pixel = Pixel(pin=48, pixel_count=1, color_order='GRB', brightness=0.3)

try:

    pre_blink()
    print_sysinfo()

    _rros = RROS(pixel=_pixel)

    if RELAY_SETUP:

        from config_loader import ConfigLoader
        from relay_setup import RelaySetup

        _config = ConfigLoader.configure('relay.yaml')
        relay_setup = RelaySetup(_config, _rros.message_bus, _rros.message_factory, _rros.pixel, level=Level.INFO);

        log.info('relay ready.')

    # blocks until completion
    _rros.enable()

except KeyboardInterrupt:
    log.info('interrupted.')
except Exception as e:
    log.error('{} raised: {}'.format(type(e), e))
    sys.print_exception(e)
finally:
    if _rros:
        _rros.close()
    log.info("complete.")

#EOF
