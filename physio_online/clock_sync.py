#!/usr/bin/env python

import copy, logging, time

from threading import Condition

import numpy as np
import zmq

from mworks.conduit import IPCClientConduit as Conduit

from pixel_clock_info_pb2 import PixelClockInfoBuffer

def state_to_code(state):
    """
    state[0] = lsb, state[-1] = msb
    """
    code = 0
    for i in xrange(len(state)):
        code += (state[i] << i)
    return code

class ClockSync(object):
    def __init__(self, conduitName, pathFunc, channelIndices, minMatch=10, maxErr=1, zmqContext=None):
        self.conduit = Conduit(conduitName)
        self.conduit.initialize()
        self.conduit.register_local_event_code(0,'#stimDisplayUpdate')
        self.conduit.register_callback_for_name('#stimDisplayUpdate', self.receive_mw_event)
        self.mwCodes = []
        self.mwTimes = []
        self.cond = Condition()
        
        if zmqContext == None:
            zmqContext = zmq.Context()
        
        self.socket = zmqContext.socket(zmq.SUB)
        for i in channelIndices:
            self.socket.connect(pathFunc(i))
        self.socket.setsockopt(zmq.SUBSCRIBE,"")
        self._mb = PixelClockInfoBuffer()
        
        self.auCodes = []
        self.auTimes = []
        self.state = [0,0,0,0]
        
        # screen 53 cm high ~ pixel clock 7 cm high : assume a 2ms screen refresh
        # so 53 / 2 cm/ms
        # pc channels at 
        self.auChannelOffsets = [86, 84, 81, 79] # [2,5,7,9]
        
        self.minEventTime = 0.01 * 44100
        self.lastEventTime = 0
        
        self.offset = None
        self.err = None
        self.matchLength = None
        
        self.minMatch = minMatch
        self.maxErr = maxErr
        self.maxCodes = (minMatch + maxErr) * 2
    
    def receive_mw_event(self, event):
        for s in event.data:
            if s is None:
                continue
            if s.has_key('bit_code'):
                self.cond.acquire()
                self.mwCodes.append(s['bit_code'])
                self.mwTimes.append(event.time/1000000.)
                while len(self.mwCodes) > self.maxCodes:
                    self.mwCodes.pop(0)
                while len(self.mwTimes) > self.maxCodes:
                    self.mwTimes.pop(0)
                self.cond.notifyAll()
                self.cond.release()
    
    def update(self):
        try:
            packet = self.socket.recv(zmq.NOBLOCK)
            self._mb.ParseFromString(packet)
            self.process_msg(self._mb)
        except Exception as e:
            return
    
    def offset_au_time(self, time, channel_id):
        """
        This function is here to offset of a given event based on it's position on the screen.
        The resulting time should correspond to the END of the screen refresh
        The resulting time should be in units SAMPLES (e.g. 44100 per second)
        """
        
        return time + self.auChannelOffsets[channel_id]
    
    def process_msg(self, mb):
        time_stamp = self.offset_au_time(mb.time_stamp, mb.channel_id)
        if abs(time_stamp - self.lastEventTime) > self.minEventTime:
            self.auCodes.append(state_to_code(self.state))
            self.auTimes.append(self.lastEventTime / 44100)
            while len(self.auCodes) > self.maxCodes:
                self.auCodes.pop(0)
            while len(self.auTimes) > self.maxCodes:
                self.auTimes.pop(0)
            self.lastEventTime = self.offset_au_time(mb.time_stamp, mb.channel_id)
        self.state[mb.channel_id] = mb.direction
    
    def set_offset(self, matches):
        pass
    
    def match(self):
        self.cond.acquire()
        ml, err, lastMatch, matches = match_codes(self.mwCodes, self.auCodes, self.minMatch, self.maxErr)
        if err <= self.maxErr:
            self.offset = self.mwTimes[lastMatch[0]] - self.auTimes[lastMatch[1]]
            self.err = err
            self.matchLength = ml
        self.cond.release()
    
    def mw_to_au(self, mwTime):
        return mwTime - self.offset
    
    def au_to_mw(self, auTime):
        return auTime + self.offset

