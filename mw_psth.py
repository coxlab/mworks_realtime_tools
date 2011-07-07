#!/myPython/bin/python
############################!/usr/bin/env python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import logging, sys, threading, time

# import zmq
import numpy as np
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.widgets as widgets

# import mworks conduit
# sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
# from mworks.conduit import IPCClientConduit

# from physio_online.spike_listener import SpikeListener
# from physio_online.clock_sync import ClockSync
# from physio_online.stimsorter import Stim, StimSpikeSyncer
# from physio_online import psth
import physio_online
import physio_online.psth # temporary module

# conduitName = 'server_event_conduit'

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    config = physio_online.cfg.Config()
    global core
    core = physio_online.core.Core(config)
    
    # zmqContext = zmq.Context()
    #     
    #     # setup clock sync
    #     pathFunc = lambda i : "ipc:///tmp/pixel_clock/%i" % i
    #     global clockSync
    #     clockSync = ClockSync(pathFunc, range(4), zmqContext=zmqContext, maxErr=2)
    #     # needs: clockSync.update() and clockSync.match()
    #     # if not (cs.offset is None):
    #     #     if cs.offset != offset:
    #     #         offset = cs.offset
    #     #         print offset, cs.matchLength, cs.err
    #     
    #     # setup stim spike syncer
    #     global stimSpikeSyncer
    #     stimSpikeSyncer = StimSpikeSyncer()
    #     # process_spike(self, channel, time)
    #     # get_stim_spikes(self, channel, stimI)
    #     # process_event(self, event, conv=1./1000000.)
    #     # find_stim(self, stim)
    #     
    #     # setup psth
    #     
    #     # setup mworks conduit
    #     conduitName = 'server_event_conduit'
    #     conduit = IPCClientConduit(conduitName)
    #     conduit.initialize()
    #     conduit.register_local_event_code(0,'#stimDisplayUpdate')
    #     
    #     def process_mw_event(event):
    #         global stimSpikeSyncer, clockSync
    #         if event is None:
    #             return
    #         else:
    #             event.value = event.data
    #         stimSpikeSyncer.process_mw_event(event)
    #         clockSync.process_mw_event(event)
    #     
    #     conduit.register_callback_for_name('#stimDisplayUpdate', process_mw_event)
    #     
    #     # setup spike listener
    #     global sl
    #     pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    #     sl = SpikeListener(pathFunc, xrange(32), zmqContext=zmqContext)
    #     
    #     def process_spike(wb): # overload process_spike
    #         global stimSpikeSyncer, clockSync
    #         
    #         if not (clockSync.offset is None):
    #             # spikeMWTime = clockSync.clockSync.au_to_mw(wb.time_stamp/44100.)
    #             stimSpikeSyncer.process_spike(wb.channel_id, clockSync.au_to_mw(wb.time_stamp/44100.))
    #         else:
    #             logging.warning("Clock not synced!! dropping spike on %i" % wb.channel_id)
    #         # # if not (cs.offset is None):
    #         # #     if cs.offset != offset:
    #         # #         offset = cs.offset
    #         # #         print offset, cs.matchLength, cs.err
    #         # if audioTimeOffset == None:
    #         #     audioTimeOffset = time.time() - wb.time_stamp/44100.
    #         # # print "SE:", wb.channel_id, wb.time_stamp/44100. + audioTimeOffset
    #         # raster.add_event(wb.time_stamp/44100. + audioTimeOffset, channelMapping[wb.channel_id]-1)
    #     
    #     sl.process_spike = process_spike
    
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
    livepsth = physio_online.psth.LivePSTH(fig.add_subplot(gs[1]))
    
    global channel
    channel = 0
    global stim
    # TODO setup default
    stimDict = { 'name': '0',
                    'pos_x': -25, 'pos_y': 0,
                    'size_x': 70, 'size_y': 70,
                    'rotation': 0 }
    stim = physio_online.stimsorter.Stim(stimDict)
    
    global transLookup
    transLookup = [(-25,-1.5), (-26.5, 0.), (-25,0.), (-23.5,0.), (-25,-1.5)]
    def set_trans(t):
        global stim, transLookup
        stim.pos_x, stim.pos_y = transLookup[t]
        get_spikes()
    
    global sizeLookup
    sizeLookup = [35, 70, 140]
    def set_size(s):
        global stim, sizeLookup
        stim.size_x = sizeLookup[s]
        stim.size_y = sizeLookup[s]
        get_spikes()
    
    def set_name(i):
        global stim
        stim.name = str(i)
        get_spikes()
    
    def set_channel(c):
        global channel
        channel = c
        get_spikes()
    
    def get_spikes():
        # global clockSync, sl, stimSpikeSyncer
        global core
        core.update()
        
        global channel, stim
        stimI = core.stimSpikeSyncer.find_stim(stim)
        
        stimI = core.stimSpikeSyncer.find_stim(stim)
        if stimI != -1:
            spikes = core.stimSpikeSyncer.get_stim_spikes(channel, stimI)
            if len(spikes) > 0:
                global livepsth
                livepsth.draw_spikes(spikes)
            else:
                logging.debug("No spikes on channel %i" % channel)
        else:
            logging.warning("Unknown stimulus: %s" % str(stim))
        
        
        # while clockSync.update():
        #     pass
        # clockSync.match()
        # while sl.update():
        #     pass
        # 
        # 
        # stimI = stimSpikeSyncer.find_stim(stim)
        # if stimI != -1:
        #     spikes = stimSpikeSyncer.get_stim_spikes(channel, stimI)
        #     if len(spikes) > 0:
        #         global livepsth
        #         livepsth.draw_spikes(spikes)
        #     else:
        #         logging.debug("No spikes on channel %i" % channel)
        # else:
        #     logging.warning("Unknown stimulus: %s" % str(stim))
    
    # global cDict
    # cDict = {}
    # for c in xrange(32):
    #     cDict[str(c)] = c
    # def cc_callback(label):
    #     global cDict
    #     c = cDict[label]
    #     set_channel(c)
    # cc = widgets.RadioButtons(fig.add_subplot(gs[0]),cDict.keys())
    # cc.on_clicked(cc_callback)
    cc = physio_online.psth.VerticalSelect(fig.add_subplot(gs[0]),32,title='C',updateFunc=set_channel) # channel control
    
    # global sDict
    # sDict = {}
    # for s in xrange(12):
    #     sDict[str(c)] = c
    # def sc_callback(label):
    #     global sDict
    #     s = cDict[label]
    #     set_name(s)
    # sc = widgets.RadioButtons(fig.add_subplot(gs[2]),sDict.keys())
    # sc.on_clicked(sc_callback)
    sc = physio_online.psth.VerticalSelect(fig.add_subplot(gs[2]),12,title='I',updateFunc=set_name) # stimulus control
    
    # global tDict
    # tDict = {'0,1': 0, '-1,0': 1, '0,0': 2, '1,0': 3, '0,-1': 4}
    # def tc_callback(label):
    #     global tDict
    #     t = tDict[label]
    #     set_trans(t)
    # tc = widgets.RadioButtons(fig.add_subplot(gs[3]),tDict.keys())
    # tc.on_clicked(tc_callback)
    tc = physio_online.psth.VerticalSelect(fig.add_subplot(gs[3]),5,title='T',updateFunc=set_trans) # translation control
    
    # global zDict
    # zDict = {'0.75': 0, '1.0': 1, '1.25': 2}
    # def zc_callback(label):
    #     global zDict
    #     z = zDict[label]
    #     set_size(z)
    # zc = widgets.RadioButtons(fig.add_subplot(gs[4]),zDict.keys())
    # zc.on_clicked(zc_callback)
    zc = physio_online.psth.VerticalSelect(fig.add_subplot(gs[4]),3,title='S',updateFunc=set_size) # size control
    
    cc.connect()
    sc.connect()
    tc.connect()
    zc.connect()
    
    # def update(event):
    #         global clockSync, sl, stimSpikeSyncer
    #         while sl.update():
    #             pass
    #         while clockSync.update():
    #             pass
    #         clockSync.match()
    #         if clockSync.offset is None:
    #             print "MW:", [e[1] for e in clockSync.mwEvents]
    #             print "AU:", [e[1] for e in clockSync.auEvents]
    
    def update(event):
        global core
        core.update()
    
    fig.canvas.mpl_connect("idle_event", core.update)
    fig.canvas.mpl_connect("motion_notify_event", update)
    
    plt.show()
