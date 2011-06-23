#!/usr/bin/env python



import logging, time

from threading import Condition

import numpy as np

from mworks.conduit import IPCClientConduit as Conduit

from spike_listener import SpikeListener

def delta_code(code1, code0):
    deltas = [0,0,0,0] # 0 is lsb
    for i in xrange(4):
        deltas[i] = ((code1 >> i) & 1) - ((code0 >> i) & 1)
    return deltas

class MWPixelClock(object):
    def __init__(self, conduitName):
        self.conduit = Conduit(conduitName)
        self.conduit.initialize()
        self.conduit.register_local_event_code(0,'#stimDisplayUpdate')
        self.conduit.register_callback_for_name('#stimDisplayUpdate', self.receive_event)
        self.codes = []
        self.cond = Condition()
        self.maxCodes = 100
    
    def receive_event(self, event):
        for s in event.data:
            if s.has_key('bit_code'):
                self.cond.acquire()
                self.codes.append((s['bit_code'],event.time/1000000.))
                # if len(self.codes) > 2:
                #     #logging.debug('MW bit_code = %i' % s['bit_code'])
                #     #print s['bit_code']
                #     #logging.debug("MW Delta: %s" % delta_code(self.codes[-1][0], self.codes[-2][0]))
                while len(self.codes) > self.maxCodes:
                    self.codes.pop(0)
                self.cond.notifyAll()
                self.cond.release()
    
    def get_deltas(self):
        """
        Return a list of (delta_code, time_of_delta)
        """
        self.cond.acquire()
        deltas = [(delta_code(self.codes[i+1][0],self.codes[i][0]),self.codes[i+1][1]) for i in xrange(len(self.codes)-1)]
        self.cond.release()
        return deltas

class AudioPixelClock(SpikeListener):
    def __init__(self, pathFunc, downIndices, zmqContext=None):
        # pixel clock channel 4 is closest to the middle of the screen
        # channel 1 is closest to the bottom edge
        # channel 1 is connected to audio input 33
        # bottom (1/33) is least significant bit
        self.downIndices = list(downIndices)
        SpikeListener.__init__(self, pathFunc, self.downIndices, zmqContext)
        self.downs = []
        self.maxDowns = 400
        self.maxEventTime = 0.002 # maximum amount of time between 'downs' for a pixel clock event
    
    def process_spike(self, wb):
        if (wb.wave_sample[0] - wb.wave_sample[-1]) > 0.01: # only record for downward waveforms
            self.downs.append((self.downIndices.index(wb.channel_id),wb.time_stamp/44100.))
            while len(self.downs) > self.maxDowns:
                self.downs.pop(0)
    
    def get_deltas(self):
        """
        Return a list of (delta_code, time_of_delta)
        All deltas will ONLY contain -1 or 0 values
        """
        if len(self.downs) == 0:
            return []
        deltas = []
        delta = [0, 0, 0, 0]
        firstTime = self.downs[0][1]
        for down in self.downs:
            if abs(down[1] - firstTime) < self.maxEventTime:
                if delta[down[0]] == -1:
                    logging.warning("setting two downs: %s at %d" % (str(down), firstTime))
                delta[down[0]] = -1
            else:
                deltas.append((delta,firstTime))
                # get ready for next event
                delta = [0,0,0,0]
                delta[down[0]] = -1
                firstTime = down[1]
        return deltas

