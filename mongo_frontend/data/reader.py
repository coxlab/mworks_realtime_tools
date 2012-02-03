#!/usr/bin/env python

import logging

import numpy
#import scipy.stats

import pymongo

# this should just get events over mworks time
# make all functions accept a time range
#   do this by constructing a query dict

# times should mworks (audio does not agree with epoch)

def range_to_query(trange):
    return {'$gt' : trange[0], '$lt' : trange[1]}

class Reader(object):
    def __init__(self, hostname, database,\
            mworks_coll= 'mworks', spikes_coll = 'spikes'):

        self.conn = pymongo.Connection(hostname)
        self.db = self.conn[database]
        self.mworks_coll= mworks_coll
        self.spikes_coll = spikes_coll
        logging.debug('MWorks count: %i' % \
                self.db[self.mworks_coll].find().count())
        logging.debug('Spikes count: %i' % \
                self.db[self.spikes_coll].find().count())
        self._valid_offset = False

    #def query(self, db, coll, q, fn, ft):
    #    for i in self.conn[db][coll].find(q,fn):
    #        yield [i[n] for n in fn]

    def query(self, coll, q, fn = None):
        if fn == None:
            for i in self.db[coll].find(q):
                yield i
        elif type(fn) == list:
            for i in self.db[coll].find(q,fn):
                yield [i[n] for n in fn]
        elif type(fn) == dict:
            for i in self.db[coll].find(q,fn):
                yield i
        elif type(fn) == str:
            for i in self.db[coll].find(q,[fn]):
                yield i[fn]
        else:
            raise ValueError("Unknown fn: %s" % str(fn))

    def count(self, coll, q):
        return self.db[coll].find(q).count()
    
    def get_spikes(self, channel, trange = None):
        q = {'ch' : channel}
        if trange is not None:
            q['aut'] = range_to_query(trange)
        return numpy.array(self.query(self.spikes_coll, q, 'aut')) \
                * (1E6 / 44100.)

    def get_stimuli(self, match_dict = {}, trange = None):
        query = {'name': '#stimDisplayUpdate'}
        if trange is not None:
            query['time'] = range_to_query(trange)
        query['data'] = {'$elemMatch': \
                {'pos_x' : \
                {'$gt': -1000}}} # get only stimuli
        if match_dict != {}: query['data'] = {'$elemMatch': match_dict}
        updates = self.query(self.mworks_coll, query, 'data')

        return [s for update in updates \
                for s in update \
                if ((s is not None) and ('pos_x' in s))]

    def get_trials(self, match_dict = {}, trange = None):
        query = {'name': '#stimDisplayUpdate'}
        if trange is not None:
            query['time'] = range_to_query(trange)
        if match_dict != {}: query['data'] = {'$elemMatch': match_dict}
        updates = self.query(self.mworks_coll, query, ['time', 'data'])
        times = []
        stims = []
        for update in updates:
            times.append(update[0]) # 'time'
            for s in update[1]: # 'data'
                if (s is not None) and ('pos_x' in s):
                    # TODO is 'pos_x' a  good marker for a stimulus?
                    stims.append(s)
        return times, stims

    def count_stimuli(self, match_dict = {}, trange = None):
        query = {'name': '#stimDisplayUpdate'}
        if trange is not None:
            query['time'] = range_to_query(trange)
        query['data'] = {'$elemMatch': \
                {'pos_x' : \
                {'$gt': -1000}}} # get only stimuli
        if match_dict != {}: query['data'] = {'$elemMatch': match_dict}
        return self.count(self.mworks_coll, query)
    
    #def unique_stimuli(self, match_dict, trange = None):
    #    stims = self.get_stimuli(match_dict, trange)
    #    # figure out which are unique
