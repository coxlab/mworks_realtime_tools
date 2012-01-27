
import pymongo

import flask

app = flask.Flask('dataserver')

conn = pymongo.Connection('soma2.rowland.org')

@app.route('/')
def main():
    return ' '.join(conn.database_names())

@app.route('/<session>')
def load_session(session=None):
    if session in conn.database_names():
        return '%i %i' % (conn[session]['spikes'].count(),\
                conn[session]['mworks'].count())
    else:
        return "", 404

# --- AJAX ---
@app.route('/_get_sessions')
def get_sessions():
    return flask.jsonify(conn.database_names())

@app.route('/_get_recent_time')
def get_recent_time():
    recent_time = conn['mworks'].find({},{'time':1}).sort('time',-1).next()['time']
    print recent_time
    return flask.jsonify({'recent_time': recent_time})

@app.route('/_get_spike_times')
def get_spike_times():
    session_name = flask.request.args.get('session', 'test_999999', type=str)
    session = conn[session_name]
    ch = flask.request.args.get('ch', 1, type=int)
    # TODO timerange
    spike_times = [s['aut'] for s in session['spikes'].find({'ch': ch}, {'time':1})]
    # TODO convert audio to mworks
    return flask.jsonify({'spike_times' : spike_times})

@app.route('/_get_mworks_events')
def get_mworks_events():
    session_name = flask.request.args.get('session', 'test_999999', type=str)
    event_name = flask.request.args.get('event', '#stimDisplayUpdate', type=str)
    times = []
    data = []
    for ev in conn[session_name]['mworks'].find({'name': event_name}, {'time':1,'data':1}):
        times.append(ev['time'])
        data.append(ev['data'])
    return flask.jsonify({'times': times, 'data': data})

@app.route('/_get_available_events')
def get_available_event_names():
    session_name = flask.request.args.get('session', 'test_999999', type=str)
    event_names = conn[session_name]['mworks'].find({},{'name':1}).distinct('name')
    return flask.jsonify({'names': event_names})

@app.route('/_get_stimuli')
def get_stimuli():
    # a note of caution here
    # because I'm using monogod < 1.3 ... I don't have the requires $elemMatch
    # so, querying for stimuli/trials is a bit difficult
    # see here for why: http://www.mongodb.org/display/DOCS/Dot+Notation+%28Reaching+into+Objects%29#DotNotation%28ReachingintoObjects%29-ArrayElementbyPosition
    # because there is 1 stimulus on screen, I can probably take shortcuts, but for now, upgrade the server
    # example:
    #c = mworks.find({'data.name': 'BlueSquare', 'data.pos_x': -25, 'data.pos_y': -5})
    # will find all stim update events where there was a Bluesquare, a stimulus at pos_x and a stim at pos_y
    # these could be the same stimulus or different (one bluesquare at -10, a different stim at -25x etc...)
    pass

if __name__ == '__main__':
    app.run(debug=True)
