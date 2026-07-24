#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2025-05-23
# modified: 2026-07-19

import time
from pixel import Pixel
from logger import Level

class Ring(Pixel):
    NAME = 'ring'
    def __init__(self, config=None, level=Level.INFO):
        _cfg = config['rros']['ring']
        _pin         = _cfg['pin']
        _pixel_count = _cfg['pixel_count'] 
        _brightness  = _cfg['brightness'] 
        Pixel.__init__(self,
                name=Ring.NAME,
                pin=_pin,
                pixel_count=_pixel_count,
                brightness=_brightness,
                level=level)
        self._log.info('ready')

#EOF
