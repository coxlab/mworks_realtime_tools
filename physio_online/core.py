#!/usr/bin/env python
"""
This is the core physio_online object
"""

import logging, sys

import zmq

# import mworks conduit
sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
from mworks.conduit import IPCClientConduit

from spike_listener import SpikeListener
from clock_sync import ClockSync
from stimsorter import Stim, StimSpikeSyncer

class Core(object):
    def __init__(self, config, zmqContext=None):
        if zmqContext is None:
            zmqContext = zmq.Context()
        
        # make clock synchronizer
        pathFunc = lambda i: config.get('pixel clock', 'socketTemplate') % i
        channels = range(config.getint('pixel clock', 'socketStart'), config.getint('pixel clock', 'socketEnd'))
        self.clockSync = ClockSync(pathFunc, channels, zmqContext=zmqContext, maxErr=config.getint('pixel clock', 'maxError'))
        
        # make stim spike syncer
        self.stimSpikeSyncer = StimSpikeSyncer()
        
        # make mworks conduit
        self.mw_conduit = IPCClientConduit(config.get('mworks','conduitname'))
        self.mw_conduit.initialize()
        self.mw_conduit.register_local_event_code(0,'#stimDisplayUpdate')
        self.mw_conduit.register_callback_for_name('#stimDisplayUpdate', self.process_mw_event)
        
        # make spike listener
        # pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
        pathFunc = lambda i : config.get('audio', 'socketTemplate') % i
        channels = range(config.getint('audio', 'socketStart'), config.getint('audio', 'socketEnd'))
        self.spikeListener = SpikeListener(pathFunc, channels, zmqContext=zmqContext)
        self.spikeListener.register_callback(self.process_spike)
        
    
    def process_mw_event(self, event):
        # global stimSpikeSyncer, clockSync
        if event is None:
            return
        else:
            event.value = event.data
        self.stimSpikeSyncer.process_mw_event(event)
        self.clockSync.process_mw_event(event)
    
    def process_spike(self, wb):
        # global stimSpikeSyncer, clockSync

        if not (self.clockSync.offset is None):
            # spikeMWTime = clockSync.clockSync.au_to_mw(wb.time_stamp/44100.)
            self.stimSpikeSyncer.process_spike(wb.channel_id, self.clockSync.au_to_mw(wb.time_stamp/float(config.getint('audio','sampRate'))))
        else:
            logging.warning("Clock not synced!! dropping spike on %i" % wb.channel_id)
    
    def update(self):
        """
        Updates the various components of the physio_online core, should be called in the main loop
        """
        logging.debug("Core updating")
        # global clockSync, sl, stimSpikeSyncer
        while self.spikeListener.update():
            pass
        while self.clockSync.update():
            pass
        self.clockSync.match()
        if self.clockSync.offset is None:
            logging.debug("MW: %s" % str([e[1] for e in self.clockSync.mwEvents]))
            logging.debug("AU: %s" % str([e[1] for e in self.clockSync.auEvents]))
    
    def clear_spikes(self):
        """
        Clears all spikes accumulated so far
        """
        self.stimSpikeSyncer.clear_spikes()
    
    def clear_stimuli(self):
        self.stimSpikeSyncer.clear_stimuli()
        