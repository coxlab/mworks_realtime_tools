#!/usr/bin/env python

import logging

import zmq

from mw_listener import MWListener
from spike_listener import SpikeListener

class DataSource(object):
    def __init__(self, config, zmqContext=zmq.Context()):

        # listen for mw events
        self.mw_listener = MWListener(\
                config.get('mworks', 'conduitname'),
                config.getlist('mworks', 'eventnames'))
        self.mw_listener.register_callback(self.process_mw_event)
        
        # listen for spikes
        pathFunc = lambda i : config.get('audio', 'socketTemplate') % i
        channels = range( config.getint('audio', 'socketStart'),\
                config.getint('audio', 'socketEnd'))
        self.spike_listener = SpikeListener(pathFunc, channels,\
                zmqContext)
        self.spike_listener.register_callback(self.process_spike_event)

        self.sampling_rate = float(config.getint('audio', 'sampling_rate'))

    def process_mw_event(event):
        logging.debug("DataSource recieved" + \
                "MW: %i : %i : %s" % \
                (event.code, event.time, str(event.data)))

    def process_spike_event(event):
        logging.debug("DataSource recieved" + \
                "Spike: %i : %i" % \
                (event.time_stamp, event.channel_id))

    def update(self):
        logging.debug("Data Source updating")
        while self.spike_listener.update(): pass
