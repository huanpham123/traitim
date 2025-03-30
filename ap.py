import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Dùng một room chung cho tất cả các client
ROOM = 'heart_room'
# Lưu trạng thái tín hiệu nửa trái tim: dict mapping ROOM -> list of (sid, timestamp)
half_hearts = {}

# Thời gian cho phép giữa 2 tín hiệu (giây)
TIME_THRESHOLD = 2.0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    join_room(ROOM)
    print(f"Client {request.sid} connected and joined room {ROOM}")

@socketio.on('disconnect')
def handle_disconnect():
    leave_room(ROOM)
    if ROOM in half_hearts:
        # Loại bỏ SID của client bị disconnect
        half_hearts[ROOM] = [(sid, ts) for (sid, ts) in half_hearts[ROOM] if sid != request.sid]
    print(f"Client {request.sid} disconnected")

@socketio.on('half_heart')
def handle_half_heart(data):
    global half_hearts
    current_time = time.time()
    if ROOM not in half_hearts:
        half_hearts[ROOM] = []
    # Loại bỏ những tín hiệu cũ hơn TIME_THRESHOLD giây
    half_hearts[ROOM] = [(sid, ts) for (sid, ts) in half_hearts[ROOM] if current_time - ts <= TIME_THRESHOLD]
    # Thêm tín hiệu hiện tại
    half_hearts[ROOM].append((request.sid, current_time))
    print(f"Received half heart from {request.sid}, list: {half_hearts[ROOM]}")
    
    # Nếu có đủ 2 thiết bị (2 SID khác nhau) gửi tín hiệu trong khoảng thời gian cho phép
    unique_sids = {sid for (sid, ts) in half_hearts[ROOM]}
    if len(unique_sids) >= 2:
        socketio.emit('complete_heart', {'message': 'Trái tim đã ghép thành công!'}, room=ROOM)
        # Reset danh sách tín hiệu cho lần ghép tiếp theo
        half_hearts[ROOM] = []

if __name__ == '__main__':
    socketio.run(app, debug=True)
