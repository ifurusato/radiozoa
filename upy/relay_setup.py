#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-07-08
# modified: 2026-07-30

import sys
from colorama import Fore, Style

from event import *
from logger import Logger, Level
from networking import Networking
from gateway import NetworkGateway
from surveyor import Surveyor
from relay import Relay

class RelaySetup:

    def __init__(self, config, message_bus, message_factory, pixel, level=Level.INFO):

        self._log = Logger('main', Level.INFO)
        try:
            _cfg = config['rros']['relay_setup']
            _enable_touch_subscriber = _cfg['enable_touch_subscriber'] # we use its subclass RemoteControl instead
            _networking = Networking()
            # create relay
            _relay = Relay(config=config, networking=_networking, message_factory=message_factory, pixel=pixel)
            # create surveyor
            self._log.info("creating surveyor…")
            _surveyor = Surveyor(config, _networking, message_bus, message_factory, _relay)
            # create gateway
            _gateway = NetworkGateway(config, message_bus, message_factory, _relay)
            _initiator = None
            if _relay.is_initiator():
                self._log.info("establishing initiator…")
                from initiator import Initiator
                _initiator = Initiator(config, message_bus, message_factory, pixel)

                self._log.info("creating touch publisher…")
                from touch_publisher import TouchPublisher

                _touch_publisher = TouchPublisher(config, message_bus, message_factory)
                _touch_publisher.enable()

            elif _enable_touch_subscriber and _relay.is_endpoint():
                self._log.info("creating touch subscriber…")
                from touch_subscriber import TouchSubscriber

                _touch_subscriber = TouchSubscriber(config, message_bus, pixel)
                _touch_subscriber.enable()

            if not _relay.is_initiator():
                from rtc_subscriber import RtcSubscriber

                _rtc_subscriber = RtcSubscriber(config, message_bus)

            self._log.info("scheduling relay task and starting event loop…")
            _relay.enable()
            if _initiator:
                _initiator.enable()

        except KeyboardInterrupt:
            self._log.info('interrupted.')
        except Exception as e:
            self._log.error('{} raised: {}'.format(type(e), e))
            sys.print_exception(e)
        finally:
            if pixel:
                pixel.close()

#EOF
