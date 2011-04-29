#!/myPython/bin/python

execfile('/myPython/bin/activate_this.py', dict(__file__='/myPython/bin/activate_this.py'))

import signal
import sys

#Let us profile code which uses threads
import thread
import time
from threading import *

from pylab import *

fakeProducer = True

if not fakeProducer:
    sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
    from mworks.conduit import IPCClientConduit

class LickData:
    def __init__(self, maxN = 50):
        self.x = []
        self.y = []
        self.maxN = maxN
    def add_event(self, event):
        print "Adding event to data"
        self.x.append(event.time)
        self.y.append(event.data)
        while len(self.x) > self.maxN:
            self.x.pop(0)
            self.y.pop(0)
    def is_empty(self):
        return not (len(self.x) + len(self.y))
    def get_x(self):
        x = array(self.x,dtype=float)
        #x -= min(x)
        #if max(x) != 0: x /= float(max(x)/10.)
        return x
    def get_y(self):
        y = array(self.y)
        return y

global cond
cond = Condition()

global ld
ld = LickData()

global line
line = None

def receive_event(event):
    global cond, ld
    print "Receive event attempted to acquire lock"
    cond.acquire()
    print "Received event"
    ld.add_event(event)
    print "Notifying"
    cond.notifyAll()
    cond.release()

def update_plot():
    global cond, ld, line
    
    if line == None:
        ion()
        line, = plot(arange(2),arange(2))
        gca().set_xlim([0.,10.])
        gca().set_ylim([0.,1000.])
    
    cond.acquire()
    print "Updating plot"
    
    while ld.is_empty():
        print "Waiting for data"
        cond.wait()
    
    # update data
    print "Setting data: %i %i" % (len(ld.x), len(ld.y))
    x = ld.get_x()
    y = ld.get_y()
    #print x, y
    gca().set_xlim([min(x),max(x)])
    gca().set_ylim([min(y),max(y)])
    line.set_xdata(ld.get_x())
    line.set_ydata(ld.get_y())
    
    cond.release()
    
    # draw
    print "Drawing"
    draw()

global eventIndex
eventIndex = 0

class FakeEvent:
    def __init__(self):
        #t = time.time()
        global eventIndex
        t = eventIndex/10.
        eventIndex += 1
        self.data = t
        self.time = t
        self.code = 0.

class EventProducer(Thread):
    def __init__(self,nEvents,hz):
        Thread.__init__(self)
        self.nEvents = nEvents
        self.iei = 1/float(hz)
    def run(self):
        for i in xrange(self.nEvents):
            print "Produced Event"
            event = FakeEvent()
            print "Received Event"
            receive_event(event)
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
        client.register_callback_for_name('LickInput2', receive_event)
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