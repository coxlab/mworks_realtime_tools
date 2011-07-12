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
    def __init__(self, pathFunc, channelIndices, minMatch=10, maxErr=1, zmqContext=None):
        self.mwEvents = []
        # self.mwCodes = []
        # self.mwTimes = []
        self.cond = Condition()
        
        if zmqContext == None:
            zmqContext = zmq.Context()
        
        self.socket = zmqContext.socket(zmq.SUB)
        for i in channelIndices:
            self.socket.connect(pathFunc(i))
        self.socket.setsockopt(zmq.SUBSCRIBE,"")
        self._mb = PixelClockInfoBuffer()
        
        self.auEvents = []
        self.rawAUEvents = []
        # self.auCodes = []
        # self.auTimes = []
        self.state = [0,0,0,0]
        
        # screen 53 cm high ~ pixel clock 7 cm high : assume a 2ms screen refresh
        # so 53 / 2 cm/ms
        # pc channels at 
        # update is bottom -> up so add the most to channel 1
        self.auChannelOffsets = [86, 84, 81, 79] # [2,5,7,9]
        
        self.minEventTime = 0.05 #* 44100
        self.lastEventTime = 0
        self.lastCode = 0
        
        self.offset = None
        self.err = None
        self.matchLength = None
        
        self.minMatch = minMatch
        self.maxErr = maxErr
        self.maxCodes = (minMatch + maxErr) * 2
        #self.maxRawCodes = self.maxCodes * 4
    
    def process_mw_event(self, event):
        for s in event.data:
            if s is None:
                continue
            if s.has_key('bit_code'):
                self.cond.acquire()
                self.mwEvents.append((event.time/1000000., s['bit_code']))
                # self.mwCodes.append(s['bit_code'])
                # self.mwTimes.append(event.time/1000000.)
                while len(self.mwEvents) > self.maxCodes:
                    self.mwEvents.pop(0)
                # while len(self.mwCodes) > self.maxCodes:
                #     self.mwCodes.pop(0)
                # while len(self.mwTimes) > self.maxCodes:
                #     self.mwTimes.pop(0)
                self.cond.notifyAll()
                self.cond.release()
    
    def update(self):
        try:
            packet = self.socket.recv(zmq.NOBLOCK)
            self._mb.ParseFromString(packet)
            self.process_msg(self._mb)
            return 1
        except zmq.ZMQError as e:
            return 0
    
    def offset_au_time(self, time, channel_id):
        """
        This function is here to offset of a given event based on it's position on the screen.
        The resulting time should correspond to the END of the screen refresh
        The resulting time should be in units SAMPLES (e.g. 44100 per second)
        """
        
        return time + self.auChannelOffsets[channel_id]
    
    def process_msg(self, mb):
        time_stamp = self.offset_au_time(mb.time_stamp, mb.channel_id)
        self.state[mb.channel_id] = mb.direction
        self.rawAUEvents.append((self.offset_au_time(mb.time_stamp, mb.channel_id) / 44100., state_to_code(self.state)))
        # if abs(time_stamp - self.lastEventTime) > self.minEventTime:
        #     self.auEvents.append((self.lastEventTime / 44100.,state_to_code(self.state)))
        #     # self.auCodes.append(state_to_code(self.state))
        #     # self.auTimes.append(self.lastEventTime / 44100)
        #     while len(self.auEvents) > self.maxCodes:
        #         self.auEvents.pop(0)
        #     # while len(self.auCodes) > self.maxCodes:
        #     #     self.auCodes.pop(0)
        #     # while len(self.auTimes) > self.maxCodes:
        #     #     self.auTimes.pop(0)
        #     self.lastEventTime = self.offset_au_time(time_stamp, mb.channel_id)
        # self.state[mb.channel_id] = mb.direction
    
    def process_raw_au_events(self):
        # for rau in self.rawAUEvents:
        #     print "%i @ %.3f" % (rau[1], rau[0])
        # print
        # return
        if len(self.rawAUEvents) == 0:
            return
        #self.rawAUEvents = sorted(self.rawAUEvents, lambda x, y: cmp(x[0],y[0]))
        lastI = -1
        for (i,au) in enumerate(self.rawAUEvents):
            if abs(au[0] - self.lastEventTime) > self.minEventTime:
                self.auEvents.append((self.lastEventTime,self.lastCode))#au[1]))
                while len(self.auEvents) > self.maxCodes:
                    self.auEvents.pop(0)
                self.lastEventTime = au[0]#self.offset_au_time(time_stamp, mb.channel_id)
                lastI = i
            self.lastCode = au[1]
            self.lastEventTime = au[0]
        if lastI != -1:
            # remove processed events
            self.lastCode = self.rawAUEvents[lastI][1]
            self.lastEventTime = self.rawAUEvents[lastI][0]
            self.rawAUEvents = self.rawAUEvents[lastI+1:]
        # print len(self.rawAUEvents)
    
    def match(self):
        self.cond.acquire()
        # sort codes
        # self.mwEvents = sorted(self.mwEvents, lambda x, y: cmp(x[0],y[0]))
        # self.auEvents = sorted(self.auEvents, lambda x, y: cmp(x[0],y[0]))
        self.process_raw_au_events()
        mwC = [mw[1] for mw in self.mwEvents]
        auC = [au[1] for au in self.auEvents]
        ml, err, lastMatch = match_codes(mwC, auC, self.minMatch, self.maxErr)
        # ml, err, lastMatch, matches = match_codes(self.mwCodes, self.auCodes, self.minMatch, self.maxErr)
        if err <= self.maxErr:
            offset = self.mwEvents[lastMatch[0]][0] -  self.auEvents[lastMatch[1]][0]
            # if offset != self.offset:
                # print self.mwEvents[lastMatch[0]][0], self.mwEvents[lastMatch[0]][1], self.auEvents[lastMatch[1]][0], self.auEvents[lastMatch[1]][1]
            self.offset = self.mwEvents[lastMatch[0]][0] -  self.auEvents[lastMatch[1]][0]
            #logging.debug("ClockSync.offset = %.4f" % self.offset)
            # self.offset = self.mwTimes[lastMatch[0]] - self.auTimes[lastMatch[1]]
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
    while (mwI < len(mw)) and (auI < len(au)):
        if mw[mwI] == au[auI]:
            matchLen += 1
            lastMatch = (mwI, auI)
            mwI += 1
            auI += 1
            # if (matchLen > minMatch):
            #     return (matchLen, err, lastMatch)
        else:
            auI += 1
            err += 1
            if (err > maxErr):
                return (matchLen, err, lastMatch)
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
    return (matchLen, err, lastMatch)

