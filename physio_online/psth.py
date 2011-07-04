#!/usr/bin/env python
"""
Online psth for every unique stimulus. Needs

 - Clock sync (to sync audio and mworks times)
 - Zmq spike listener
 - mwconduit listener (can read clock sync in future)
 - realtime plot
 - selectable channel & stimulus

"""

import logging

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

class LivePSTH:
    def __init__(self, ax, nChans=32):
        _,_,patches = ax.hist([0],bins=np.linspace(-0.1,0.5,25),alpha=0.5,color='k') # bin into 24 bins
        self.patches = patches
        self.figure = self.patches[0].figure
        self.axes = self.patches[0].axes
        for p in self.patches:
            p.set_y(0.)
            p.set_height(0.)
        self.spikes = []
        self.update_patches()
    
    def connect(self):
        """Connect callbacks"""
        self.cidpress = self.figure.canvas.mpl_connect(
            'button_press_event', self.on_press)
        # self.cidpress = self.channelControl.figure.canvas.mpl_connect(
        #         'button_press_event', self.change_channel_press)
    
    def on_press(self, event):
        """Process mouse press callback"""
        # print event
        if event.inaxes != self.axes: return
        self.add_spike(event.xdata)
    
    def update_patches(self):
        maxH = self.axes.get_ylim()[1]
        for s in self.spikes:
            for p in self.patches:
                if s > p.get_x() and s <= (p.get_x() + p.get_width()):
                    h = p.get_height() + 1
                    p.set_height(h)
                    maxH = max(maxH,h)
                    continue
        self.spikes = []
        if maxH > self.axes.get_ylim()[1]:
            self.axes.set_ylim([0,h])
        self.figure.canvas.draw()
    
    def add_spike(self, offset):
        self.spikes.append(offset)
        self.update_patches()

class VerticalSelect(object):
    def __init__(self, axes, nOptions, initial=0, title=''):
        self.axes = axes
        self.patch = axes.barh([initial],[1],height=1.)[0]
        self.item = initial
        axes.set_yticks(np.arange(nOptions)+0.5)
        axes.set_yticklabels(np.arange(1,nOptions+1),va='center',stretch='expanded')
        axes.set_ylim([0,nOptions])
        axes.set_xticks([])
        axes.set_title(title)
    
    def connect(self):
        self.cidpress = self.axes.figure.canvas.mpl_connect(
                'button_press_event', self.on_press)
    
    def on_press(self, event):
        if event.inaxes  != self.axes: return
        self.change_item(int(event.ydata))
    
    def change_item(self, item):
        self.item = item
        self.patch.set_y(item)
        self.axes.figure.canvas.draw()

if __name__ == '__main__':
    fig = plt.figure()

    gs = gridspec.GridSpec(1, 5, width_ratios=[1,12,1,1,1])

    # channel control
    cc = VerticalSelect(fig.add_subplot(gs[0]),32,title='C')
    # stim control
    sc = VerticalSelect(fig.add_subplot(gs[2]),12,title='I') # stimulus control
    tc = VerticalSelect(fig.add_subplot(gs[3]),5,title='T') # translation control
    zc = VerticalSelect(fig.add_subplot(gs[4]),3,title='S') # size control


    lp = LivePSTH(fig.add_subplot(gs[1]))
    cc.connect()
    sc.connect()
    tc.connect()
    zc.connect()
    lp.connect()

    plt.show()