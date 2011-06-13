#!/usr/bin/env python

from pylab import *
import sys, time

try:
    sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
    import mworks.conduit
    # mworks conduit: "cnc"
    ORIGIN_X = 0
    ORIGIN_Y = 1
    ORIGIN_Z = 2
    SLOPE_X = 3
    SLOPE_Y = 4
    SLOPE_Z = 5
    DEPTH = 6
    PATH_INFO = 7
    mwConduitAvailable = True
    print "Found mwconduit module"
except Exception, e:
    print "Unable to load MW Conduit: %s", e
    sys.exit(1)

self.mwConduit = mworks.conduit.IPCServerConduit("cnc")
self.mwConduit.initialize()
self.mwConduit.send_data(PATH_INFO, (-1000, -1000, -1000, -1000, -1000, -1000, -1000))
self.mwConduit.send_data(PATH_INFO, (p1InS[0], p1InS[2], p1InS[3], mInS[0], mInS[1], mInS[2], self.ocW))
self.mwConduit.finalize()

# # ------------- animation ---------------
# ion()
# 
# tstart = time.time()               # for profiling
# x = arange(0,2*pi,0.01)            # x-array
# line, = plot(x,sin(x))
# for i in arange(1,200):
#     line.set_ydata(sin(x+i/10.0))  # update the data
#     draw()                         # redraw the canvas
# 
# print 'FPS:' , 200/(time.time()-tstart)