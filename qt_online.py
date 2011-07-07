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

#import sys
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtUiTools import *

import physio_online

class QtPhysio(physio_online.core.Core):
    def __init__(self, config, figure, axes):
        physio_online.core.Core.__init__(self, config)
        self.figure = figure
        self.axes = axes
    def update(self):
        # call super
        physio_online.core.Core.update(self)
        try:
            spikes = core.stimSpikeSyncer.get_stim_spikes
            self.draw_spikes(spikes)
        except:
            logging.debug('No spikes')
            return
    def draw_spikes(self, spikes):
        self.axes.cla()
        self.axes.hist(spikes,bins=np.linspace(-0.1,0.5,25),alpha=0.5,color='k')
        self.axes.vlines(0,0,self.axes.get_ylim()[1],color='b')
        self.axes.figure.canvas.draw()

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

config = physio_online.cfg.Config()
core = QtPhysio(config, fig, ax)

# attach plot
mpl = win.findChild(QVBoxLayout,'mplPlot')
mpl.addWidget(canvas)

timer = QTimer(canvas)
timer.timeout.connect(core.update)
timer.start(100)

win.show()
sys.exit(app.exec_())