#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-06-09
# modified: 2026-06-09

import time
from analog_ctrl import AnalogControl
from config_loader import ConfigLoader

config = ConfigLoader.configure('config.yaml')
control = AnalogControl(config)

while True:
    raw        = control.raw_value
    percentage = control.percentage_value
    scaled     = control.value

    print("raw: {0} | percentage: {1} |  scaled: {2}".format(raw, percentage, scaled))
    time.sleep(0.1)

#EOF
