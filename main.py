from flask import Flask
import importlib

app = Flask(__name__)

files = ['cyber_bomber', 'cyber_phis', 'cyber_spy']
for file in files:
    module = importlib.import_module(file)
    if hasattr(module, 'bp'):
        app.register_blueprint(module.bp)

@app.route('/')
def home():
    return {'status': 'online', 'tools': ['/bomber', '/phis', '/spy']}

@app.route('/ping')
def ping():
    from datetime import datetime
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
