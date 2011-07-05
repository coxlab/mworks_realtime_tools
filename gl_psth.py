#!/myPython/bin/python
############################!/usr/bin/env python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import copy, logging, sys, threading, time

import zmq
import numpy as np
import glumpy
import glumpy.atb as atb
import ctypes as ct
# import glumpy.pylab as gplt
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import OpenGL.GLUT as glut
import OpenGL.GL as gl

# import mworks conduit
sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
from mworks.conduit import IPCClientConduit

from physio_online.spike_listener import SpikeListener
from physio_online.clock_sync import ClockSync
from physio_online.stimsorter import Stim, StimSpikeSyncer
from physio_online import psth

conduitName = 'server_event_conduit'

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    zmqContext = zmq.Context()
    
    # setup clock sync
    pathFunc = lambda i : "ipc:///tmp/pixel_clock/%i" % i
    global clockSync
    clockSync = ClockSync(pathFunc, range(4), zmqContext=zmqContext, maxErr=2)
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
    
    def process_mw_event(event):
        global stimSpikeSyncer, clockSync
        if event is None:
            return
        else:
            event.value = event.data
        stimSpikeSyncer.process_mw_event(event)
        clockSync.process_mw_event(event)
    
    conduit.register_callback_for_name('#stimDisplayUpdate', process_mw_event)
    
    # setup spike listener
    global sl
    pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    sl = SpikeListener(pathFunc, xrange(32), zmqContext=zmqContext)
    
    def process_spike(wb): # overload process_spike
        global stimSpikeSyncer, clockSync
        
        if not (clockSync.offset is None):
            # spikeMWTime = clockSync.clockSync.au_to_mw(wb.time_stamp/44100.)
            stimSpikeSyncer.process_spike(wb.channel_id, clockSync.au_to_mw(wb.time_stamp/44100.))
        else:
            logging.warning("Clock not synced!! dropping spike on %i" % wb.channel_id)
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
    
    # ==============================================================================================
    # ==============================================================================================
    # ========================================= Plotting ===========================================
    # ==============================================================================================
    # ==============================================================================================
    
    global ax, fig
    fig = plt.figure(figsize=(7,7))
    ax = plt.subplot(111)
    # ax.plot(data)
    
    global window
    w, h = fig.get_size_inches() * fig.dpi
    window = glumpy.Window(int(w),int(h)) #Ft.shape[1], Ft.shape[0])
    
    global channel
    channel = 0
    def get_channel():
        global channel
        return channel
    
    def set_channel(c):
        global channel
        if (c > -1) and (c < 32):
            channel = c
        get_spikes()
    
    global stim, stimI
    stimI = -1
    # TODO setup default
    stimDict = { 'name': '0',
                    'pos_x': -25, 'pos_y': 0,
                    'size_x': 70, 'size_y': 70,
                    'rotation': 0 }
    stim = Stim(stimDict)
    
    def get_stim_i():
        global stimI
        return stimI
    
    def set_stim_i(i):
        global stimI, stimSpikeSyncer
        if (i < 0) or (stimI >= len(stimSpikeSyncer.stimList)):
            return
        stimI = i
        global stim
        stim = stimSpikeSyncer.stimList[i]
        get_spikes()
    
    def get_stim_x():
        global stim
        return stim.pos_x
    def get_stim_y():
        global stim
        return stim.pos_y
    def get_stim_size():
        global stim
        return stim.size_x
    
    def set_stim_x(x):
        global stim, stimI, stimSpikeSyncer
        newStim = copy.deepcopy(stim)
        newStim.pos_x = x
        i = stimSpikeSyncer.find_stim(newStim)
        if i != -1:
            stimI = i
            stim = stimSpikeSyncer.stimList[i]
            get_spikes()
    
    def set_stim_y(y):
        global stim, stimI, stimSpikeSyncer
        newStim = copy.deepcopy(stim)
        newStim.pos_y = y
        i = stimSpikeSyncer.find_stim(newStim)
        if i != -1:
            stimI = i
            stim = stimSpikeSyncer.stimList[i]
            get_spikes()
    
    def set_stim_size(s):
        global stim, stimI, stimSpikeSyncer
        newStim = copy.deepcopy(stim)
        newStim.size_x = s
        newStim.size_y = s
        i = stimSpikeSyncer.find_stim(newStim)
        if i != -1:
            stimI = i
            stim = stimSpikeSyncer.stimList[i]
            get_spikes()
    
    atb.init()
    global bar
    bar = atb.Bar(name="Controls", label="Controls",
                  help="Scene controls", position=(10, 10), size=(200, 320))
    # channel = ct.c_int(1)
    # stim_id = ct.c_int(1)
    # stim_x = ct.c_float(1)
    # stim_y = ct.c_float(1)
    # stim_size = ct.c_int(1)
    bar.add_var("Channel", getter=get_channel, setter=set_channel)
    bar.add_var("Stim/Id", getter=get_stim_i, setter=set_stim_i)
    bar.add_var("Stim/X", getter=get_stim_x, setter=set_stim_x)
    bar.add_var("Stim/Y", getter=get_stim_y, setter=set_stim_y)
    bar.add_var("Stim/Size", getter=get_stim_size, setter=set_stim_size)
    
    def update_figure(spikes):
        # print "Updating figure"
        global window, frame, ax, fig
        # draw in matplotlib
        ax.cla()
        ax.hist(spikes,bins=np.linspace(-0.1,0.5,25),color='k')
        ax.vlines(0,0,ax.get_ylim()[1],color='b')

        fig.canvas.draw()
        buffer = fig.canvas.buffer_rgba(0,0)
        x,y,w,h = fig.bbox.bounds
        F = np.fromstring(buffer,np.uint8).copy()
        F.shape = h,w,4

        # Replace 'transparent' color with a real transparent color
        v = np.array(np.array([1,2,3,255]),dtype=np.uint8).view(dtype=np.int32)[0]
        Ft = np.where(F.view(dtype=np.int32) == v, 0, F)

        # Create main frame 
        frame = glumpy.Image(Ft,interpolation='nearest')
        frame.update()

        glut.glutPostRedisplay()
    
    update_figure([0])
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    
    # global transLookup
    # transLookup = [(-25,-1.5), (-26.5, 0.), (-25,0.), (-23.5,0.), (-25,-1.5)]
    # def set_trans(t):
    #     global stim, transLookup
    #     stim.pos_x, stim.pos_y = transLookup[t]
    #     get_spikes()
    # 
    # global sizeLookup
    # sizeLookup = [35, 70, 140]
    # def set_size(s):
    #     global stim, sizeLookup
    #     stim.size_x = sizeLookup[s]
    #     stim.size_y = sizeLookup[s]
    #     get_spikes()
    # 
    # def set_name(i):
    #     global stim
    #     stim.name = str(i)
    #     get_spikes()
    
    # def set_channel(c):
    #     global channel
    #     channel = c
    #     get_spikes()
    
    @window.event("on_key_press")
    def on_key_press(key, modifiers):
        print "Glumpy:", key, modifiers
    
    global t
    t = 0
    
    @window.event("on_idle")
    def update_data(dt):
        global t
        t += dt
        if t > 0.03:
            global clockSync, sl, stimSpikeSyncer
            while sl.update():
                pass
            while clockSync.update():
                pass
            clockSync.match()
            if clockSync.offset is None:
                print "MW:", [e[1] for e in clockSync.mwEvents]
                print "AU:", [e[1] for e in clockSync.auEvents]
        
            global channel, stim
            stimI = stimSpikeSyncer.find_stim(stim)
            if stimI != -1:
                spikes = stimSpikeSyncer.get_stim_spikes(channel, stimI)
                if len(spikes) > 0:
                    # global livepsth
                    # livepsth.draw_spikes(spikes)
                    update_figure(spikes)
                else:
                    logging.debug("No spikes on channel %i" % channel)
            else:
                logging.warning("Unknown stimulus: %s" % str(stim))
            
            t -= 0.03

    @window.event("on_draw")
    def on_draw():
        global frame
        window.clear()
        gl.glColor4f(1,1,1,1)
        frame.blit(0,0,window.width, window.height)
        atb.TwDraw()
    
    window.push_handlers(atb.glumpy.Handlers(window))
    window.mainloop()
    
    
    # fig = plt.figure()
    # # gs = gridspec.GridSpec(1, 5, width_ratios=[1,12,1,1,1])
    # global livepsth
    # # livepsth = psth.LivePSTH(fig.add_subplot(gs[1]))
    # livepsth = psth.LivePSTH(fig.suplot(111))
    # 
    # window = glumpy.active_window()
    # @window.event
    # def on_idle(dt):
    #     global clockSync, sl, stimSpikeSyncer
    #     while sl.update():
    #         pass
    #     while clockSync.update():
    #         pass
    #     clockSync.match()
    #     if clockSync.offset is None:
    #         print "MW:", [e[1] for e in clockSync.mwEvents]
    #         print "AU:", [e[1] for e in clockSync.auEvents]
    # 
    # def get_spikes():
    #     global clockSync, sl, stimSpikeSyncer
    #     while clockSync.update():
    #         pass
    #     clockSync.match()
    #     while sl.update():
    #         pass
    #     
    #     global channel, stim
    #     stimI = stimSpikeSyncer.find_stim(stim)
    #     if stimI != -1:
    #         spikes = stimSpikeSyncer.get_stim_spikes(channel, stimI)
    #         if len(spikes) > 0:
    #             global livepsth
    #             livepsth.draw_spikes(spikes)
    #         else:
    #             logging.debug("No spikes on channel %i" % channel)
    #     else:
    #         logging.warning("Unknown stimulus: %s" % str(stim))
    # 
    # 
    # 
    # 
    # global channel
    # channel = 0
    # global stim
    # # TODO setup default
    # stimDict = { 'name': '0',
    #                 'pos_x': -25, 'pos_y': 0,
    #                 'size_x': 70, 'size_y': 70,
    #                 'rotation': 0 }
    # stim = Stim(stimDict)
    # 
    # global transLookup
    # transLookup = [(-25,-1.5), (-26.5, 0.), (-25,0.), (-23.5,0.), (-25,-1.5)]
    # def set_trans(t):
    #     global stim, transLookup
    #     stim.pos_x, stim.pos_y = transLookup[t]
    #     get_spikes()
    # 
    # global sizeLookup
    # sizeLookup = [35, 70, 140]
    # def set_size(s):
    #     global stim, sizeLookup
    #     stim.size_x = sizeLookup[s]
    #     stim.size_y = sizeLookup[s]
    #     get_spikes()
    # 
    # def set_name(i):
    #     global stim
    #     stim.name = str(i)
    #     get_spikes()
    # 
    # def set_channel(c):
    #     global channel
    #     channel = c
    #     get_spikes()
    # 
    # def get_spikes():
    #     global clockSync, sl, stimSpikeSyncer
    #     while clockSync.update():
    #         pass
    #     clockSync.match()
    #     while sl.update():
    #         pass
    #     
    #     global channel, stim
    #     stimI = stimSpikeSyncer.find_stim(stim)
    #     if stimI != -1:
    #         spikes = stimSpikeSyncer.get_stim_spikes(channel, stimI)
    #         if len(spikes) > 0:
    #             global livepsth
    #             livepsth.draw_spikes(spikes)
    #         else:
    #             logging.debug("No spikes on channel %i" % channel)
    #     else:
    #         logging.warning("Unknown stimulus: %s" % str(stim))
    # 
    # cc = psth.VerticalSelect(fig.add_subplot(gs[0]),32,title='C',updateFunc=set_channel) # channel control
    # sc = psth.VerticalSelect(fig.add_subplot(gs[2]),12,title='I',updateFunc=set_name) # stimulus control
    # tc = psth.VerticalSelect(fig.add_subplot(gs[3]),5,title='T',updateFunc=set_trans) # translation control
    # zc = psth.VerticalSelect(fig.add_subplot(gs[4]),3,title='S',updateFunc=set_size) # size control
    # 
    # cc.connect()
    # sc.connect()
    # tc.connect()
    # zc.connect()
    # 
    # def update(event):
    #     global clockSync, sl, stimSpikeSyncer
    #     while sl.update():
    #         pass
    #     while clockSync.update():
    #         pass
    #     clockSync.match()
    #     if clockSync.offset is None:
    #         print "MW:", [e[1] for e in clockSync.mwEvents]
    #         print "AU:", [e[1] for e in clockSync.auEvents]
    # 
    # fig.canvas.mpl_connect("motion_notify_event", update)
    # 
    # plt.show()
