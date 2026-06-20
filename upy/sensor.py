
from orientation import*

class Sensor:

    def __init__(self, orientation):
        if orientation is None:
            raise ValueError('no orientation provided.')
        elif type(orientation) is not Orientation:
            raise ValueError('argument was not an orientation.')
        else:
            self._orientation = orientation
        self._enabled  = True # default

    @property
    def enabled(self):
        return self._enabled

    def enable(self):
        self._log.info('🍊 {} enabled.'.format(type(self)))
        self._enabled = True

    def disable(self):
        self._log.info('🍊 {} disabled.'.format(type(self)))
        self._enabled = False

    @property
    def orientation(self):
        '''
        Usage:
            orient = sensor.orientation
        '''
        return self._orientation

    def get_orientation(self):
        '''
        Usage:
            orient = sensor.get_orientation()
        '''
        return self._orientation

