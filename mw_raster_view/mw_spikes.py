#!/myPython/bin/python
############################!/usr/bin/env python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import sys, time

from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *

from spike_listener import SpikeListener
from glraster import GLRaster

# import mworks conduit
sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
from mworks.conduit import IPCClientConduit

if __name__ == '__main__':
    # setup opengl
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(1024,600)
    glutCreateWindow("Spike Raster")
    glClearColor(0., 0., 0., 1.)
    
    mwEventNames = ['#stimDisplayUpdate','#annouceTrial','success','failure','ignore','correctIgnore']
    #mwEventNames = ['#stimDisplayUpdate','#annouceTrial']
    global mwEventColors
    mwEventColors = [(0.,1.,0.,1.),(0.,1.,0.,1.),(0.,0.,1.,1.),(1.,0.,0.,1.),(.7,.7,.7,1.),(0.,0.,1.,1.)]
    
    # channel mapping (tdt to position on probe)
    global channelMapping
    channelMapping = [3, 9, 7, 13, 5, 17, 1, 21, 14, 2, 8, 6, 18, 4, 12, 10, 23, 15, 31, 27, 19, 11, 29, 25, 30, 26, 20, 16, 32, 28, 24, 22]    
    
    # setup raster view
    global NChannels
    NChannels = 32
    NRows = NChannels + len(mwEventNames)
    global startTime
    startTime = time.time()
    global raster
    raster = GLRaster(NRows,startTime,['%i' % i for i in channelMapping] + [s[:2] for s in mwEventNames])
    # global rasterCond
    # rasterCond = Condition()
    global mwTimeOffset
    mwTimeOffset = None
    
    # setup mworks conduit
    # setup mworks conduit
    def receive_event(event):
        global mwEventColors, mwTimeOffset, raster #, rasterCond, startTime
        #print event.time, event.data, event.code
        # rasterCond.acquire()
        if mwTimeOffset == None:
            mwTimeOffset = time.time() - event.time/1000000.
        # print "MW:", event.code, event.time/1000000. + mwTimeOffset
        raster.add_event(event.time/1000000. + mwTimeOffset, event.code, mwEventColors[event.code-NChannels])
        # 
        # if raster.cursorX == startTime:
        #     raster.reset(raster.newEvents[0][0])
        # rasterCond.notifyAll()
        # rasterCond.release()
    mwconduit = IPCClientConduit('python_bridge_plugin_conduit')
    mwconduit.initialize()
    
    for (i,eventName) in enumerate(mwEventNames):
        print "registering %s" % eventName
        mwconduit.register_callback_for_name(eventName, receive_event)
        # register local code?
        mwconduit.register_local_event_code(i+NChannels,eventName)
    
    # setup spike listener
    global sl
    sl = SpikeListener("ipc:///tmp/spike_channels/", xrange(32))
    global audioTimeOffset
    audioTimeOffset = None
    def process_spike(wb): # overload process_spike
        global audioTimeOffset, channelMapping, raster
        if audioTimeOffset == None:
            audioTimeOffset = time.time() - wb.time_stamp/44100.
        # print "SE:", wb.channel_id, wb.time_stamp/44100. + audioTimeOffset
        raster.add_event(wb.time_stamp/44100. + audioTimeOffset, channelMapping[wb.channel_id]-1)
    sl.process_spike = process_spike
    
    def draw():
        global raster
        raster.draw(time.time()) # passing in new time
        glutSwapBuffers()
    glutDisplayFunc(draw)
    
    global prevT
    prevT = time.time()
    
    def idle():
        global prevT, sl
        sl.update()
        
        dt = time.time() - prevT
        
        if dt > 0.03:
            prevT = time.time()
            glutPostRedisplay()
    
    glutIdleFunc(idle)
    
    # raster.reset(raster.newEvents[0][0])
    
    glClear(GL_COLOR_BUFFER_BIT)
    glutMainLoop()