# class PixelClock(SpikeListener):
#     def __init__(self, pathFunc, upIndices, downIndices, zmqContext=None):
#         self.upIndices = list(upIndices) # to deal with possible xrange(N) arguments
#         self.downIndices = list(downIndices)
#         SpikeListener.__init__(self, pathFunc, self.upIndices + self.downIndices, zmqContext)
#         self.states = [0 for i in xrange(len(self.upIndices))]
#         self.codes = []
#         self.maxCodes = 20
#     
#     def process_spike(self, wb):
#         try:
#             if wb.channel_id in self.upIndices:
#                 index = self.upIndices.index(wb.channel_id)
#                 delta = +1
#             else:
#                 index = self.downIndices.index(wb.channel_id)
#                 delta = -1
#         except:
#             logging.warning("Pixel clock failed to parse spike waveform: %i" % wb.channel_id)
#             return
#         self.states[index] += delta
#         self.eventTimes[index] = wb.time_stamp
#         if self.states[index] < 0:
#             logging.debug("Pixel clock channel %i detected two downs" % index)
#             self.states[index] = 0
#         if self.states[index] > 1:
#             logging.debug("Pixel clock channel %i detected two ups" % index)
#             self.states[index] = 1
#         self.calculate_code()
#     
#     def get_code_time_stamp(self):
#         """
#         This should be more complex taking into account the position of the various sensors etc...
#         """
#         return max(self.eventTimes)
#     
#     def calculate_code(self):
#         code = 0
#         for s in self.states:
#             code = (code << 1) + s
#         t = self.get_time()
#         self.codes.append((code,t))
#         while len(self.codes) > self.maxCodes:
#             self.pop(0)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    conduitName = 'server_event_conduit'
    mwPC = MWPixelClock(conduitName)
    
    pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    aPC = AudioPixelClock(pathFunc, range(33,37))
    
    def delta_to_num(delta):
        num = 0
        # 0 is lsb
        for i in xrange(4):
            if delta[i] == -1:
                num += (1 << i)
        return num
    
    def find_match(a,k):
        minMatch = -1.
        matchVal = np.inf
        for o in xrange(len(a)-len(k)):
            m = sum(abs(a[o:o+len(k)] - k))/float(len(k))
            if m <= matchVal:
                minMatch = o
                matchVal = m
                #logging.debug('Match: %i %.2f' % (o, m))
        return minMatch, matchVal, len(k)
    
    def compare_matches(m1, m2):
        if (m2[2] >= m1[2]) and (m2[1] <= m1[1]): # takes care of = and m2>m1
            return m2
        if (m1[2] >= m2[2]) and (m1[1] < m2[1]): # takes care of m1>m2
            return m1
        # somewhat ambiguous as length and val comparisons do not agree
        if ((m2[1] * m2[2]) < (m1[1] * m1[2])):
            return m2
        else:
            return m1
    
    aNums = []
    mwNums = []
    prevMatch = (0, np.inf, 0, 0)
    
    while 1:
        mwDeltas = mwPC.get_deltas()
        if len(mwDeltas):
            mwNums = np.array([delta_to_num(d[0]) for d in mwDeltas])
        # if len(mwDeltas):
        #     mwDelta = mwDeltas[-1][0]
        #     if mwDelta != oldMWDelta:
        #         print "MW:",
        #         for mw in mwDelta:
        #             print "%+i" % mw,
        #         print
        #         oldMWDelta = mwDelta
        # if len(mwDeltas):
        #     logging.debug("Most recent mw delta: %s" % str(mwDeltas[-1]))
        #logging.debug("Deltas %s" % d)
        
        
        aPC.update()
        aDeltas = aPC.get_deltas()
        if len(aDeltas):
            aNums = np.array([delta_to_num(d[0]) for d in aDeltas])
        #     aDelta = aDeltas[-1][0]
        #     if aDelta != oldADelta:
        #         print "\t\tAU:",
        #         for a in aDelta:
        #             print "%+i" % a,
        #         print
        #         oldADelta = aDelta
        # if len(aDeltas):
        #     logging.debug("Most recent audio delta: %s" % str(aDeltas[-1]))
        kSize = 25
        if len(aNums) > kSize and len(mwNums) > kSize:
            mwToA = find_match(aNums, mwNums[-kSize:])
            mwT = mwDeltas[-1][1]
            aT = aDeltas[mwToA[0]+kSize-1][1]
            mwToAOffset = aT - mwT
            mwToA += (mwToAOffset,)
            
            aToMW = find_match(mwNums, aNums[-kSize:])
            mwT = mwDeltas[aToMW[0]+kSize-1][1]
            aT = aDeltas[-1][1]
            aToMWOffset = aT - mwT
            aToMW += (aToMWOffset,)
            
            match = compare_matches(mwToA, aToMW)
            offset = match[3]
            
            if (match[0] != 1):
                bestMatch = compare_matches(match, prevMatch)
                if bestMatch != prevMatch:
                    logging.debug("Match: %s" % str(match))
                    prevMatch = match
            
        # if len(aNums) and len(mwNums):
        #     if len(aNums) < len(mwNums):
        #         match = find_match(mwNums, aNums)
        #         if match[0] != -1:
        #             d1 = mwDeltas[match[0]+len(aNums)-1]
        #             d2 = aDeltas[-1]
        #             # logging.debug("Offset for delta codes: %s, %s" % (str(d1), str(d2)))
        #             offset = d1[1] - d2[1]
        #     else:
        #         match = find_match(aNums, mwNums)
        #         if match[0] != -1:
        #             d1 = mwDeltas[-1]
        #             d2 = aDeltas[match[0]+len(mwNums)-1]
        #             # logging.debug("Offset for delta codes: %s, %s" % (str(d1), str(d2)))
        #             offset = d1[1] - d2[1]
            # if (match[0] != -1): # match was found
            #     if ((match[1] < matchVal) and (match[2] >= matchLen)) or \
            #         ((match[2] > matchLen) and (match[1] <= matchVal)): # it is a better match
            #         if (match[2] < 10):
            #             logging.debug("Match %s was too short" % str(match))
            #             continue
            #         logging.debug("%.2f %.2f, %i %i" % (match[1], matchVal, match[2], matchLen))
            #         matchIndex = match[0]
            #         matchVal = match[1]
            #         matchLen = match[2]
            #         if offset != oldOffset:
            #             logging.debug("Match: I:%i, V:%.2f, L:%i Offset: %f" % (match[0], match[1], match[2], offset))
            #             oldOffset = offset
            # if (match[0] != -1) and (offset != oldOffset):
            #     #logging.debug("Offset for delta codes: %s, %s" % (str(d1), str(d2)))
            #     logging.debug("Match: I:%i, V:%.2f, L:%i Offset: %f" % (match[0], match[1], match[2], offset))
            #     oldOffset = offset
        
        time.sleep(0.001)