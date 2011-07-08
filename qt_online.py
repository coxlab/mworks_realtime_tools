#!/usr/bin/env python
"""
    A Qt based online physiology monitoring program
    
    What this should have...
    Bare minimum:
        - audio/mworks clock syncing
        - online psth (with arbitrary grouping)
    Little more:
        - include raster view
        - timed note entries
        - stimulus viewing & selection (for screening->testing transition)
    Even more:
        - include cnc control, frame generation, everything from cncController
    
    == Parts ==
    Core should be UI independent
"""

import logging, sys
logging.basicConfig(level=logging.DEBUG)

import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pylab as pl
import numpy as np

#import sys
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtUiTools import *

import physio_online

# class QtStimSpikeSyncer(physio_online.stimsorter.StimSpikeSyncer, QStandardItemModel):
#     def __init__(self, parent=None):
#         physio_online.stimsorter.StimSpikeSyncer.__init__(self)
#         QStandardItemModel.__init__(self, 0, 5, parent) # name, posx, posy, sizex, sizy
#         self.setHeaderData(0, Qt.Horizontal, "Name")
#         self.setHeaderData(1, Qt.Horizontal, "Pos X")
#         self.setHeaderData(2, Qt.Horizontal, "Pos Y")
#         self.setHeaderData(3, Qt.Horizontal, "Size X")
#         self.setHeaderData(4, Qt.Horizontal, "Size Y")
#     def add_stim(self, stim):
#         i = physio_online.stimsorter.StimSpikeSyncer.add_stim(self, stim)
#         # add stimulus to model
#         self.insertRow(0)
#         self.setData(self.index(0, 0), stim['name'])
#         self.setData(self.index(0, 1), stim['pos_x'])
#         self.setData(self.index(0, 2), stim['pos_y'])
#         self.setData(self.index(0, 3), stim['size_x'])
#         self.setData(self.index(0, 4), stim['size_y'])
#         return i
#     
#     def clicked(self, index):
#         print self.itemFromIndex(index)
#     
#     def clear_stimuli(self):
#         physio_online.stimsorter.StimSpikeSyncer.clear_stimuli(self)
#         self.clear()

class QtStimSpikeSyncer(physio_online.stimsorter.StimSpikeSyncer):
    def set_table(self, table):
        self.table = table
        # self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.table.setColumnCount(6)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setHorizontalHeaderLabels(['Name','Pos X','Pos Y','Size X','Size Y','Rotation'])
    
    def add_stim(self, stim):
        i = physio_online.stimsorter.StimSpikeSyncer.add_stim(self, stim)
        self.table.insertRow(0)
        self.table.setItem(0, 0, QTableWidgetItem(stim.name))
        self.table.setItem(0, 1, QTableWidgetItem(str(stim.pos_x)))
        self.table.setItem(0, 2, QTableWidgetItem(str(stim.pos_y)))
        self.table.setItem(0, 3, QTableWidgetItem(str(stim.size_x)))
        self.table.setItem(0, 4, QTableWidgetItem(str(stim.size_y)))
        self.table.setItem(0, 5, QTableWidgetItem(str(stim.rotation)))
    
    def clear_stimuli(self):
        physio_online.stimsorter.StimSpikeSyncer.clear_stimuli(self)
        self.table.clear()
    
    def stim_at_row(self, r):
        sd = {}
        sd['name'] = str(self.table.item(r,0).text())
        sd['pos_x'] = float(self.table.item(r,1).text())
        sd['pos_y'] = float(self.table.item(r,2).text())
        sd['size_x'] = float(self.table.item(r,3).text())
        sd['size_y'] = float(self.table.item(r,4).text())
        sd['rotation'] = float(self.table.item(r,5).text())
        return physio_online.stimsorter.Stim(sd)
    
    def get_selected(self):
        selectedRows = self.table.selectionModel().selectedRows()
        selectedStimI = []
        for sel in selectedRows:
            stim = self.stim_at_row(sel.row())
            i = self.find_stim(stim)
            if i == -1:
                logging.warning("Selected row[%i][stim=%s] did not match" % (sel.row(), stim))
            else:
                selectedStimI.append(i)
        return selectedStimI

class QtPhysio(physio_online.core.Core):
    def __init__(self, config, figure, axes, parent=None):
        physio_online.core.Core.__init__(self, config)
        self.figure = figure
        self.axes = axes
        # little bit of a hack
        self.stimSpikeSyncer = QtStimSpikeSyncer()
        self.channel = 0
    
    def update(self):
        # call super
        physio_online.core.Core.update(self)
    
    def draw_spikes(self, spikes):
        self.axes.cla()
        if spikes:
            self.axes.hist(spikes,bins=np.linspace(-0.1,0.5,25),alpha=0.5,color='k')
        self.axes.vlines(0,0,self.axes.get_ylim()[1],color='b')
        self.axes.figure.canvas.draw()
    
    def set_channel(self, channel):
        self.channel = channel
        self.display_selection()
    
    def display_selection(self):
        selectedStimI = self.stimSpikeSyncer.get_selected()
        spikes = []
        for stimI in selectedStimI:
            try:
                spikes += core.stimSpikeSyncer.get_stim_spikes(self.channel,stimI) # TODO channel and stimuli selection
            except:
                logging.debug('No spikes')
                return
        self.draw_spikes(spikes)

# Create a Qt application 
app = QApplication(sys.argv)
loader = QUiLoader()
f = QFile('resources/psth.ui')
f.open(QFile.ReadOnly)
win = loader.load(f)

# make initial matplotlib figure
fig = Figure(figsize=(600,600), dpi=72, facecolor=(1,1,1), edgecolor=(0,0,0))
ax = fig.add_subplot(111)
ax.plot([0,1])
canvas = FigureCanvas(fig)

# attach plot
mpl = win.findChild(QVBoxLayout,'mplPlot')
mpl.addWidget(canvas)

# make core physio_online object
config = physio_online.cfg.Config()
core = QtPhysio(config, fig, ax, win)

# setup stimulus table
stimuliTable = win.findChild(QTableWidget, 'stimuliTable')
core.stimSpikeSyncer.set_table(stimuliTable)
stimuliTable.selectionModel().selectionChanged.connect(core.display_selection)

channelSpin = win.findChild(QSpinBox, 'channelSpin')
channelSpin.valueChanged[int].connect(core.set_channel)

# fill with fake stimuli and spikes
sd = {'name':'0','pos_x':0,'pos_y':0,'size_x':1,'size_y':1,'rotation':0}
core.stimSpikeSyncer.add_stim(physio_online.stimsorter.Stim(sd))
sd['name'] = '1'
core.stimSpikeSyncer.add_stim(physio_online.stimsorter.Stim(sd))
sd['name'] = '3'
core.stimSpikeSyncer.add_stim(physio_online.stimsorter.Stim(sd))
core.stimSpikeSyncer.channels[0][0] = [0.01,-0.01]
core.stimSpikeSyncer.channels[0][1] = [0.02,0.025]
core.stimSpikeSyncer.channels[0][2] = [0.03,0.035]

# self.view.selectionModel().selectionChanged.connect(self.updateActions)
# stimuliTable.setModel(core.stimSpikeSyncer)
# stimuliTable.clicked[QModelIndex].connect(core.stimSpikeSyncer.clicked)

# make and start update timer
timer = QTimer(canvas)
timer.timeout.connect(core.update)
timer.start(1000)

win.show()
sys.exit(app.exec_())