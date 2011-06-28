#!/usr/bin/env python

import copy, logging, time

from threading import Condition

import numpy as np

from mworks.conduit import IPCClientConduit as Conduit

from pixel_clock_info_pb2 import PixelClockInfoBuffer

def state_to_code(state):
    """
    state[0] = lsb, state[-1] = msb
    """
    code = 0
    for i in xrange(len(state)):
        code += (state[i] << i)
    return code

class MWPixelClock(object):
    def __init__(self, conduitName):
        self.conduit = Conduit(conduitName)
        self.conduit.initialize()
        self.conduit.register_local_event_code(0,'#stimDisplayUpdate')
        self.conduit.register_callback_for_name('#stimDisplayUpdate', self.receive_event)
        self.codes = []
        self.cond = Condition()
        self.maxCodes = 100
    
    def receive_event(self, event):
        for s in event.data:
            if s.has_key('bit_code'):
                self.cond.acquire()
                self.codes.append((s['bit_code'],event.time/1000000.))
                # if len(self.codes) > 2:
                #     #logging.debug('MW bit_code = %i' % s['bit_code'])
                #     #print s['bit_code']
                #     #logging.debug("MW Delta: %s" % delta_code(self.codes[-1][0], self.codes[-2][0]))
                while len(self.codes) > self.maxCodes:
                    self.codes.pop(0)
                self.cond.notifyAll()
                self.cond.release()
    
    def get_codes(self):
        self.cond.acquire()
        codes = copy.deepcopy(self.codes)
        self.cond.release()
        return codes

class AudioPixelClock(object):
    def __init__(self, pathFunc, channelIndices, zmqContext=None):
        if zmqContext == None:
            zmqContext = zmq.Context()
        
        self.socket = zmqContext.socket(zmq.SUB)
        for i in channelIndices:
            self.socket.connect(pathFunc(i))
        self.socket.setsockopt(zmq.SUBSCRIBE,"")
        self._mb = PixelClockInfoBuffer()
        
        self.codes = []
        self.state = [0,0,0,0]
        self.maxCodes = 100
        
        self.minEventTime = 0.01 * 44100
        self.lastEventTime = -minEventTime
    
    def update(self):
        try:
            packet = self.socket.recv(zmq.NOBLOCK)
            self._mb.ParseFromString(packet)
            self.process_msg(self._mb)
        except:
            return
    
    def offset_time(self, time, channel_id):
        """
        This function is here to offset of a given event based on it's position on the screen.
        The resulting time should correspond to the END of the screen refresh
        """
        return time
    
    def process_msg(self, mb):
        self.state[mb.channel_id] = mb.direction
        if abs(mw.time_stamp - self.lastEventTime) > self.minEventTime:
            self.codes.append((self.lastEventTime, state_to_code(self.state)))
            while len(self.codes) > self.maxCodes:
                self.codes.pop(0)
            self.lastEventTime = self.offset_time(mb.time_stamp, mb.channel_id)

def time_match_mw_with_pc(pc_codes, pc_times, mw_codes, mw_times,
                                submatch_size = 10, slack = 0, max_slack=10,
                                pc_check_stride = 100, pc_file_offset= 0):

    time_matches = []

    for pc_start_index in range(0, len(pc_codes)-submatch_size, pc_check_stride):
        match_sequence = pc_codes[pc_start_index:pc_start_index+submatch_size]
        pc_time = pc_times[pc_start_index]

        for i in range(0, len(mw_codes) - submatch_size - max_slack):
            good_flag = True

            total_slack = 0
            for j in range(0, submatch_size):
                target = match_sequence[j]
                if target != mw_codes[i+j+total_slack]:
                    slack_match = False
                    slack_count = 0
                    while slack_count < slack and j != 0:
                        slack_count += 1
                        total_slack += 1
                        if target == mw_codes[i+j+total_slack]:
                            slack_match = True
                            break

                    if total_slack > max_slack:
                        good_flag = False
                        break

                    if not slack_match:
                        # didn't find a match within slack
                        good_flag = False
                        break

            if good_flag:
                logging.info("Total slack: %d" % total_slack)
                logging.info("%s matched to %s" % \
                      (match_sequence, mw_codes[i:i+submatch_size+total_slack]))
                time_matches.append((pc_time, mw_times[i]))
                break

    # print time_matches
    return time_matches

def find_matches(auCodes, mwCodes):
    auC = [au[1] for au in auCodes]
    auT = [au[0] for au in auCodes]
    mwC = [mw[1] for mw in mwCodes]
    mwT = [mw[0] for mw in mwCodes]
    
    return time_match_mw_with_pc(auC,auT,mwC,mwT)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    conduitName = 'server_event_conduit'
    mwPC = MWPixelClock(conduitName)
    
    #pathFunc = lambda i : "tcp://127.0.0.1:%i" % (i+8000) 
    pathFunc = lambda i : "ipc:///tmp/pixel_clock/%i" % i
    auPC = AudioPixelClock(pathFunc, range(4))
    
    minLength = 10
    
    while 1:
        mwCodes = mwPC.get_codes()
        auPC.update()
        auCodes = auPC.codes
        
        if (len(mwCodes) > minLength) and (len(auCodes) > minLength)):
            match = find_matches(auCodes, mwCodes)
        
        time.sleep(0.001)