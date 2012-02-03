#!/usr/bin/env python

import logging

import numpy
import scipy.stats

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

class PixelClock(object):
    def __init__(self, zcutoff = 3., min_n = 10):
        """
        Arguments
        =========
        zcutoff : outlier z-score cutoff
        min_n : min number of offsets to fit prediction
        """
        self._valid_offset = False
        self._mw_to_au = None
        self._au_to_mw = None
        self._mw_to_offset = None
        self._err_to_z = None

        self.zcutoff = zcutoff
        self.min_n = min_n
        self.n_outliers = 0

        self.times = []
        self.offsets = []

    def add_event(self, time, offset):
        self.times.append(time)
        self.offsets.append(offset)

        if self._valid_offset:
            # test if offset agrees with prediction
            prediction = self.get_offset(time)
            err = prediction - offset
            z = self._err_to_z(err)
            if abs(z) > self.zcutoff:
                # this is an outlier, or prediction is wrong
                self.n_outliers += 1
                if self.n_outliers >= self.min_n:
                    self.calculate_offset(self.times,\
                            self.offsets)
                    self.n_outliers = 0
        else:
            # no valid prediction
            if len(self.times) >= self.min_n:
                self.calculate_offset(self.times,\
                        self.offsets)

    def reset(self):
        self._valid_offset = False
        self.times = []
        self.offsets = []

    def get_recent_time(self):
        self.times[-1]

    def calculate_offset(self, times, offsets):
        non_outliers = numpy.logical_not(\
                find_outlier_indices(offsets, self.zcutoff))

        x = times[non_outliers] # mworks times
        y = offsets[non_outliers] # offsets
        cx, cy, m, b = fit_line_and_cull(x, y, self.zcutoff)
        
        self._mw_to_au = lambda w: w - (w * m + b)
        self._au_to_mw = lambda a: (a + b) / (1. - m)
        self._mw_to_offset = lambda w: w * m + b # for a mw time
        self._valid_offset = True

        # make z_score function
        erry =  cy - (cx * m + b)
        zm = numpy.mean(erry)
        zs = numpy.std(erry)
        self._err_to_z = lambda e: (e - zm) / zs

        return m, b

    def audio_to_mworks_time(self, time):
        if not self._valid_offset:
            return self._au_to_mw(time)
        else:
            logging.warning("Attempted audio_to_mworks with no offset")
            # TODO what should I return here?
            return time

    def mworks_to_audio_time(self, time):
        if not self._valid_offset:
            return self._mw_to_au(time)
        else:
            logging.warning("Attempted mworks_to_audio with no offset")
            # TODO what should I return here?
            return time

    def get_offset(self, mworks_time):
        if not self._valid_offset:
            return self._mw_to_offset(mworks_time)
        else:
            logging.warning("Attempted get_offset with no offset")
            # TODO what should I return here?
            return mworks_time
