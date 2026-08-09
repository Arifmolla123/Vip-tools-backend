from flask import Blueprint, render_template, request, session, redirect, url_for, current_app
from flask_socketio import emit
import base64

bp = Blueprint('random', __name__, url_prefix='/random')

ADMIN_PASSWORD = 'admin123'

clients = {}
viewers = set()
admin_sids = set()

@bp.route('/')
def index():
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

# ========== Socket.IO ইভেন্ট (current_app.socketio ব্যবহার করে) ==========
# আমরা ফাংশন ডেফিনেশনের সময় socketio পাই না, তাই ইভেন্টগুলো রেজিস্টার করার জন্য
# আমরা নিচে একটি ফাংশন তৈরি করেছি যা main.py থেকে কল হবে।
# কিন্তু যেহেতু আমরা main.py-তে কোনো অতিরিক্ত কল করতে চাই না, তাই আমরা
# main.py-তে socketio ডিফাইন করার পর random.py লোড হয়, তাই আমরা সরাসরি
# main.socketio ইম্পোর্ট করতে পারি। কিন্তু আমি সার্কুলার ইম্পোর্ট এড়াতে
# current_app ব্যবহার করছি।

# এখানে ইভেন্টগুলো রেজিস্টার করার ফাংশন নেই, কারণ আমরা চাই main.py থেকে
# কোনো কল না করতে। তাই আমি বিকল্প পদ্ধতি ব্যবহার করছি:
# random.py-তে আমরা main.py-তে ডিফাইন করা socketio ইম্পোর্ট করব,
# কিন্তু সার্কুলার ইম্পোর্ট এড়াতে আমরা main.py থেকে socketio ইম্পোর্ট করব
# যখন ইভেন্টগুলো ডেকোরেটর হিসেবে অ্যাটাচ করব। তবে ডেকোরেটরগুলো মডিউল লোডের
# সময় এক্সিকিউট হয়, তাই main.socketio ইম্পোর্ট করা যায় যদি main.py ইতিমধ্যে
# socketio ডিফাইন করে থাকে। যেহেতু main.py আগে লোড হয় (কারণ আমরা main.py
# থেকে random ইম্পোর্ট করি), তাই main.socketio ডিফাইন হওয়া উচিত।

# কিন্তু ডেকোরেটর ব্যবহারের সময় main.socketio অ্যাক্সেস করা যায়। আমি নিচে
# ডেকোরেটর ব্যবহার করছি main.socketio দিয়ে।

import main   # main মডিউল ইম্পোর্ট (এখন main.py লোড হওয়ার পর random লোড হয়)

@main.socketio.on('connect')
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

@main.socketio.on('disconnect')
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

@main.socketio.on('ready')
def handle_ready():
    if request.sid in clients:
        viewers.add(request.sid)
        emit_clients_except_self(to=request.sid)
        for v in viewers:
            if v != request.sid:
                emit_clients_except_self(to=v)
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

@main.socketio.on('location_update')
def handle_location(data):
    if request.sid in clients:
        clients[request.sid]['location'] = data
        emit_clients_except_self()
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

@main.socketio.on('video_frame')
def handle_video(data):
    if request.sid in clients:
        clients[request.sid]['last_frame'] = data.get('image')
        clients[request.sid]['audio_level'] = data.get('audio_volume', 0)
        emit_clients_except_self()
        if admin_sids:
            emit('admin_update', clients, to=list(admin_sids))

def emit_clients_except_self(to=None):
    target_list = [to] if to else list(viewers)
    for target in target_list:
        filtered = {sid: data for sid, data in clients.items() if sid != target}
        emit('clients_update', filtered, to=target)
