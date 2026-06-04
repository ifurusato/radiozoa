# TinyPICO MicroPython Helper Library
# 2019 Seon Rozenblum, Matt Trentini
#
# Project home:
#   https://github.com/TinyPICO
#
# 2019-Mar-12 - v0.1 - Initial implementation
# 2019-May-20 - v1.0 - Initial Release
# 2019-Oct-23 - v1.1 - Removed temp sensor code, prep for frozen modules
# 2026-Jun-04 - v1.2 - removed documentation to save space (Furusato)

from micropython import const
from machine import Pin, SPI, ADC
import machine, time, esp32

BAT_VOLTAGE = const(35)
BAT_CHARGE = const(34)
DOTSTAR_CLK = const(12)
DOTSTAR_DATA = const(2)
DOTSTAR_PWR = const(13)
SPI_MOSI = const(23)
SPI_CLK = const(18)
SPI_MISO = const(19)
I2C_SDA = const(21)
I2C_SCL = const(22)
DAC1 = const(25)
DAC2 = const(26)

# Helper functions

def get_battery_voltage():
    adc = ADC(Pin(BAT_VOLTAGE))
    measuredvbat = adc.read()
    measuredvbat /= 4095
    measuredvbat *= 3.7
    return measuredvbat

def get_battery_charging():
    measuredVal = 0
    io = Pin(BAT_CHARGE, Pin.IN)
    for y in range(0, 10):
        measuredVal += io.value()
    return measuredVal == 0

def set_dotstar_power(state):
    if state:
        Pin(DOTSTAR_PWR, Pin.OUT, None)
        Pin(DOTSTAR_PWR).value(False)
    else:
        Pin(13, Pin.IN, Pin.PULL_HOLD)
    Pin(DOTSTAR_CLK, Pin.OUT if state else Pin.IN)
    Pin(DOTSTAR_DATA, Pin.OUT if state else Pin.IN)
    time.sleep(0.035)

def dotstar_color_wheel(wheel_pos):
    wheel_pos = wheel_pos % 255
    if wheel_pos < 85:
        return 255 - wheel_pos * 3, 0, wheel_pos * 3
    elif wheel_pos < 170:
        wheel_pos -= 85
        return 0, wheel_pos * 3, 255 - wheel_pos * 3
    else:
        wheel_pos -= 170
        return wheel_pos * 3, 255 - wheel_pos * 3, 0

def go_deepsleep(t):
    set_dotstar_power(False)
    machine.deepsleep(t)

