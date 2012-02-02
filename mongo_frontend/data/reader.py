#!/usr/bin/env python

import logging

import numpy
import scipy.stats

import pymongo

# times should mworks (audio does not agree with epoch)
# make all functions accept a time range
#   do this by constructing a query dict

def find_outlier_indices(a, zcutoff):
    return numpy.abs(scipy.stats.zscore(a)) > zcutoff

def fit_line(x, y):
    m, b, _ , _ ,_ = scipy.stats.linregress(x, y)
    return m, b

def fit_line_and_cull(x, y, zcutoff):
    m, b = fit_line(x, y)
    no = numpy.logical_not(find_outlier_indices(y - (x * m + b), zcutoff))
    cx = x[no]
    cy = y[no]
    m, b = fit_line(cx, cy)
    return cx, cy, m, b

class Reader(object):
    def __init__(self, hostname, database,\
            mworks = 'mworks', spikes = 'spikes'):
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
        
        # t = evs[:,0], data = evs[:,1]
        non_outliers = numpy.logical_not(find_outlier_indices(evs[:,1], 3)) # array of True/False

        x = evs[non_outliers,0] # mworks times
        y = evs[non_outliers,1] # offsets
        cx, cy, m, b = fit_line_and_cull(x, y, 3)
        
        self._mw_to_au = lambda w: w - (w * m + b)
        self._au_to_mw = lambda a: (a + b) / (1. - m)
        self._mw_to_offset = lambda w: w * m + b # for a mw time
        self._valid_offset = True
        return m, b

    def audio_to_mworks_time(self, time):
        if not self._valid_offset: self.calculate_offset()
        return self._au_to_mw(time)

    def mworks_to_audio_time(self, time):
        if not self._valid_offset: self.calculate_offset()
        return self._mw_to_au(time)

    def get_offset(self, mworks_time):
        if not self._valid_offset: self.calculate_offset()
        return self._mw_to_offset(mworks_time)

    def get_spikes_over_range(self, channel, trange):
        """time_range = mworks"""
        trange = [self.audio_to_mworks_time(trange[i]) for i in xrange(2)]
        auts = [s['aut'] for s in self.spikes.find(\
                {'aut' : {'$gt': trange[0], '$lt': trange[1]}, \
                'ch' : channel}, {'aut'})]
        auts = numpy.array(auts) * (1E6 / 44100.)
        return self.audio_to_mworks_time(auts)

    def get_spikes(self, channel):
        auts = [s['aut'] for s in self.spikes.find(\
                {'ch': channel}, {'aut'})]
        auts = numpy.array(auts) * (1E6 / 44100.)
        return self.audio_to_mworks_time(auts)
    
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
