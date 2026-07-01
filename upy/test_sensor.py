#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-04
# modified: 2026-07-01

import sys
import time
from machine import Pin, I2C

from colorama import Fore, Style
from config_loader import ConfigLoader
from logger import Logger, Level
from i2c_scanner import I2CScanner
from pixel import Pixel
from radiozoa_config import RadiozoaConfig
from ring_visualiser import RingVisualiser

# force module reload
for mod in ['test_sensor']:
    if mod in sys.modules:
        del sys.modules[mod]

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def config_callback():
    print("🍄 callback")

radiozoa_config = None

try:

    print('configuring I2C bus…')
    i2c = I2C(1, scl=38, sda=18, freq=400_000)

    print('creating I2CScanner…')
    scanner = I2CScanner(i2c=i2c)

    config = ConfigLoader.configure('config.yaml')
#   ring = Pixel(pin=44, pixel_count=24, color_order='GRB', brightness=0.1)

    visualiser = None
    radiozoa_config = RadiozoaConfig(config=config, i2c=i2c, i2c_scanner=scanner, visualiser=visualiser, level=Level.INFO)
    radiozoa_config.reset()
    time.sleep(1)
    radiozoa_config.configure(callback=config_callback)

    print("🍄 scan...")
    scanner.i2cdetect()

except Exception as e:
    print(Fore.RED + '{} raised: {}'.format(type(e), e) + Style.RESET_ALL)
    sys.print_exception(e)
finally:
    if radiozoa_config:
        radiozoa_config.close()

#EOF
