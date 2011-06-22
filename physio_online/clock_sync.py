#!/usr/bin/env python

import logging, time

from threading import Condition

from mworks.conduit import IPCClientConduit as Conduit

from spike_listener import SpikeListener

def delta_code(code1, code0):
    deltas = []
    for i in xrange(4):
        mask = (1 << i)
        deltas[i] = (code1 & mask) - (code0 & mask)
    return deltas

class MWPixelClock(object):
    def __init__(self, conduitName):
        self.conduit = Conduit(conduitName)
        self.conduit.initialize()
        self.conduit.register_local_event_code(0,'#stimDisplayUpdate')
        self.conduit.register_callback_for_name('#stimDisplayUpdate', self.receive_event())
        self.codes = []
        self.cond = Condition()
        self.maxCodes = 20
    
    def receive_event(self, event):
        for s in event.value:
            if s.has_key('bit_code'):
                self.cond.acquire()
                self.codes.append((s['bit_code'],event.time/1000000.))
                logging.debug('MW bit_code = %i' % bit_code)
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
    def __init__(self, pathFunc, upIndices, zmqContext=None):
        self.upIndices = list(upIndices)
        SpikeListener.__init__(self, pathFunc, self.upIndices, zmqContext)
        self.ups = []
        self.maxUps = 40
    
    def process_spike(self, wb):
        self.ups.append((self.upIndices.index(wb.channel_id),wb.time_stamp))
        while len(self.ups) > self.maxUps:
            self.ups.pop(0)

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
    
    while 1:
        d = mwPC.get_deltas()
        logging.debug("Deltas %s" % d)
        
        time.sleep(0.1)