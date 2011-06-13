#!/usr/bin/env python

import os, random, sys, time
from numpy.random import poisson

import zmq

sys.path.append('../')
from physio_online.spike_wave_pb2 import SpikeWaveBuffer

class Spiker:
    def __init__(self, hz):
        self.hz = hz
    def update(self,dt):
        """
        dt : seconds
        returns the number of spikes within the update interval
        """
        if dt > 0:
            return poisson(self.hz*dt)
        else:
            return 0

global zmqContext
zmqContext = None

class SocketSpiker (Spiker):
    def __init__(self, hz, ipcPath, id):
        Spiker.__init__(self, hz)
        global zmqContext
        if zmqContext == None:
            zmqContext = zmq.Context()
        self.id = id
        self.socket = zmqContext.socket(zmq.PUB)
        self.socket.bind(ipcPath)
        
        # make default waveform
        st = 44 # spike time
        b = 0.9 # build-up
        d = 0.1 # decay
        I = 0.
        a = 0.
        self.default_waveform = []
        for i in xrange(88):
            if i == st:
                I = 1.0
            elif i > st:
                I -= d
            a += I * b
            self.default_waveform.append(max(a,0.))
    
    def make_spike_waveform(self):
        return [random.random() + self.default_waveform[i] for i in xrange(len(self.default_waveform))]
    
    def update(self, dt):
        nSpikes = Spiker.update(self, dt)
        if nSpikes:
            t = time.time() * 44100 # convert time to microseconds
            for i in xrange(nSpikes):
                wb = SpikeWaveBuffer()
                wb.channel_id = self.id
                wb.time_stamp = int(t)
                
                for v in self.default_waveform:
                    wb.wave_sample.append(v)
                
                self.socket.send(wb.SerializeToString())
        return nSpikes

ipcPath = "ipc:///tmp/spike_channels/"
NChannels = 32
Hz = 0.1

if not os.path.exists('/tmp/spike_channels/'):
    os.makedirs('/tmp/spike_channels/')

spikers = []
for i in xrange(NChannels):
    spikers.append(SocketSpiker(Hz,'%s/%i' % (ipcPath,i),i))

prevTime = time.time()
while True:
    currTime = time.time()
    dt = currTime - prevTime
    [spiker.update(dt) for spiker in spikers]
    prevTime = currTime
    time.sleep(0.00001)
