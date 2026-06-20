# motor class

from colorama import Fore

from orientation import Orientation
from logger import Logger, Level

class Motor:

    def __init__(self, orientation=None, board=None):
        '''
        Constructs a motor for the orientation, provided with the hardware library connection.

        Args:
            orientation (Orientation):      the orientation of this motor: port or starboard.
            board (KitronikPicoRobotics):   the hardware support library's object
        '''
        if orientation is Orientation.PORT:
            self._name = 'port'
            self._color = Fore.RED
        elif orientation is Orientation.STBD:
            self._name = 'stbd'
            self._color = Fore.GREEN
        else:
            raise TypeError('expected PORT or STBD orientation.')

        self._log = Logger('{} motor'.format(self._name), Level.INFO)
        self._channel = orientation.channel
        if board is None:
            self._log.warn('no motor controller provided.')
#           raise ValueError('expected motor controller board argument.')
        self._board = board
        self._speed = 0 # initially stopped
        self._log.info(self._color + "{} motor ready on channel {}.".format(self._name, self._channel))

    @property
    def speed(self):
        '''
        Return the last speed value set for this motor (not the actual speed of the motor,
        which we cannot measure).
        '''
        return self._speed

    def set_speed(self, speed):
        '''
        Set the speed of this motor to the argument.
        '''
        if self._board is None:
            self._log.warn('no motor controller available.')
            return
        if speed is None:
            raise TypeError("null speed argument.")
        elif not isinstance(speed, int):
            raise TypeError("speed must be an int, but got {}".format(type(speed)))
        if not -100 <= speed <= 100:
            raise ValueError("speed must be between -100 and 100, but got {}".format(speed))
        try:
            if speed == 0:
                # stop the motor
                self._board.motorOff(self._channel)

            elif speed < 0:
                # the motor should run in reverse
                speed = abs(speed)
                self._log.info("REV speed on " + self._color + '{}'.format(self._name)
                        + Fore.CYAN + " channel {}:".format(self._channel) + Fore.WHITE + " {}".format(speed))
                self._board.motorOn(self._channel, 'r', speed) # the call to the hardware library

            else:
                # the motor should run forward
                self._log.info("FWD speed on " + self._color + '{}'.format(self._name)
                        + Fore.CYAN + " channel {}:".format(self._channel) + Fore.WHITE + " {}".format(speed))
                self._board.motorOn(self._channel, 'f', speed) # the call to the hardware library

        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self._log.error("timeout occurred with controller: {}".format(e))
            else:
                raise # raises e
        finally:
            self._speed = speed
        self._log.info(self._color + "set {} motor speed to: {}".format(self._name, speed))

    def stop(self):
        '''
        Stop the motor.
        '''
        self.set_speed(0)

#EOF
