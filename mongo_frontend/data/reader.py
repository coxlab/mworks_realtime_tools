#!/usr/bin/env python

import logging

import numpy
import scipy.stats

import pymongo

import pixelclock

# times should mworks (audio does not agree with epoch)
# make all functions accept a time range
#   do this by constructing a query dict

class Reader(object):
    def __init__(self, hostname, database,\
            mworks = 'mworks', spikes = 'spikes'):
        self.clock = pixelclock.PixelClock()

        self.conn = pymongo.Connection(hostname)
        self.db = self.conn[database]
        self.mworks = self.db[mworks]
        self.spikes = self.db[spikes]
        logging.debug('MWorks count: %i' % self.mworks.find().count())
        logging.debug('Spikes count: %i' % self.spikes.find().count())
        self._valid_offset = False

    def calculate_offset(self):
        evs = numpy.array([(c['time'], c['data']) for c in \
                self.mworks.find({'name': '#pixelClockOffset'}).\
                sort('time',pymongo.ASCENDING)])
        return self.clock.calculate_offset(evs[:,0],evs[:,1])

    def get_spikes_over_range(self, channel, trange):
        """time_range = mworks"""
        trange = [self.audio_to_mworks_time(trange[i]) for i in xrange(2)]
        auts = [s['aut'] for s in self.spikes.find(\
                {'aut' : {'$gt': trange[0], '$lt': trange[1]}, \
                'ch' : channel}, {'aut'})]
        auts = numpy.array(auts) * (1E6 / 44100.)
        return self.clock.audio_to_mworks_time(auts)

    def get_spikes(self, channel):
        auts = [s['aut'] for s in self.spikes.find(\
                {'ch': channel}, {'aut'})]
        auts = numpy.array(auts) * (1E6 / 44100.)
        return self.clock.audio_to_mworks_time(auts)
    
    def get_trials(self, match_dict = {}):
        # TODO failure filtering
        return self.get_stimuli(match_dict)

    def get_stimuli(self, match_dict = {}):
        query = {'name': '#stimDisplayUpdate'}
        if match_dict != {}: query['$elemMatch'] = match_dict
        updates = [t for t in self.mworks.find(\
                query,{'time', 'data'})]
        times = numpy.array([t['time'] for t in updates])
        # TODO is 'pos_x' a  good marker for a stimulus?
        stims = [s for t in updates\
                for s in t['data']\
                if ((s is not None) and ('pos_x' in s))]
        return times, stims

    def count_stimuli(self, match_dict = {}):
        query = {'name': '#stimDisplayUpdate'}
        if match_dict != {}: query['$elemMatch'] = match_dict
        return self.mworks.find(query).count()
    
    def unique_stimuli(self, match_dict):
        _, stims = self.get_stimuli(match_dict)
