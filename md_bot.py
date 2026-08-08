from flask import Blueprint, request, redirect, url_for, render_template_string
import sqlite3
import time
import threading
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')

# ========== আপনার টোকেন (সঠিক) ==========
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1Lcpus1Z2iz6kOORo"
BOT_LINK = "https://t.me/Arif1222_bot"
DB_PATH = '/tmp/phish_data.db'

# ========== ডেটাবেস ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('auto_react', 'off')")
    conn.commit()
    conn.close()
init_db()

def get_auto_react():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value FROM bot_config WHERE key='auto_react'")
        row = c.fetchone()
        conn.close()
        return row[0] if row else 'off'
    except:
        return 'off'

def set_auto_react(status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value=? WHERE key='auto_react'", (status,))
    conn.commit()
    conn.close()

# ========== ড্যাশবোর্ড ==========
@bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        status = request.form.get('auto_react', 'off')
        set_auto_react(status)
        logger.info(f"🔄 Auto-react set to: {status}")
        return redirect(url_for('md_bot.dashboard'))
    
    is_on = get_auto_react() == 'on'
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyber Tools MD</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        body { background:#0d1117; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
        .card { background:#161b22; border-radius:28px; padding:30px 24px; max-width:400px; width:100%; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid #30363d; }
        .icon { background:#1f6feb; width:64px; height:64px; border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:32px; margin-bottom:16px; }
        h1 { font-size:24px; font-weight:600; color:#f0f6fc; margin-bottom:4px; }
        .sub { color:#8b949e; font-size:14px; margin-bottom:24px; }
        .badge { display:inline-block; background:#238636; color:#fff; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:500; margin-bottom:20px; }
        .btn { display:block; background:#1f6feb; color:#fff; text-align:center; padding:14px; border-radius:14px; font-size:17px; font-weight:600; text-decoration:none; margin-bottom:24px; }
        .btn:hover { background:#388bfd; }
        .divider { border:none; border-top:1px solid #30363d; margin:20px 0; }
        .toggle { display:flex; justify-content:space-between; align-items:center; background:#0d1117; padding:12px 16px; border-radius:14px; margin-bottom:8px; }
        .toggle-label { color:#c9d1d9; font-size:16px; font-weight:500; }
        .options { display:flex; gap:12px; }
        .options label { color:#8b949e; font-size:15px; display:flex; align-items:center; gap:6px; cursor:pointer; }
        .options input[type="radio"] { accent-color:#1f6feb; width:18px; height:18px; cursor:pointer; }
        .save { width:100%; background:#238636; color:#fff; border:none; padding:14px; border-radius:14px; font-size:17px; font-weight:600; cursor:pointer; margin-top:12px; }
        .save:hover { background:#2ea043; }
        .footer { text-align:center; color:#484f58; font-size:12px; margin-top:20px; }
    </style>
    </head>
    <body>
    <div class="card">
        <div class="icon">🛡️</div>
        <h1>Cyber Tools MD</h1>
        <div class="sub">Bot Control</div>
        <div class="badge">● Active</div>
        <a href="https://t.me/Arif1222_bot" target="_blank" class="btn">📱 Open Bot</a>
        <hr class="divider">
        <form method="post">
            <div class="toggle">
                <span class="toggle-label">Auto React</span>
                <div class="options">
                    <label><input type="radio" name="auto_react" value="on" {{ "checked" if is_on else "" }}> ON</label>
                    <label><input type="radio" name="auto_react" value="off" {{ "checked" if not is_on else "" }}> OFF</label>
                </div>
            </div>
            <button type="submit" class="save">Save Settings</button>
        </form>
        <div class="footer">Token hidden</div>
    </div>
    </body>
    </html>
    ''', is_on=is_on)

# ========== রিয়েক্ট ফাংশন (ডাইরেক্ট টোকেন) ==========
def send_reactions(chat_id, message_id):
    status = get_auto_react()
    if status != 'on':
        return
    
    emojis = ["❤️", "🔥", "👍", "🎉", "😂", "😍", "👏", "💯", "🤩", "🥳", "✨"]
    try:
        reaction_list = [{"type": "emoji", "emoji": e} for e in emojis]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps(reaction_list)
        }
        r = requests.post(url, json=payload, timeout=5)
        if r.json().get('ok'):
            logger.info(f"✅ 11 reactions sent to {message_id}")
        else:
            logger.error(f"❌ React error: {r.text}")
    except Exception as e:
        logger.error(f"❌ Exception: {e}")

# ========== কমান্ড ==========
def handle_commands(msg):
    text = msg.get('text', '')
    if not text.startswith('/'):
        return
    chat_id = msg['chat']['id']
    reply = None

    if text == '/start':
        reply = """<b>🛡️ Cyber MD Bot is LIVE!</b> 🚀

<b>📝 Commands:</b>
/bold [text] - <b>Bold</b>
/italic [text] - <i>Italic</i>
/code [text] - <code>Code</code>
/strike [text] - <s>Strike</s>
/echo [text] - All formats

<b>⚙️ Dashboard:</b>
/bot/dashboard - Control auto‑react

<b>👋 Welcome:</b>
I welcome new members automatically."""
    elif text == '/help':
        reply = "Send /start to see commands."
    elif text.startswith('/bold '):
        reply = f"<b>{text[6:]}</b>"
    elif text.startswith('/italic '):
        reply = f"<i>{text[8:]}</i>"
    elif text.startswith('/code '):
        reply = f"<code>{text[6:]}</code>"
    elif text.startswith('/strike '):
        reply = f"<s>{text[8:]}</s>"
    elif text.startswith('/echo '):
        reply = f"<b>{text[6:]}</b>, <code>code</code>, <s>strike</s>"
    elif text == '/testreact':
        # টেস্ট কমান্ড: জোর করে ১টি রিয়েক্ট পাঠাই
        send_reactions(msg['chat']['id'], msg['message_id'])
        reply = "✅ Test reaction sent (👍) to this message!"

    if reply:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={
                'chat_id': chat_id,
                'text': reply,
                'parse_mode': 'HTML'
            }, timeout=5)
            if r.json().get('ok'):
                logger.info(f"✅ Replied to {chat_id}")
            else:
                logger.error(f"❌ Send failed: {r.text}")
        except Exception as e:
            logger.error(f"Send error: {e}")

# ========== ওয়েলকাম ==========
def handle_welcome(msg):
    if 'new_chat_members' not in msg:
        return
    chat_id = msg['chat']['id']
    for member in msg['new_chat_members']:
        name = member.get('first_name', 'Guest')
        logger.info(f"👤 New member: {name}")
        welcome = f"<b>🎉 Welcome {name}!</b> 🥳\nGlad to have you here. Type /start to see what I can do."
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={
                'chat_id': chat_id,
                'text': welcome,
                'parse_mode': 'HTML'
            }, timeout=5)
            if r.json().get('ok'):
                logger.info(f"✅ Welcome sent to {name}")
            else:
                logger.error(f"❌ Welcome failed: {r.text}")
        except Exception as e:
            logger.error(f"Welcome error: {e}")

# ========== পোলিং ==========
def polling_worker():
    logger.info("🔄 Polling started.")
    last_update_id = 0
    while True:
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
        except:
            pass
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={'offset': last_update_id + 1, 'timeout': 30}
            )
            data = resp.json()
            if not data.get('ok'):
                logger.error(f"API error: {data}")
                time.sleep(5)
                continue
            for update in data.get('result', []):
                last_update_id = update['update_id']
                msg = update.get('message')
                if not msg:
                    continue
                logger.info(f"📩 Msg: {msg.get('text', '')}")
                send_reactions(msg['chat']['id'], msg['message_id'])
                handle_commands(msg)
                handle_welcome(msg)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

threading.Thread(target=polling_worker, daemon=True).start()
logger.info("🚀 Bot started.")
