#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-27
# modified: 2026-08-22

class Direction:
    _instances = {}

    def __init__(self, id, name, abbr):
        self._id = id
        self._name = name
        self._abbr = abbr
        Direction._instances[id] = self

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def abbrevisation(self):
        return self._abbr

    @classmethod
    def from_id(cls, id):
        return cls._instances.get(id)

# used by Relay
OUTBOUND = Direction( 1, 'outbound',          'outb') # downstream, forward
INBOUND  = Direction(-1, 'inbound',           'inbd') # upstream, reverse

# general movement directives
STOPPED           = ( 0, 'stopped',           'stop')
AHEAD             = ( 2, 'ahead',             'ahed')
ASTERN            = ( 3, 'astern',            'astn')
PORT              = ( 4, 'port',              'port')
STBD              = ( 5, 'starboard',         'stbd')
CLOCKWISE         = ( 6, 'clockwise',         'clws')
COUNTER_CLOCKWISE = ( 7, 'counter-clockwise', 'ccwz')

#EOF
