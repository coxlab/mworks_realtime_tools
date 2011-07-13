#!/myPython/bin/python
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

############################!/usr/bin/env python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import logging, sys
logging.basicConfig(level=logging.ERROR)

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

class QtStimSorter(QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.setDynamicSortFilter(True)
        self.columnFilters = []
        for i in xrange(6):
            self.columnFilters.append(QRegExp('.', Qt.CaseInsensitive, QRegExp.PatternSyntax(QRegExp.RegExp)))
        self.core = None
    
    def filterAcceptsRow(self, sourceRow, sourceParent):
        ret = True
        for i in xrange(6):
            colI = self.sourceModel().index(sourceRow, i, sourceParent)
            regex = self.columnFilters[i]
            if regex.indexIn(str(self.sourceModel().data(colI))) == -1:
                ret = False
        return ret
    
    def query(self):
        self.set_filter(self.nameEdit.text(), 0)
        self.set_filter(self.posXEdit.text(), 1)
        self.set_filter(self.posYEdit.text(), 2)
        self.set_filter(self.sizeEdit.text(), 3)
        self.invalidateFilter()
        if not (self.core is None):
            core.display_selection()
    
    def set_filter(self, filterString, colI):
        self.columnFilters[colI] = QRegExp(filterString, Qt.CaseInsensitive, QRegExp.PatternSyntax(QRegExp.RegExp))
    
    def get_stimuli(self):
        stimuli = []
        sd = {}
        for r in xrange(self.rowCount()):
            sd['name'] = str(self.data(self.index(r,0)))
            for (c,a) in enumerate(['pos_x','pos_y','size_x','size_y','rotation']):
                sd[a] = self.data(self.index(r,c+1))
            stimuli.append(physio_online.stimsorter.Stim(sd))
        return stimuli

class QtStimSpikeSyncerModel(physio_online.stimsorter.StimSpikeSyncer, QStandardItemModel):
    def __init__(self, *args, **kwargs):
        QStandardItemModel.__init__(self, *args, **kwargs)
        physio_online.stimsorter.StimSpikeSyncer.__init__(self)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(['Name','Pos X','Pos Y','Size X','Size Y','Rotation'])
    
    def add_stim(self, stim):
        i = physio_online.stimsorter.StimSpikeSyncer.add_stim(self, stim)
        rowI = None
        for r in xrange(self.rowCount()):
            try:
                intName = int(self.item(r, 0).text())
            except:
                intName = -ord(str(self.item(r,0).text())[0])
            if intName > stim.intName:
                rowI = r
                break
            elif intName < stim.intName:
                continue
            if float(self.item(r,1).text()) > stim.pos_x:
                rowI = r
                break
            elif float(self.item(r,1).text()) < stim.pos_x:
                continue
            if float(self.item(r,2).text()) > stim.pos_y:
                rowI = r
                break
            elif float(self.item(r,2).text()) < stim.pos_y:
                continue
            if float(self.item(r,3).text()) > stim.size_x:
                rowI = r
                break
            elif float(self.item(r,3).text()) < stim.size_x:
                continue
            if float(self.item(r,4).text()) > stim.size_y:
                rowI = r
                break
            elif float(self.item(r,4).text()) < stim.size_y:
                continue
            if float(self.item(r,5).text()) > stim.rotation:
                rowI = r
                break
            elif float(self.item(r,5).text()) < stim.rotation:
                continue
        if rowI is None:
            rowI = self.rowCount()
        self.insertRow(rowI)
        self.setData(self.index(rowI, 0), stim.name)
        self.setData(self.index(rowI, 1), stim.pos_x)
        self.setData(self.index(rowI, 2), stim.pos_y)
        self.setData(self.index(rowI, 3), stim.size_x)
        self.setData(self.index(rowI, 4), stim.size_y)
        self.setData(self.index(rowI, 5), stim.rotation)
    
    def clear_stimuli(self):
        physio_online.stimsorter.StimSpikeSyncer.clear_stimuli(self)
        self.clear()
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(['Name','Pos X','Pos Y','Size X','Size Y','Rotation'])
    
    # def stim_at_row(self, r):
    #     sd = {}
    #     sd['name'] = str(self.item(r,0).text())
    #     sd['pos_x'] = float(self.item(r,1).text())
    #     sd['pos_y'] = float(self.item(r,2).text())
    #     sd['size_x'] = float(self.item(r,3).text())
    #     sd['size_y'] = float(self.item(r,4).text())
    #     sd['rotation'] = float(self.item(r,5).text())
    #     return physio_online.stimsorter.Stim(sd)
    # 
    # def get_selected(self):
    #     selectedRows = self.table.selectionModel().selectedRows()
    #     selectedStimI = []
    #     for sel in selectedRows:
    #         stim = self.stim_at_row(sel.row())
    #         i = self.find_stim(stim)
    #         if i == -1:
    #             logging.warning("Selected row[%i][stim=%s] did not match" % (sel.row(), stim))
    #         else:
    #             selectedStimI.append(i)
    #     return selectedStimI

class QtPhysio(physio_online.core.Core):
    def __init__(self, config, figure, axes, parent=None):
        physio_online.core.Core.__init__(self, config)
        self.figure = figure
        self.axes = axes
        # little bit of a hack
        self.stimSpikeSyncer = QtStimSpikeSyncerModel()
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
        self.channel = channel-1 # convert from 1 to 0 based indexing
        self.display_selection()
    
    def display_selection(self):
        # selectedStimI = self.stimSpikeSyncer.get_selected()
        stimuli = self.sortModel.get_stimuli()
        spikes = []
        # for stimI in selectedStimI:
        for stim in stimuli:
            try:
                stimI = core.stimSpikeSyncer.find_stim(stim)
                if stimI != -1:
                    spikes += core.stimSpikeSyncer.get_stim_spikes(self.channel,stimI)
                else:
                    logging.warning("Attempted to get spikes for unknown stimulus: %s" % str(stim))
            except:
                logging.debug('No spikes')
                return
        self.draw_spikes(spikes)

# Create a Qt application 
app = QApplication(sys.argv)
loader = QUiLoader()
f = QFile('resources/online.ui')
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
sortModel = QtStimSorter()
sortModel.setSourceModel(core.stimSpikeSyncer)
stimuliTableView = win.findChild(QTableView, 'stimuliTableView')
stimuliTableView.setModel(sortModel)
core.sortModel = sortModel
sortModel.core = core
# core.stimSpikeSyncer.set_table(stimuliTable)
# stimuliTable.selectionModel().selectionChanged.connect(core.display_selection)

channelSpin = win.findChild(QSpinBox, 'channelSpin')
channelSpin.valueChanged[int].connect(core.set_channel)

# fill with fake stimuli and spikes
if False:
    sd = {'name':'0','pos_x':0,'pos_y':0,'size_x':1,'size_y':1,'rotation':0}
    core.stimSpikeSyncer.add_stim(physio_online.stimsorter.Stim(sd))
    sd['name'] = '1'
    sd['pos_x'] = 1
    core.stimSpikeSyncer.add_stim(physio_online.stimsorter.Stim(sd))
    sd['name'] = '3'
    sd['size_x'] = 0.5
    core.stimSpikeSyncer.add_stim(physio_online.stimsorter.Stim(sd))
    core.stimSpikeSyncer.channels[0][0] = [0.01,-0.01]
    core.stimSpikeSyncer.channels[0][1] = [0.02,0.025]
    core.stimSpikeSyncer.channels[0][2] = [0.03,0.035]
    sd['name'] = 'BlueSquare'
    core.stimSpikeSyncer.add_stim(physio_online.stimsorter.Stim(sd))

# self.view.selectionModel().selectionChanged.connect(self.updateActions)
# stimuliTable.setModel(core.stimSpikeSyncer)
# stimuliTable.clicked[QModelIndex].connect(core.stimSpikeSyncer.clicked)

clearSpikesButton = win.findChild(QPushButton, 'clearSpikesButton')
clearSpikesButton.clicked.connect(core.clear_spikes)

clearStimuliButton = win.findChild(QPushButton, 'clearStimuliButton')
clearStimuliButton.clicked.connect(core.clear_stimuli)


# global nameText, posText, sizeText
# def query():
#     global nameText, posText, sizeText
#     print "query:",nameText.toPlainText(),posText.toPlainText(),sizeText.toPlainText()
    

queryButton = win.findChild(QPushButton, 'queryButton')
queryButton.clicked.connect(sortModel.query)

sortModel.nameEdit = win.findChild(QLineEdit, 'nameEdit')
sortModel.nameEdit.textChanged.connect(sortModel.query)
sortModel.posXEdit = win.findChild(QLineEdit, 'posXEdit')
sortModel.posXEdit.textChanged.connect(sortModel.query)
sortModel.posYEdit = win.findChild(QLineEdit, 'posYEdit')
sortModel.posYEdit.textChanged.connect(sortModel.query)
sortModel.sizeEdit = win.findChild(QLineEdit, 'sizeEdit')
sortModel.sizeEdit.textChanged.connect(sortModel.query)

# make and start update timer
timer = QTimer(canvas)
timer.timeout.connect(core.update)
timer.start(1000)

win.show()
sys.exit(app.exec_())