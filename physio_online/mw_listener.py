#!/usr/bin/env python

import logging

from mworks.conduit import IPCClientConduit

class MWListener(object):
    def __init__(self, conduit_name, event_names):
        self.callbacks = []
        self.conduit = IPCClientConduit(conduit_name)
        self.conduit.initialize()
        self.event_names = event_names
        for (i,event_name) in enumerate(event_names):
            self.conduit.register_local_event_code(i, event_name)
            self.conduit.register_callback_for_name(event_name,\
                    self.process_event)

    def process_event(self, event):
        if event is None:
            return
        logging.debug("MWListener recieved" + \
                "%i : %i : %s" % \
                (event.code, event.time, str(event.data)))
        event.name = self.event_names[event.code]
        [cb(event) for cb in self.callbacks]

    def register_callback(self, func):
        self.callbacks.append(func)
