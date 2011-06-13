from mworks.conduit import *
import time, sys

client = IPCClientConduit("python_bridge_plugin_conduit")


def hello_x(evt):
    print("got evt")
    print("evt.code = %i" % evt.code)
    print("evt.data = %d" % evt.data)
    print("evt.time = %i" % evt.time)
    

client.initialize()

client.register_callback_for_name("x", hello_x)
time.sleep(0.2)

while True:
    pass  # probably should looks for a keypress or something


server.finalize()
client.finalize()
