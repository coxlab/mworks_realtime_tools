#!/myPython/bin/python
############################!/usr/bin/env python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import sys, time

from threading import Condition

from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *

#from spike_listener import SpikeListener
from glraster import GLRaster

# import mworks conduit
sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
from mworks.conduit import IPCClientConduit

eventNames = ['#stimDisplayUpdate','#annouceTrial','x']

if __name__ == '__main__':
    # setup opengl
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(1024,128)
    glutCreateWindow("Spike Raster")
    glClearColor(0., 0., 0., 1.)
    
    # setup raster view
    NRows = len(eventNames)#32
    global startTime
    startTime = time.time()
    global raster
    raster = GLRaster(NRows,startTime)
    global rasterCond
    rasterCond = Condition()
    
    # setup mworks conduit
    def receive_event(event):
        global raster, rasterCond, startTime
        #print event.time, event.data, event.code
        rasterCond.acquire()
        raster.add_event(event.time/1000000., event.code)
        if raster.cursorX == startTime:
            raster.reset(raster.newEvents[0][0])
        rasterCond.notifyAll()
        rasterCond.release()
    mwconduit = IPCClientConduit('python_bridge_plugin_conduit')
    mwconduit.initialize()
    
    for (i,eventName) in enumerate(eventNames):
        print "registering %s" % eventName
        mwconduit.register_callback_for_name(eventName, receive_event)
        # register local code?
        mwconduit.register_local_event_code(i,eventName)
    
    def draw():
        global raster, rasterCond
        rasterCond.acquire()
        raster.draw() # passing in new time
        rasterCond.release()
        glutSwapBuffers()
    glutDisplayFunc(draw)
    
    global prevT
    prevT = time.time()
    
    def idle():
        global prevT
        
        dt = time.time() - prevT
        
        if dt > 0.03:
            prevT = time.time()
            glutPostRedisplay()
    
    glutIdleFunc(idle)
    
    glClear(GL_COLOR_BUFFER_BIT)
    glutMainLoop()