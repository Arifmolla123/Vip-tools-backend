from flask import Blueprint, request, render_template_string
import os
import sqlite3
import time
import threading
import requests
import logging
import json

# ========== লগিং সেটআপ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

# ========== ডেটাবেস (শুধু টোকেন রাখার জন্য) ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('bot_token', '')")
    conn.commit()
    conn.close()
init_db()

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

# ========== ওয়েব সেটআপ পেজ (টোকেন দেওয়ার ফর্ম) ==========
@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if not token:
            return "<h2 style='color:red;'>❌ Token cannot be empty!</h2><a href='/bot/setup'>Try Again</a>"
        
        # ১. টোকেন সেভ করো
        set_token(token)
        logger.info("✅ Token saved to database.")
        
        # ২. টোকেন ভ্যালিড কিনা চেক করো (getMe)
        try:
            me = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if not me.json().get('ok'):
                return f"<h2 style='color:red;'>❌ Invalid Token! Telegram says: {me.json()}</h2><a href='/bot/setup'>Try Again</a>"
        except Exception as e:
            return f"<h2 style='color:red;'>❌ Network Error checking token: {e}</h2><a href='/bot/setup'>Try Again</a>"
        
        logger.info("✅ Token validated with Telegram API.")
        
        # ৩. ইউজারের কাছে লাইভ মেসেজ পাঠানোর চেষ্টা (যদি আগে থেকে বটে মেসেজ দিয়ে থাকে)
        try:
            updates = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params={'limit': 1}, timeout=5)
            if updates.json().get('ok') and updates.json().get('result'):
                chat_id = updates.json()['result'][0]['message']['chat']['id']
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                              json={'chat_id': chat_id, 'text': '🛡️ *Cyber MD Bot is LIVE!* 🚀\nType /start to begin.', 'parse_mode': 'MarkdownV2'})
                logger.info(f"✅ Live notification sent to chat {chat_id}")
        except Exception as e:
            logger.warning(f"Could not send live notification (user may not have started bot yet): {e}")
        
        return f"""
        <h2 style='color:green;'>✅ Setup Complete!</h2>
        <p>Token: <code>{token[:10]}...</code></p>
        <p>Now go to your Telegram bot and type <code>/start</code>.</p>
        <p><strong>Check Render Logs for live updates!</strong></p>
        <a href='/bot/setup'>Go Back</a>
        """
    
    current = get_token()
    return f"""
    <!DOCTYPE html>
    <html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;background:#0d1117;color:#c9d1d9;padding:20px;border-radius:10px;">
    <h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
    <h3>🤖 Bot Setup</h3>
    {'<p style="color:#3fb950;">✅ Token already saved. Enter new one to update:</p>' if current else '<p>Paste your token from @BotFather:</p>'}
    <form method="post">
    <input type="text" name="bot_token" placeholder="e.g. 123456:ABC-DEF" style="width:100%;padding:10px;background:#161b22;color:#fff;border:1px solid #30363d;border-radius:6px;">
    <button type="submit" style="margin-top:10px;background:#238636;color:#fff;padding:10px 20px;border:0;border-radius:6px;cursor:pointer;">Save & Activate</button>
    </form>
    </body></html>
    """

# ==========================================================
# ========== পোলিং ইঞ্জিন (এটাই বটের মূল প্রাণ) ==========
# ==========================================================
def polling_worker():
    logger.info("🔄 [WORKER] Polling thread started.")
    last_update_id = 0
    
    while True:
        token = get_token()
        if not token:
            time.sleep(5)
            continue
        
        # ১. প্রথমেই কনফ্লিক্ট এড়াতে ওয়েবহুক ডিলিট করে নাও
        try:
            del_resp = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=5)
            if del_resp.json().get('ok'):
                # শুধু একবার লগ করলেই হয়, তাই প্রতিবার না করে শর্ত দিই
                pass 
        except:
            pass

        try:
            # ২. নতুন আপডেট চেক করো
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            resp = requests.get(url, params={'offset': last_update_id + 1, 'timeout': 30})
            data = resp.json()
            
            if not data.get('ok'):
                logger.error(f"API Error: {data}")
                time.sleep(5)
                continue
            
            if data.get('result'):
                for update in data['result']:
                    last_update_id = update['update_id']
                    msg = update.get('message')
                    if not msg:
                        continue
                    
                    chat_id = msg['chat']['id']
                    text = msg.get('text', '')
                    username = msg['from'].get('username', 'Unknown')
                    
                    logger.info(f"📩 Received: '{text}' from {username} (Chat: {chat_id})")
                    
                    # ৩. কমান্ড প্রসেস করো
                    reply = None
                    if text == '/start':
                        reply = """🛡️ *Cyber MD Bot is LIVE!* 🚀

I am your Markdown formatting bot.

*Commands:*
/bold [text] - **Bold**
/italic [text] - _Italic_
/code [text] - `Code`
/strike [text] - ~Strike~
/echo [text] - All formats
/help - This message

*Web Tools:* /bot/md/preview (if installed)"""
                    
                    elif text == '/help':
                        reply = "Send /start to see all commands."
                    
                    elif text.startswith('/bold '):
                        reply = f"*{text[6:]}*"
                    elif text.startswith('/italic '):
                        reply = f"_{text[8:]}_"
                    elif text.startswith('/code '):
                        reply = f"`{text[6:]}`"
                    elif text.startswith('/strike '):
                        reply = f"~{text[8:]}~"
                    elif text.startswith('/echo '):
                        reply = f"*{text[6:]}*, `code`, ~strike~"
                    else:
                        # ফাঁকা বা অচেনা মেসেজ
                        pass
                    
                    # ৪. রিপ্লাই পাঠাও (যদি থাকে)
                    if reply:
                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                        r = requests.post(send_url, json={
                            'chat_id': chat_id,
                            'text': reply,
                            'parse_mode': 'MarkdownV2'
                        }, timeout=5)
                        if r.json().get('ok'):
                            logger.info(f"✅ Replied to {chat_id}")
                        else:
                            logger.error(f"❌ Failed to send: {r.text}")
            
            # স্লিপ না করে দ্রুত রেসপন্স দিতে ১ সেকেন্ড ওয়েট
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"⚠️ Polling loop error: {e}")
            time.sleep(5)

# ========== পোলিং থ্রেড চালু করো (Flask এর সাথে) ==========
polling_thread = threading.Thread(target=polling_worker, daemon=True)
polling_thread.start()
logger.info("🚀 [MAIN] Polling worker thread launched.")

# ========== (অপশনাল) md_tools লোড করো ==========
try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)
    bp.register_blueprint(converter.bp)
    bp.register_blueprint(formatter.bp)
    logger.info("✅ md_tools loaded successfully.")
except ImportError:
    logger.warning("⚠️ md_tools not found (web tools will be unavailable).")
