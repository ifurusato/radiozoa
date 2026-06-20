#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-14
# modified: 2026-06-14

import sys

from logger import Logger, Level
from motor_controller import MotorController

# force module reload
for mod in ['stop']:
    if mod in sys.modules:
        del sys.modules[mod]

# ...............................................................

mc = None
log = Logger('stop', Level.INFO)

try:
    mc = MotorController()
    mc.enable()
    log.info('stopping…')
    mc.stop()
except KeyboardInterrupt:
    log.info('interrupted.')
except Exception as e:
    log.error('{} raised: {}'.format(type(e), e))
    sys.print_exception(e)
finally:
    if mc:
        mc.close()

#EOF
