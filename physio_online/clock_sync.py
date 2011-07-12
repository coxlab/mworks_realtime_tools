#!/usr/bin/env python

import copy, logging, time

from threading import Condition

import numpy as np
from scipy.stats import linregress

from mworks.conduit import IPCClientConduit as Conduit

class ClockSync(object):
    def __init__(self):
        self.mwEvents = []
        self.cond = Condition()
        
        self.offsets = []
        self.offset = None
        
        self.maxOffsets = 100
        self.outlierThreshold = 10000 # in microsecondss
        self.slopeThreshold = 0.0001
    
    def process_mw_event(self, event):
        self.cond.acquire()
        self.offsets.append((event.time, event.value))
        while len(self.offsets) > self.maxOffsets:
            self.offsets.pop(0)
        self.recompute_offset()
        self.cond.notifyAll()
        self.cond.release()
    
    def recompute_offset(self):
        offsetsArray = np.array(self.offsets)
        offsets = offsetsArray[:,1]
        times = offsetsArray[:,0]
        
        # find outliers
        meanOffset = np.mean(offsets)
        goodIndexes = np.where(abs(offsets-meanOffset) < self.outlierThreshold)
        
        # remove outliers
        meanOffsets = meanOffsets[goodIndexes]
        times = times[goodIndexes]
        
        # calculate most recent offset using slope
        s, i, _, _, _ = linregress(times,meanOffsets)
        if (s > 0) and (s < self.slopeThreshold):
            self.offset = times[-1] * s + i
    
    def mw_to_au(self, mwTime):
        return mwTime - self.offset
    
    def au_to_mw(self, auTime):
        return auTime + self.offset

# ===============================

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    cs = ClockSync(pathFunc, range(4))
    
    conduitName = 'server_event_conduit'
    
    conduit = Conduit(conduitName)
    conduit.initialize()
    conduit.register_local_event_code(0,'#pixelClockOffset')
    conduit.register_callback_for_name('#pixelClockOffset', cs.process_mw_event)
    
    offset = 0
    while 1:
        while cs.update():
            pass
        cs.match()
        mwC = [e[1] for e in cs.mwEvents]
        auC = [e[1] for e in cs.auEvents]
        if len(mwC):
            if np.any(np.array(mwC[1:]) == np.array(mwC[:-1])):
                print "Repeat found!"

        if not (cs.offset is None):
            if cs.offset != offset:
                offset = cs.offset
                print offset, cs.matchLength, cs.err
        else:
            print "mw =", mwC
            print "au =", auC
            print "aut=", ["%.3f" % e[0] for e in cs.auEvents]
        
        time.sleep(0.03)