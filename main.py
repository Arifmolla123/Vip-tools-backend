from flask import Flask
import importlib
import os
from cyber_phis import init_db
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key-2026')

init_db()

# ========== SocketIO ==========
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
app.socketio = socketio

# ========== বাকি ব্লুপ্রিন্ট ==========
files = ['hard_bomber', 'cyber_phis', 'cyber_spy', 'support', 'md_bot', 'random_route']
for file in files:
    try:
        module = importlib.import_module(file)
        if hasattr(module, 'bp'):
            app.register_blueprint(module.bp)
            print(f"✅ {file} ব্লুপ্রিন্ট রেজিস্টার হয়েছে")
    except ModuleNotFoundError:
        print(f"⚠️ {file}.py নেই – স্কিপ")

@app.route('/')
def home():
    return {'status': 'online', 'tools': ['/hard_bomber', '/phis', '/spy', '/support', '/bot', '/random']}

@app.route('/ping')
def ping():
    from datetime import datetime
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