# ======= code matching =========

def test_match(mw, au, minMatch, maxErr):
    mwI = 0
    try:
        auI = au.index(mw[mwI])
    except:
        auI = 0
    err = 0
    matchLen = 0
    lastMatch = (-1,-1)
    matches = []
    while (mwI < len(mw)) and (auI < len(au)):
        if mw[mwI] == au[auI]:
            matchLen += 1
            lastMatch = (mwI, auI)
            matches.append((mwI, auI))
            mwI += 1
            auI += 1
            # if (matchLen > minMatch):
            #     return (matchLen, err, lastMatch)
        else:
            auI += 1
            err += 1
            if (err > maxErr):
                return (matchLen, err, lastMatch, matches)
            # if (mwI < (len(mw) - 1)):
            #     if (auI < (len(au) - 1)):
            #         # both auI and mwI can be increased
            #         if (mw[mwI+1] == au[auI]):
            #             mwI += 1
            #             err += 1
            #         elif (mw[mwI] == au[auI+1]):
            #             auI += 1
            #             err += 1
            #         else:
            #             auI += 1
            #             err += 1
            #     else:
            #         mwI += 1
            #         err += 1
            # elif (auI < (len(au) - 1)):
            #     auI += 1
            #     err += 1
            # else:
            #     break
    return (matchLen, err, lastMatch, matches)

def match_codes(mw, au, minMatch = 10, maxErr = 1):
    # matchAttempts = []
    for mwI in xrange(len(mw)):
        #if (mw[mwI] in au):
        try:
            startI = au.index(mw[mwI])
            matchLen, err, lastMatch, matches = test_match(mw[startI:], au, minMatch, maxErr)
            # matchLen, err, lastMatch, matches = test_match(mw, au[startI:], minMatch, maxErr)
            # matchAttempts.append((matchLen, err, lastMatch))
            # if lastMatch != (-1,-1):
            #     print matchLen, err, lastMatch
            if (matchLen > minMatch) and (err <= maxErr):
                # correct lastMatch
                lastMatch = (lastMatch[0]+startI, lastMatch[1])
                return (matchLen, err, lastMatch, matches)
        except ValueError:
            continue
    return (0, maxErr * 2, (-1,-1), [])

# ===============================

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    conduitName = 'server_event_conduit'
    pathFunc = lambda i : "ipc:///tmp/pixel_clock/%i" % i
    cs = ClockSync(conduitName, pathFunc, range(4))
    offset = 0
    while 1:
        cs.update()
        cs.match()
        # print "mw =", cs.mwCodes
        # if len(cs.mwCodes):
        #     if np.any(np.array(cs.mwCodes[1:]) == np.array(cs.mwCodes[:-1])):
        #         print "Repeat found!"
        # print "au =", cs.auCodes
        if not (cs.offset is None):
            if cs.offset != offset:
                offset = cs.offset
                print offset, cs.matchLength, cs.err
        
        time.sleep(0.001)
    
    # conduitName = 'server_event_conduit'
    #     mwPC = MWPixelClock(conduitName)
    #     
    #     #pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    #     pathFunc = lambda i : "ipc:///tmp/pixel_clock/%i" % i
    #     auPC = AudioPixelClock(pathFunc, range(4))
    #     
    #     minLength = 10
    #     
    #     while 1:
    #         mwCodes = mwPC.get_codes()
    #         auPC.update()
    #         auCodes = auPC.codes
    #         
    #         if (len(mwCodes) > minLength) and (len(auCodes) > minLength):
    #             match = find_matches(auCodes, mwCodes)
    #             if len(match):
    #                 print match
    #         
    #         time.sleep(0.001)