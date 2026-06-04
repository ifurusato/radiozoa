
import sys
from i2c_scanner import I2CScanner

# force module reload
for mod in ['scan', 'i2c_scanner']:
    if mod in sys.modules:
        del sys.modules[mod]

# def __init__(self, i2c_id=1, scl=None, sda=None):
scanner = I2CScanner(i2c_id=1, scl=22, sda=21)   
scanner.i2cdetect()

