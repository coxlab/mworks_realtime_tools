#!/usr/bin/env python

#from pylab import *

import zmq

from spike_wave_pb2 import SpikeWaveBuffer

class SpikeListener:
    def __init__(self, pathFunc, channelIndices, zmqContext=None):
        if zmqContext == None:
            zmqContext = zmq.Context()
        
        self.socket = zmqContext.socket(zmq.SUB)
        for i in channelIndices:
            self.socket.connect(pathFunc(i))
        self.socket.setsockopt(zmq.SUBSCRIBE,"")
        self._wb = SpikeWaveBuffer()
        
        self.callbacks = []
    
    def update(self):
        try:
            packet = self.socket.recv(zmq.NOBLOCK)
            self._wb.ParseFromString(packet)
            self.process_spike(self._wb)
            [c(self._wb) for c in self.callbacks]
            return 1
        except zmq.ZMQError:
            return 0
    
    def process_spike(self, wb):
        pass
    
    def register_callback(self, func):
        self.callbacks.append(func)


if __name__ == '__main__':
    #sl = SpikeListener("ipc:///tmp/spike_channels/%i", xrange(32))
    #define HOST_ADDRESS    "tcp://127.0.0.1"
    #define SPIKE_BASE_PORT     8000
    pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    sl = SpikeListener(pathFunc, xrange(32))
    def process_spike(wb): # overload process_spike
        print wb.time_stamp, wb.channel_id
    sl.register_callback(process_spike)
    #sl.process_spike = process_spike
    
    while True:
        sl.update()