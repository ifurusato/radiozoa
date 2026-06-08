#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2021-06-29
# modified: 2026-06-04

from logger import Logger, Level

class Component:
    '''
    A basic component providing enabled, suppressed and closed state flags.
    This is a simplification of the CPython version.

    :param name:       the component name
    :param suppressed: initial suppressed state (default False)
    :param enabled:    initial enabled state (default False)
    '''
    def __init__(self, name, suppressed=False, enabled=False, level=Level.INFO):
        if name is None:
            raise ValueError('null name argument.')
        self._name       = name
        self._log        = Logger(name, level)
        self._suppressed = suppressed
        self._enabled    = enabled
        self._closed     = False

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def name(self):
        return self._name

    @property
    def enabled(self):
        return self._enabled

    @property
    def disabled(self):
        return not self._enabled

    @property
    def suppressed(self):
        return self._suppressed

    @property
    def released(self):
        return not self._suppressed

    @property
    def is_active(self):
        '''
        Returns True if enabled and not suppressed.
        '''
        return self._enabled and not self._suppressed

    @property
    def closed(self):
        return self._closed

    def enable(self):
        if not self._closed:
            self._enabled = True
            self._log.info('enabled.')
        else:
            self._log.warn('already closed.')

    def disable(self):
        self._log.info('disabled.')
        self._enabled = False

    def suppress(self):
        self._suppressed = True
        self._log.info('suppressed.')

    def release(self):
        self._suppressed = False
        self._log.info('released.')

    def close(self):
        if not self._closed:
            self._enabled = False
            self._closed  = True
            self._log.info('closed.')
        else:
            self._log.warn('already closed.')

#EOF
