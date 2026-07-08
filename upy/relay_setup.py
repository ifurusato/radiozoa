#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2026-07-08
# modified: 2026-07-08

import sys

from colorama import Fore, Style
from event import *
from logger import Logger, Level

from networking import Networking
from gateway import NetworkGateway
from surveyor import Surveyor
from relay import Relay

ENABLE_TOUCH_SUBSCRIBER = False # we use its subclass RemoteControl instead

class RelaySetup:

    def __init__(self, config, message_bus, message_factory, pixel, level=Level.INFO):

        self._log = Logger('main', Level.INFO)
        try:

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

            elif ENABLE_TOUCH_SUBSCRIBER and _relay.is_endpoint():
                self._log.info("creating touch subscriber…")
                from touch_subscriber import TouchSubscriber

                _touch_subscriber = TouchSubscriber(config, message_bus, pixel)
                _touch_subscriber.enable()

            if not _relay.is_initiator():
                from rtc_subscriber import RtcSubscriber

                _rtc_subscriber = RtcSubscriber(config, message_bus)

            self._log.info("scheduling relay task and starting event loop…")
            _relay.enable()
        #   self._log.info("relay enabled.")
            if _initiator:
                _initiator.enable()
        #       self._log.info("initiator enabled.")


        except KeyboardInterrupt:
            self._log.info('interrupted.')
        except Exception as e:
            self._log.error('{} raised: {}'.format(type(e), e))
            sys.print_exception(e)
        finally:
            if pixel:
                pixel.close()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

'''
from config_loader import ConfigLoader
from message_bus import MessageBus
from message_factory import MessageFactory
from pixel import Pixel

_config = ConfigLoader.configure('relay_config.yaml')
_message_bus     = MessageBus()
_message_factory = MessageFactory(_message_bus)
_pixel = Pixel(pin=48, pixel_count=1, color_order='GRB', brightness=0.1)

relay_setup = RelaySetup(_config, _message_bus, _message_factory, _pixel, level=Level.INFO);

print('complete')
'''

#EOF
