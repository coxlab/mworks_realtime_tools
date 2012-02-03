#!/usr/bin/env python

import collections
import logging

def compare_stimuli(a, b, keys):
    return all([a[k] == b[k] for k in keys])

default_keys = ['name', 'pos_x', 'pos_y', 'rotation', 'size_x', 'size_y']

def unique_stimuli(stimuli, keys = default_keys):
    uniques = [stimuli[0]]
    for i in xrange(1,len(stimuli)):
        for u in uniques:
            if compare_stimuli(stimuli[i], u, keys):
                break
        else:
            uniques.append(stimuli[i])
    return uniques

def unique_keys(stimuli, keys = default_keys):
    ukeys = collections.defaultdict(list)
    for s in stimuli:
        for k in keys:
            if s[k] not in ukeys[k]: ukeys[k].append(s[k])
    return ukeys
