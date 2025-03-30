import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Room chung cho tất cả client
ROOM = 'heart_room'
# Lưu trữ thông tin client: SID -> {'position': 'left'/'right', 'connect_time': float}
clients = {}
# Lưu trạng thái hold: SID -> timestamp (float) hoặc None nếu không đang hold
hold_states = {}
# Lưu vị trí trái tim của client
heart_positions = {}

# Ngưỡng thời gian (giây) để xem 2 tín hiệu hold có xảy ra gần nhau không
TIME_THRESHOLD = 2.0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    join_room(ROOM)
    sid = request.sid
    # Gán vị trí trái tim dựa vào thứ tự kết nối
    if len(clients) == 0:
        heart_positions[sid] = 'left'
    elif len(clients) == 1:
        heart_positions[sid] = 'right'
    else:
        heart_positions[sid] = None
    clients[sid] = {
        'position': heart_positions.get(sid),
        'connect_time': time.time()
    }
    hold_states[sid] = None  # Ban đầu không hold
    emit('position_assigned', {'position': clients[sid]['position']})
    print(f"Client {sid} connected; position: {clients[sid]['position']}")

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    leave_room(ROOM)
    if sid in clients:
        del clients[sid]
    if sid in hold_states:
        del hold_states[sid]
    if sid in heart_positions:
        del heart_positions[sid]
    print(f"Client {sid} disconnected")

@socketio.on('hold')
def handle_hold():
    sid = request.sid
    # Lưu thời điểm hold
    hold_states[sid] = time.time()
    print(f"Client {sid} is holding at {hold_states[sid]}")
    check_heart_completion()

@socketio.on('release')
def handle_release():
    sid = request.sid
    hold_states[sid] = None
    emit('hide_half_heart', {}, room=sid)
    print(f"Client {sid} released hold")

def check_heart_completion():
    # Lấy danh sách các hold đang hoạt động với timestamp
    active_holds = [(sid, t) for sid, t in hold_states.items() if t is not None]
    if len(active_holds) >= 2:
        # Sắp xếp theo thời gian hold mới nhất
        sorted_holds = sorted(active_holds, key=lambda x: x[1], reverse=True)[:2]
        time_diff = abs(sorted_holds[0][1] - sorted_holds[1][1])
        print(f"Time diff between holds: {time_diff} seconds")
        if time_diff <= TIME_THRESHOLD:
            emit('show_complete_heart', {'message': 'Trái tim đã ghép thành công!'}, room=ROOM)
            # Reset trạng thái hold cho các client đã hold
            for sid, _ in active_holds:
                hold_states[sid] = None
            emit('hide_half_heart', {}, room=ROOM)

if __name__ == '__main__':
    socketio.run(app, debug=True)
