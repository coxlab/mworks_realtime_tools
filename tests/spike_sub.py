#!/usr/bin/env python

import sys

#from pylab import *

sys.path.append('../')
from physio_online.spike_listener import SpikeListener

if __name__ == '__main__':
    pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    sl = SpikeListener(pathFunc, xrange(32))
    def process_spike(wb): # overload process_spike
        print wb.time_stamp/44100., wb.channel_id
    sl.process_spike = process_spike
    
    while True:
        sl.update()