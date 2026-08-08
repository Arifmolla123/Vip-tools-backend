from flask import Blueprint, request, render_template_string
import sqlite3
import os
import time
import threading
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

def get_token():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_config WHERE key='bot_token'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

def set_token(token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value=? WHERE key='bot_token'", (token,))
    conn.commit()
    conn.close()

@bp.route('/setup', methods=['GET','POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if token:
            set_token(token)
            return "<h2>✅ Token Saved! Bot is starting...</h2><a href='/bot/setup'>Back</a>"
    return '''
    <form method="post">
    <input type="text" name="bot_token" placeholder="Enter token" style="width:300px;">
    <button type="submit">Save</button>
    </form>
    '''

# ========== পোলিং লুপ (শুধু requests দিয়ে) ==========
def polling_loop():
    logger.info("🔄 Simple polling loop started")
    last_update_id = 0
    while True:
        token = get_token()
        if not token:
            time.sleep(5)
            continue
        
        try:
            # ১. নতুন মেসেজ চেক করো
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            resp = requests.get(url, params={'offset': last_update_id + 1, 'timeout': 30})
            data = resp.json()
            
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    last_update_id = update['update_id']
                    msg = update.get('message')
                    if msg:
                        chat_id = msg['chat']['id']
                        text = msg.get('text', '')
                        
                        # ২. কমান্ড হ্যান্ডেল করো
                        if text == '/start':
                            reply = "🛡️ Cyber MD Bot is live!\\nSend /help for commands."
                        elif text == '/help':
                            reply = "Commands: /start, /help"
                        else:
                            reply = f"You said: {text}"
                        
                        # ৩. রিপ্লাই পাঠাও
                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                        requests.post(send_url, json={'chat_id': chat_id, 'text': reply})
                        logger.info(f"Replied to {chat_id}: {reply}")
        except Exception as e:
            logger.error(f"Polling error: {e}")
        time.sleep(1)

# ব্যাকগ্রাউন্ডে পোলিং থ্রেড চালু করো
threading.Thread(target=polling_loop, daemon=True).start()
logger.info("✅ Polling thread started (simple version)")
