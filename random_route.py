from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_socketio import emit
import base64
from main import socketio

bp = Blueprint('random_route', __name__, url_prefix='/random')

ADMIN_PASSWORD = 'admin123'

# clients এখন IP-ভিত্তিক
clients = {}        # key = ip, value = {id, ip, ua, location, frame, audio, sids}
viewers = set()     # sids যারা 'ready' পাঠিয়েছে
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

# ========== Socket.IO ইভেন্ট (IP-ভিত্তিক) ==========
@socketio.on('connect')
def handle_connect():
    # X-Forwarded-For থেকে প্রথম IP টা নাও
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    ua = request.headers.get('User-Agent')
    
    if ip not in clients:
        clients[ip] = {
            'id': ip,
            'ip': ip,
            'user_agent': ua,
            'location': None,
            'last_frame': None,
            'audio_level': 0,
            'sids': [request.sid]   # এই IP-র সব সিডি
        }
    else:
        # IP আগে থেকেই আছে, নতুন সিডি যোগ করো
        if request.sid not in clients[ip]['sids']:
            clients[ip]['sids'].append(request.sid)
    
    if session.get('admin_logged_in'):
        admin_sids.add(request.sid)
        emit('admin_update', {ip: clients[ip]}, to=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    # কোন IP-র সিডি ডিসকানেক্ট হয়েছে সেটা খুঁজি
    for ip, data in list(clients.items()):
        if request.sid in data['sids']:
            data['sids'].remove(request.sid)
            if not data['sids']:   # কোনো সিডি না থাকলে IP-টি ডিলিট
                del clients[ip]
            break
    emit_clients_except_self()
    if admin_sids:
        emit('admin_update', clients, to=list(admin_sids))

@socketio.on('ready')
def handle_ready():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if ip in clients:
        viewers.add(request.sid)
        emit_clients_except_self(to=request.sid)
        for v in viewers:
            if v != request.sid:
                emit_clients_except_self(to=v)
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

@socketio.on('location_update')
def handle_location(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if ip in clients:
        clients[ip]['location'] = data
        emit_clients_except_self()
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

@socketio.on('video_frame')
def handle_video(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if ip in clients:
        clients[ip]['last_frame'] = data.get('image')
        clients[ip]['audio_level'] = data.get('audio_volume', 0)
        emit_clients_except_self()
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

def emit_clients_except_self(to=None):
    target_list = [to] if to else list(viewers)
    for target in target_list:
        # টার্গেটের IP বের করো
        target_ip = None
        for ip, data in clients.items():
            if target in data['sids']:
                target_ip = ip
                break
        # নিজের IP বাদ দিয়ে বাকি IP-গুলো পাঠাও
        filtered = {ip: data for ip, data in clients.items() if ip != target_ip}
        emit('clients_update', filtered, to=target)
