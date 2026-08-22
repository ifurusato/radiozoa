#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-08-21
# modified: 2026-08-21

class IntentVector:
    '''
    An intent vector as a struct.
    '''
    def __init__(self, vx=0.0, vy=0.0, omega=0.0):
        self.vx = vx
        self.vy = vy
        self.omega = omega

    @property
    def vx(self):
        return self._vx

    @vx.setter
    def vx(self, vx):
        self._vx = vx

    @property
    def vy(self):
        return self._vy

    @vy.setter
    def vy(self, vy):
        self._vy = vy

    @property
    def omega(self):
        return self._omega

    @omega.setter
    def omega(self, omega):
        self._omega = omega

    def clear(self):
        self.vx = 0.0
        self.vy = 0.0
        self.omega = 0.0

    def to_tuple(self):
        return (self.vx, self.vy, self.omega)

#EOF
