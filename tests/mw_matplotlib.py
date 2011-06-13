#!/myPython/bin/python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import signal
import sys

#Let us profile code which uses threads
import thread
import time
from threading import *

from pylab import *

fakeProducer = False
targetEvents = ['LickInput','LickInput3','LickInput3']

global codeToName
codeToName = {}

if not fakeProducer:
    sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
    from mworks.conduit import IPCClientConduit

class MWData:
    def __init__(self, targetEvents, maxN = 500):
        self.xs = {}
        self.ys = {}
        self.maxN = maxN
        for targetEvent in targetEvents:
            self.xs[targetEvent] = []
            self.ys[targetEvent] = []
    def add_event(self, name, event):
        print "Adding event to data: %s" % name
        self.xs[name].append(event.time)
        self.ys[name].append(event.data)
        while len(self.xs[name]) > self.maxN:
            self.xs[name].pop(0)
            self.ys[name].pop(0)
    def is_empty(self):
        for k in self.xs.keys():
            if len(self.xs[k]) + len(self.ys[k]):
                return False
        return True
    def get_x(self,name):
        x = array(self.xs[name],dtype=float)/1000000.
        #x -= min(x)
        #if max(x) != 0: x /= float(max(x)/10.)
        return x
    def get_y(self,name):
        y = array(self.ys[name])
        return y

global cond
cond = Condition()

global data
data = MWData(targetEvents)

global lines
lines = {}

def receive_event(event):
    global cond, data, codeToName
    name = codeToName[event.code]
    print "Receive event attempted to acquire lock"
    cond.acquire()
    print "Received event: %s" % name
    data.add_event(name, event)
    print "Notifying"
    cond.notifyAll()
    cond.release()

def update_plot():
    global cond, data, lines
    
    if lines == {}:
        ion()
        for targetEvent in targetEvents:
            lines[targetEvent], = plot(arange(2),arange(2),label=targetEvent)
        gca().set_xlim([0.,10.])
        gca().set_ylim([0.,1000.])
        
        legend()
    
    cond.acquire()
    print "Updating plot"
    
    while data.is_empty():
        print "Waiting for data"
        cond.wait()
    
    # update data
    
    print "Setting data"
    xlims = None
    ylims = None
    for e in targetEvents:
        line = lines[e]
        x = data.get_x(e)
        y = data.get_y(e)
        sys.stdout.write("%s %i %i\n" % (e, len(x), len(y)))
        sys.stdout.flush()
        line.set_xdata(x)
        line.set_ydata(y)
        if not (len(x) + len(y)): # check if empty
            continue
        if xlims == None:
            xlims = [min(x),max(x)]
            ylims = [min(y),max(y)]
        else:
            xlims = [min(min(x),xlims[0]),max(max(x),xlims[1])]
            ylims = [min(min(y),ylims[0]),max(max(y),ylims[1])]
    
    # todo add sensible axis limiting
    
    # set limits on axis
    if xlims[0] != xlims[1]:
        dt = xlims[1] - xlims[0]
        min(dt,10.)
        xlims[0] = xlims[1] - dt
        gca().set_xlim(xlims)
    if ylims[0] != ylims[1]: # why does this happen?
        gca().set_ylim(ylims)
    
    cond.release()
    
    # draw
    print "Drawing"
    draw()

global eventIndex
eventIndex = 0

class FakeEvent:
    def __init__(self, data=0.,time=0.,code=0):
        #t = time.time()
        self.data = data
        self.time = time
        self.code = code

class EventProducer(Thread):
    def __init__(self,nEvents,hz):
        Thread.__init__(self)
        self.nEvents = nEvents
        self.iei = 1/float(hz)
        self.eventIndex = 0
    def run(self):
        for i in xrange(self.nEvents):
            print "Produced Event"
            t = self.eventIndex/10.
            self.eventIndex += 1
            event = FakeEvent(t,t,0)
            print "Received Event"
            receive_event('fake',event)
            print "Sleeping..."
            time.sleep(self.iei)

if __name__=="__main__":
    if fakeProducer:
        fp = EventProducer(1000,100)
        fp.start()
    else:
        conduit_resource_name = 'python_bridge_plugin_conduit'

        client = IPCClientConduit(conduit_resource_name)
        client.initialize()
        sys.stdout.write('registering callbacks\n')
        for i in xrange(len(targetEvents)):
            eventName = targetEvents[i]
            #client.register_callback_for_name(eventName, receive_event)
            client.register_local_event_code(i,targetEvents[i])
            client.register_callback_for_name(eventName, receive_event)
            codeToName[i] = targetEvents[i]
        print codeToName
        sys.stdout.write('waiting for events\n')
    
    while 1:
        update_plot()
        if fakeProducer:
           if not fp.is_alive():
               print "Fake event producer is done producing events"
               break 
        time.sleep(1.)
    
    print "Joining threads"
    if fakeProducer:
        fp.join()
    else:
        client.finalize()
    print "DONE!"
    show()