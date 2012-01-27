#!/usr/bin/env python

import logging

import pymongo
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

    def process_mw_event(self, event):
        pass

    def process_spike_event(self, event):
        pass

    def update(self):
        logging.debug("Data Source updating")
        while self.spike_listener.update(): pass

class DebugDataSource(DataSource):
    def process_mw_event(self, event):
        logging.debug("DataSource recieved" + \
                "MW: %s : %i : %i : %s" % \
                (event.name, event.code, event.time, str(event.data)))
    def process_spike_event(self, event):
        logging.debug("DataSource recieved" + \
                "Spike: %i : %i" % \
                (event.time_stamp, event.channel_id))

class MongoDataSource(DataSource): # or DebugDataSource for verbose logging.debug calls
    def __init__(self, config, zmqContext=zmq.Context()):
        DataSource.__init__(self, config, zmqContext)

        # setup mongo
        hostname = config.get('mongo', 'hostname')
        self.conn = pymongo.Connection(hostname)

        db_name = config.get('mongo', 'database')
        self.db = self.conn[db_name]

        spike_collection = config.get('mongo', 'spike_collection')
        self.spikes = self.db[spike_collection]

        mworks_collection = config.get('mongo', 'mworks_collection')
        self.mworks = self.db[mworks_collection]

    def process_mw_event(self, event):
        self.mworks.insert(self.mworks_to_mongo(event))

    def process_spike_event(self, event):
        self.spikes.insert(self.spike_to_mongo(event))

    def mworks_to_mongo(self, event):
        return {'code': event.code, 'name': event.name,\
                'time': event.time, 'data': event.data}
    
    def spikes_to_mongo(self, event):
        return {'ch': event.channel_id, 'aut': event.time_stamp}

#TODO make fake mongodatasource for complete offline testing
