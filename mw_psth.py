#!/myPython/bin/python
############################!/usr/bin/env python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import sys, time

import zmq
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# import mworks conduit
sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
from mworks.conduit import IPCClientConduit

from physio_online.spike_listener import SpikeListener
from physio_online.clock_sync import ClockSync
from physio_online.stimsorter import Stim, StimSpikeSyncer
from physio_online import psth

conduitName = 'server_event_conduit'

if __name__ == '__main__':
    # channel mapping (tdt to position on probe)
    global channelMapping
    channelMapping = [3, 9, 7, 13, 5, 17, 1, 21, 14, 2, 8, 6, 18, 4, 12, 10, 23, 15, 31, 27, 19, 11, 29, 25, 30, 26, 20, 16, 32, 28, 24, 22]    
    channelNames = [7,10,1,14,5,12,3,11,2,16,22,15,4,9,18,28,6,13,21,27,8,32,17,31,24,26,20,30,23,25,19,29]
    
    zmqContext = zmq.Context()
    
    # setup clock sync
    pathFunc = lambda i : "ipc:///tmp/pixel_clock/%i" % i
    global clockSync
    clockSync = ClockSync(pathFunc, range(4), zmqContext=zmqContext)
    # needs: clockSync.update() and clockSync.match()
    # if not (cs.offset is None):
    #     if cs.offset != offset:
    #         offset = cs.offset
    #         print offset, cs.matchLength, cs.err
    
    # setup stim spike syncer
    global stimSpikeSyncer
    stimSpikeSyncer = StimSpikeSyncer()
    # process_spike(self, channel, time)
    # get_stim_spikes(self, channel, stimI)
    # process_event(self, event, conv=1./1000000.)
    # find_stim(self, stim)
    
    # setup psth
    
    # setup mworks conduit
    conduitName = 'server_event_conduit'
    conduit = IPCClientConduit(conduitName)
    conduit.initialize()
    conduit.register_local_event_code(0,'#stimDisplayUpdate')
    conduit.register_callback_for_name('#stimDisplayUpdate', process_mw_event)
    
    def process_mw_event(event):
        global stimSpikeSyncer, clockSync
        stimSpikeSyncer.process_mw_event(event)
        clockSync.process_mw_event(event)
    
    # setup spike listener
    global sl
    pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    sl = SpikeListener(pathFunc, xrange(32), zmqContext=zmqContext)
    
    def process_spike(wb): # overload process_spike
        global stimSpikeSyncer, clockSync
        
        if not (clockSync is None):
            # spikeMWTime = clockSync.clockSync.au_to_mw(wb.time_stamp/44100.)
            stimSpikeSyncer.process_spike(wb.channel_id, clockSync.clockSync.au_to_mw(wb.time_stamp/44100.))
        else:
            print "Clock not synced!! dropping spike"
        # # if not (cs.offset is None):
        # #     if cs.offset != offset:
        # #         offset = cs.offset
        # #         print offset, cs.matchLength, cs.err
        # if audioTimeOffset == None:
        #     audioTimeOffset = time.time() - wb.time_stamp/44100.
        # # print "SE:", wb.channel_id, wb.time_stamp/44100. + audioTimeOffset
        # raster.add_event(wb.time_stamp/44100. + audioTimeOffset, channelMapping[wb.channel_id]-1)
    
    sl.process_spike = process_spike
    
    # need to call at idle
    # 1. sl.update()
    # 2. clockSync.update() and clockSync.match()
    # ---
    # for getting data :: 
    #   process_spike(self, channel, time)
    #   get_stim_spikes(self, channel, stimI)
    #   process_event(self, event, conv=1./1000000.)
    #   find_stim(self, stim)
    
    fig = plt.figure()
    gs = gridspec.GridSpec(1, 5, width_ratios=[1,12,1,1,1])
    global livepsth
    livepsth = psth.LivePSTH(fig.add_subplot(gs[1]))
    
    global channel
    global stim
    # TODO setup default
    stimDict = { 'name': '0',
                    'pos_x': 0, 'pos_y': 0,
                    'size_x': 1, 'size_y': 1,
                    'rotation': 0 }
    stim = Stim(stimDict)
    
    global transLookup
    transLookup = [(0.,-1.5), (-1.5, 0.), (0.,0.), (1.5,0.), (0.,-1.5)]
    def set_trans(t):
        global stim, transLookup
        stim.pos_x, stim.pos_y = transLookup[t]
    
    global sizeLookup
    sizeLookup = [0.75, 1., 1.25]
    def set_size(s):
        global stim, sizeLookup
        stim.size_x = sizeLookup[s]
        stim.size_y = sizeLookup[s]
    
    def set_name(i):
        global stim
        stim.name = str(i)
        get_spikes()
    
    def set_channel(c):
        global channel
        channel = c
        get_spikes()
    
    def get_spikes():
        global clockSync, sl, stimSpikeSyncer
        sl.update()
        clockSync.update()
        clockSync.match()
        
        global channel, stim
        stimI = stimSpikeSyncer.find_stim(stim)
        if stimI != -1:
            spikes = stimSpikeSyncer.get_stim_spikes(channel, stimI):
            if len(spikes) > 0:
                global livepsth
                livepsth.draw_spikes(spikes)
    
    cc = psth.VerticalSelect(fig.add_subplot(gs[0]),32,title='C',updateFunc=set_channel) # channel control
    sc = psth.VerticalSelect(fig.add_subplot(gs[2]),12,title='I',updateFunc=set_name) # stimulus control
    tc = psth.VerticalSelect(fig.add_subplot(gs[3]),5,title='T',updateFunc=set_trans) # translation control
    zc = psth.VerticalSelect(fig.add_subplot(gs[4]),3,title='S',updateFunc=set_size) # size control
    
    cc.connect()
    sc.connect()
    tc.connect()
    zc.connect()

    plt.show()