def match_codes(mw, au, minMatch = 10, maxErr = 1):
    # matchAttempts = []
    for mwI in xrange(len(mw)):
        #if (mw[mwI] in au):
        try:
            startI = au.index(mw[mwI])
            matchLen, err, lastMatch = test_match(mw[startI:], au, minMatch, maxErr)
            # matchLen, err, lastMatch, matches = test_match(mw, au[startI:], minMatch, maxErr)
            # matchAttempts.append((matchLen, err, lastMatch))
            # if lastMatch != (-1,-1):
            #     print matchLen, err, lastMatch
            if (matchLen > minMatch) and (err <= maxErr):
                # correct lastMatch
                lastMatch = (lastMatch[0]+startI, lastMatch[1])
                return (matchLen, err, lastMatch)
        except ValueError:
            continue
    return (0, maxErr * 2, (-1,-1))

# ===============================

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    #pathFunc = lambda i : "ipc:///tmp/pixel_clock/%i" % i
    pathFunc = lambda i : "tcp://localhost:%i" % (11000 + i)
    cs = ClockSync(pathFunc, range(4))
    
    conduitName = 'server_event_conduit'
    
    conduit = Conduit(conduitName)
    conduit.initialize()
    conduit.register_local_event_code(0,'#stimDisplayUpdate')
    conduit.register_callback_for_name('#stimDisplayUpdate', cs.process_mw_event)
    
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