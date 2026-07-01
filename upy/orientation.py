# this class defines two orientations

class Orientation:
    '''
    A pseudo-enum enumerating the different orientations, port (left) and starboard (right).
    '''
    def __init__(self, name, description, channel):
        self._name = name
        self._description = description
        self._channel = channel

    @property
    def name(self):
        '''
        Return the name of this orientation.
        '''
        return self._name.lower()

    @property
    def description(self):
        '''
        Return the descripton of this orientation.
        '''
        return self._description

    @property
    def channel(self):
        '''
        Return the channel or motor number.
        '''
        return self._channel

    def __repr__(self):
        '''
        Return a string representation of the Orientation
        '''
        return "Orientation.{}".format(self._name)


# now instantiate our two orientations:
Orientation.PORT = Orientation("PORT", "port", 1)
Orientation.STBD = Orientation("STBD", "starboard", 2)
Orientation.CNTR = Orientation("CNTR", "center", 3)
Orientation.ALL  = Orientation("ALL",  "all", 4)
