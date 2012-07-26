#!/usr/bin/env python

import pylab

import data

reader = data.reader.Reader('soma2.rowland.org', 'test_120201')

stim_times, stims = reader.get_trials({})
spike_times = pylab.array(reader.get_spikes(1))

print "Found %i trials" % len(stims)
if len(stims): print "\tExample: %s" % str(stims[0])
print "Found %i spikes" % len(spike_times)

pylab.figure()
stimy = pylab.ones_like(stim_times)
spikey = pylab.zeros_like(spike_times)
pylab.scatter(stim_times, stimy, color='b')
pylab.scatter(spike_times, spikey, color='g')
pylab.title('Mworks Time')

pylab.figure()
pylab.scatter(reader.mworks_to_audio_time(stim_times),\
        stimy, color='b')
pylab.scatter(reader.mworks_to_audio_time(spike_times),\
        spikey, color='g')
pylab.title('Audio Time')

pylab.show()
