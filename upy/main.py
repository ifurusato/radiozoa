#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-06-15
# modified: 2026-06-04
#

import time 
import os, gc
import micropython # used to get memory information
from machine import SoftSPI, Pin
import tinypico as TinyPICO
from dotstar import DotStar

from colors import *
from logger import Logger, Level

# constants ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

START_COUNT = 3

log = Logger('main', Level.INFO)

# functions ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def show_color(color):
    '''
    Display the color on the DotStar.
    '''
#   print("show color: {}".format(color.description))
#   _dotstar[0] = (color[2], color[1], color[0]) # in BGR order
#   _dotstar[0] = (color[0], color[1], color[2]) # in RGB order
    _dotstar[0] = color

def rainbow():
    '''
    Displays rainbow colours on the Dotstar.
    '''
    # create a colour wheel index int
    color_index = 0
#   while True: # forever
    for _ in range(0, 100): # 100 times (0-99)
        # get the R,G,B values of the next colour
        r,g,b = TinyPICO.dotstar_color_wheel(color_index)
        # Set the colour on the dotstar
        _dotstar[0] = (r, g, b, 0.3)
        # increase the wheel index
        color_index += 1
        # sleep for 20ms so the colour cycle isn't too fast
        time.sleep_ms(20)

def pre_blink():
    for i in range(START_COUNT):
        log.info('[{}/{}] starting…'.format(i, START_COUNT))
        show_color(COLOR_CYAN)
        time.sleep_ms(50)
        show_color(COLOR_BLACK)
        time.sleep_ms(950)
    time.sleep_ms(50)

def print_sysinfo():
    gc.collect()
    s = os.statvfs("/")
    log.info("RAM free: {:.1f}KB; used: {:.1f}KB; FS total: {:.1f}KB; used: {:.1f}KB; free: {:.1f}KB".format(
        gc.mem_free()/1024,
        gc.mem_alloc()/1024,
        (s[2]*s[1])/1024,
        ((s[2]*s[1])-(s[4]*s[1]))/1024,
        (s[4]*s[1])/1024
    ))

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# configure SPI for controlling the DotStar
spi = SoftSPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO))
_brightness = 0.3 # 30% brightness
_dotstar = DotStar(spi, 1, brightness=_brightness)
# turn on the power to the DotStar
TinyPICO.set_dotstar_power(True)

try:

    # indicate startup, waiting 3 seconds so it can be interrupted…
    pre_blink()

    # show some info on boot
    log.info("battery voltage is {}V".format(TinyPICO.get_battery_voltage()))
    log.info("battery charge state is {}\n".format( TinyPICO.get_battery_charging()))

    print_sysinfo()
#   # show available memory
#   log.info("memory info - micropython.mem_info()")
#   log.info("------------------------------------")
#   micropython.mem_info()

    # do something intelligent here

except KeyboardInterrupt:
    _dotstar.deinit()
except Exception as e:
    log.error('error: {}'.format(e))

#EOF
