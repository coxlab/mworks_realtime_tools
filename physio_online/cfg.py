#!/usr/bin/env python

import ConfigParser, io, logging, os

# blank items will be filled in later (in set_session)
# use %% for a % character
CFGDEFAULTS = """
[mworks]
conduitname: server_event_conduit
eventnames: #stimDisplayUpdate, #pixelClockOffset

[audio]
socketTemplate: tcp://127.0.0.1:%%i
socketStart: 8000
socketEnd: 8032
sampling_rate: 44100

[mongo]
hostname: soma2.rowland.org
database: test_999999
spike_collection: spikes
mworks_collection: mworks
"""

class Config(ConfigParser.SafeConfigParser):
    def __init__(self, *args, **kwargs):
        ConfigParser.SafeConfigParser.__init__(self, *args, **kwargs)
        # read in defaults
        self.readfp(io.BytesIO(CFGDEFAULTS))
    
    def read_user_config(self, homeDir=os.getenv('HOME')):
        filename = '/'.join((homeDir,'.physio_online'))
        if os.path.exists(filename):
            logging.debug("Found user cfg: %s" % filename)
            self.read(filename)
        else:
            logging.warning('No user cfg found: %s' % filename)

    def getlist(self, section, option, delimiter=','):
        list_string = self.get(section, option)
        return [s.strip() for s in list_string.split(delimiter)]
