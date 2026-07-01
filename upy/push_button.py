
import time
from sensor import Sensor
from machine import Pin
from colorama import Fore, Style

from logger import Logger, Level
from orientation import Orientation

class PushButton(Sensor):

    def __init__(self, pin_number=None, callback=None):
        '''
        A push button implementation that includes a debounce feature. The callback
        is used to indicate an event has occurred.

        There is an enable/disable flag to keep the button from false triggering.
        The default is enabled.

        Args:
            pin_number: the GPIO number of the Pin
            callback:   the callback to be executed when the button is triggered
        '''
        # we made a bad assumption: not all sensors have an orientation so we pass any orientation
        super().__init__(Orientation.PORT) 
        if pin_number is None:
            pin_number = 35 # default GPIO pin
        self._log = Logger('pushbutton', level=Level.INFO)
        self._value    = False
        self._callback = callback
        self._ms_ago   = 500 # milliseconds debounce time
        self._next_call = time.ticks_ms() + self._ms_ago
        self._pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self._pin.irq(handler=self._debounce_handler, trigger=Pin.IRQ_RISING) # Pin.IRQ_FALLING | Pin.IRQ_RISING)
        self._log.info('push button ready on pin {}; enabled? {}'.format(pin_number, self.enabled))

    def _call_callback(self, pin):
        if self._callback is not None:
            try:
                self._callback(pin)
            except Exception as e:
                self._log.error('{} raised executing callback: {}'.format(type(e), e))
        else:
            self._log.warn('no callback available.')

    def _debounce_handler(self, pin):
        '''
        Attach a callback function that is executed when the sensor is triggered.
        '''
        if time.ticks_ms() > self._next_call:
            self._next_call = time.ticks_ms() + self._ms_ago
            if self.enabled:
                self._log.info(Style.BRIGHT + 'debounce handler triggered.')
                self._value = not self._value
                if self._value:
                    self._log.info(Style.BRIGHT + 'PUSHBUTTON EVENT: value={}'.format(self._value))
                else:
                    self._log.info(Style.NORMAL + 'PUSHBUTTON EVENT: value={}'.format(self._value))
                self._call_callback(pin)
            else:
                self._log.warn('push button not enabled.')
        else:
            self._log.info(Style.DIM + 'debounce handler triggered.')

    @property
    def value(self):
        '''
        Returns the current toggled value of the button (not the pin state).
        '''
        return self._value

