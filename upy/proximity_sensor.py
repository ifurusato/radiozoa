
from sensor import Sensor
from machine import Pin

from logger import Logger, Level
from orientation import Orientation

class ProximitySensor(Sensor):

    def __init__(self, orientation, callback=None):
        super().__init__(orientation)
        pin_number = -1
        if orientation is Orientation.PORT:
            pin_number = 27
        elif orientation is Orientation.STBD:
            pin_number = 20
        else:
            raise ValueError('invalid orientation.')
        self._log = Logger('proximity:{}'.format(orientation.name.lower()), level=Level.INFO)
        self._pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self._callback = callback
        self._pin.irq(handler=self._handle_callback, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
        self._log.info('{} proximity sensor ready on pin {}.'.format(orientation.description, pin_number))

    def _handle_callback(self, callback):
        '''
        Handle a callback execution when the sensor is triggered, if the sensor is enabled.
        '''
        if self.enabled:
            self._log.info('proximity sensor callback…')
            self._callback(self._pin)
        else:
            self._log.warn('proximity sensor callback disabled.')

    @property
    def triggered(self):
        '''
        Returns True if the proximity sensor is currently triggered.
        '''
        return self._pin.value() == 1

    @property
    def value(self):
        return self._pin.value()

