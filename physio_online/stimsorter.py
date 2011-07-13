#!/usr/bin/env python

import logging

class Stim(object):
    # attributePrecedence = ['rotation','size_y','size_x','pos_y','pos_x','name']
    attributePrecedence = ['intName','pos_x','pos_y','size_x','size_y','rotation']
    def __init__(self, stimdict):
        self.stimdict = stimdict
        self.name = stimdict['name']
        try: # hack to allow sorting with non-int name sorting
            self.intName = int(self.name)
        except:
            self.intName = -ord(self.name[0])
        self.pos_x = stimdict['pos_x']
        self.pos_y = stimdict['pos_y']
        self.rotation = stimdict['rotation']
        self.size_x = stimdict['size_x']
        self.size_y = stimdict['size_y']
    
    def __lt__(self, other):
        for attr in self.attributePrecedence:
            print self.__getattribute__(attr), other.__getattribute__(attr), self.__getattribute__(attr) < other.__getattribute__(attr)
            if self.__getattribute__(attr) < other.__getattribute__(attr):
                return True
            elif self.__getattribute__(attr) > other.__getattribute__(attr):
                return False
        return False

    def __gt__(self, other):
        for attr in self.attributePrecedence:
            print self.__getattribute__(attr), other.__getattribute__(attr), self.__getattribute__(attr) > other.__getattribute__(attr)
            if self.__getattribute__(attr) > other.__getattribute__(attr):
                return True
            elif self.__getattribute__(attr) < other.__getattribute__(attr):
                return False
        return False

    def __le__(self, other):
        for attr in self.attributePrecedence:
            print self.__getattribute__(attr), other.__getattribute__(attr), self.__getattribute__(attr) < other.__getattribute__(attr)
            if self.__getattribute__(attr) < other.__getattribute__(attr):
                return True
            elif self.__getattribute__(attr) > other.__getattribute__(attr):
                return False
        return True

    def __ge__(self, other):
        for attr in self.attributePrecedence:
            print self.__getattribute__(attr), other.__getattribute__(attr), self.__getattribute__(attr) > other.__getattribute__(attr)
            if self.__getattribute__(attr) > other.__getattribute__(attr):
                return True
            elif self.__getattribute__(attr) < other.__getattribute__(attr):
                return False
        return True

    def __eq__(self, other):
        for attr in self.attributePrecedence:
            if self.__getattribute__(attr) != other.__getattribute__(attr):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)
    
    # def comp(self, other):
    #     if (self.name != other.name) or \
    #         (self.pos_x != other.pos_x) or \
    #         (self.pos_y != other.pos_y) or \
    #         (self.size_x != other.size_x) or \
    #         (self.size_y != other.size_y) or \
    #         (self.rotation != other.rotation):
    #         return False
    #     else:
    #         return True
    
    def __repr__(self):
        return 'Stim:%s x:%.2f y:%.2f r:%.2f size:%.2f %.2f' % \
            (self.name, self.pos_x, self.pos_y,\
            self.rotation, self.size_x, self.size_y)

class StimSorter(object):
    def __init__(self):
        self.stimList = []
    
    def find_stim(self, stim):
        for i in xrange(len(self.stimList)):
            if self.stimList[i] == (stim):
                return i
        return -1
    
    def add_stim(self, stim):
        self.stimList.append(stim)
        return len(self.stimList)-1

class StimCounter(StimSorter):
    def __init__(self):
        StimSorter.__init__(self)
        self.counts = {}
    
    def update(self, stim):
        i = self.find_stim(stim)
        if i == -1:
            i = self.add_stim(stim)
            self.counts[i] = 1
        else:
            self.counts[i] += 1

class StimTimer(StimSorter):
    def __init__(self, blacklist=['BlankScreenGray','pixel clock']):
        StimSorter.__init__(self)
        self.times = {}
        self.blacklist = blacklist
    
    def process_mw_event(self, event, conv=1./1000000.):
        """
        Process a #stimDisplayUpdate, adding any new stimuli to
        self.stimList and recording the presentation time of any stimuli in
        the dictionary self.times with:
            key : index of stimulus in stimList
            val : list of stimulus times (0=oldest)
        """
        for s in event.value:
            if (not (s is None)) and (not (s['name'] in self.blacklist)):
                stim = Stim(s)
                i = self.find_stim(stim)
                if i == -1:
                    i = self.add_stim(stim)
                    self.times[i] = [event.time * conv,]
                else:
                    if i in self.times.keys():
                        self.times[i].append(event.time * conv)
                    else:
                        #TODO not sure how I got here
                        logging.debug("Unknown stimulus")
                        self.times[i] = [event.time * conv,]
    
    def lookup_stim_for_time(self, time, pre=0.1, post=0.5):
        """
        Lookup what stimulus was on screen at a certain time.
        pre and post define a window around a given stimulus time
        which the stimulus is considered active. So, if the supplied time
        is within (stimTime-pre, stimTime+post) this function will
        return (stim, i) where stim is the active stimulus and i is the
        index of the stimulus within self.stimList
        """
        for i in xrange(len(self.stimList)):
            stim = self.stimList[i]
            # print self.times.keys()
            if i in self.times.keys():
                stimTimes = self.times[i][::-1]
                for stimTime in stimTimes:
                    if time < (stimTime + post) and time > (stimTime - pre):
                        return stim, i, time - stimTime
                    if time >= (stimTime + post):
                        break
                else:
                    logging.debug("Spike encountered for unknown stimulus")
        return None, None, None

class StimSpikeSyncer(StimTimer):
    def __init__(self, channels=range(32), blacklist=['BlankScreenGray','pixel clock']):
        StimTimer.__init__(self, blacklist)
        self.channels = {}
        for c in channels:
            self.channels[c] = {}
    
    def process_spike(self, channel, time):
        stim, stimI, dt = self.lookup_stim_for_time(time)
        if stim == None:
            # this spike does not match any stimuli
            # however, since spike & mw events may come out of order
            # it may match a stim that comes later
            return -1
        if stimI in self.channels[channel].keys():
            self.channels[channel][stimI].append(dt)
        else:
            self.channels[channel][stimI] = [dt,]
        return stimI
    
    def get_stim_spikes(self, channel, stimI):
        if stimI in self.channels[channel].keys():
            return self.channels[channel][stimI]
        else:
            return []
    
    def clear_spikes(self):
        for c in self.channels.keys():
            for sI in self.channels[c].keys():
                self.channels[c][sI] = []
    
    def clear_stimuli(self):
        self.stimList = []
        for c in self.channels.keys():
            self.channels[c] = {}

if __name__ == '__main__':
    import mworks.data as mw
    
    f = mw.MWKFile('K4_110701.mwk')
    f.open()
    
    evCode = '#stimDisplayUpdate'
    evs = f.get_events(codes=[evCode,])
    
    counts = {}
    # stimSorter = StimSorter()
    # stimCounter = StimCounter()
    stimTimer = StimTimer()
    
    for e in evs:
        stimTimer.process_mw_event(e)
        
        # for s in e.value:
        #     if (not (s is None)) and (not (s['name'] in ['BlankScreenGray','pixel clock'])):
        #         stimCounter.update(Stim(s))
        #         # stim = Stim(s)
        #         # i = stimSorter.find_stim(stim)
        #         # if i == -1:
        #         #     i = stimSorter.add_stim(stim)
        #         #     counts[i] = 1
        #         # else:
        #         #     counts[i] += 1
    
    print "Found N Stimuli: %i" % len(stimTimer.times.keys())
    print stimTimer.stimList
    print stimTimer.times.values()