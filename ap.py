from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import time
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Room configuration
ROOM = 'heart_room'
clients = {}
hold_states = {}
heart_positions = {}

TIME_THRESHOLD = 2.0

@app.route('/')
def index():
    return "Heart Connection Server"

@socketio.on('connect')
def handle_connect():
    join_room(ROOM)
    sid = request.sid
    
    # Assign position based on connection order
    if len(clients) == 0:
        heart_positions[sid] = 'left'
    elif len(clients) == 1:
        heart_positions[sid] = 'right'
    else:
        heart_positions[sid] = None
    
    clients[sid] = {'position': heart_positions.get(sid)}
    hold_states[sid] = False
    emit('position_assigned', {'position': clients[sid]['position']})

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    leave_room(ROOM)
    if sid in clients:
        del clients[sid]
    if sid in hold_states:
        del hold_states[sid]

@socketio.on('hold')
def handle_hold():
    sid = request.sid
    hold_states[sid] = True
    check_heart_completion()

@socketio.on('release')
def handle_release():
    sid = request.sid
    hold_states[sid] = False
    emit('hide_half_heart', room=sid)

def check_heart_completion():
    current_time = time.time()
    active_holds = [sid for sid, state in hold_states.items() if state]
    
    if len(active_holds) >= 2:
        # Get the two most recent holds
        sorted_holds = sorted(
            [(sid, clients[sid]['connect_time']) for sid in active_holds],
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        if abs(sorted_holds[0][1] - sorted_holds[1][1]) <= TIME_THRESHOLD:
            emit('show_complete_heart', room=ROOM)
            # Reset states
            for sid in active_holds:
                hold_states[sid] = False
            emit('hide_half_heart', room=ROOM)

if __name__ == '__main__':
    socketio.run(app)
