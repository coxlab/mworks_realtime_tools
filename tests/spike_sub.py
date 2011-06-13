#!/usr/bin/env python

import sys

#from pylab import *

sys.path.append('../')
from physio_online.spike_listener import SpikeListener

if __name__ == '__main__':
    sl = SpikeListener("ipc:///tmp/spike_channels/", xrange(32))
    def process_spike(wb): # overload process_spike
        print wb.time_stamp/44100., wb.channel_id
    sl.process_spike = process_spike
    
    while True:
        sl.update()