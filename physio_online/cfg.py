#!/usr/bin/env python

import ConfigParser, io, logging, os

# blank items will be filled in later (in set_session)
# use %% for a % character
CFGDEFAULTS = """
[mworks]
conduitname: server_event_conduit
conv: 0.000001

[pixel clock]
socketTemplate: ipc:///tmp/pixel_clock/%%i
socketStart: 0
socketEnd: 4
maxError: 2

[audio]
socketTemplate: tcp://127.0.0.1:%%i
socketStart: 8000
socketEnd: 8032
sampRate: 44100
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
    
    # def read_session_config(self, session):
    #     filename = '/'.join((self.get('filesystem','datarepo'),session,'physio.ini'))
    #     if os.path.exists(filename):
    #         logging.debug("Found session cfg: %s" % filename)
    #         self.read(filename)
    #     else:
    #         logging.warning('No session cfg found: %s' % filename)
    # 
    # def set_session(self, session):
    #     self.set('session','name',session)
    #     
    #     if self.get('session','dir').strip() == '':
    #         self.set('session','dir','/'.join((self.get('filesystem','datarepo'),session)))
    #     
    #     if self.get('session','output').strip() == '':
    #         self.set('session','output','/'.join((self.get('session','dir'),'processed')))
    #     
    #     if self.get('mworks','file').strip() == '':
    #         self.set('mworks','file','/'.join((self.get('session','dir'),session + self.get('mworks','ext'))))
    #     
    #     if self.get('pixel clock','output').strip() == '':
    #         self.set('pixel clock','output','/'.join((self.get('session','output'),'pixel_clock')))
