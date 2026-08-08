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
DB_PATH = '/tmp/phish_data.db'

# ========== ডেটাবেস ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('bot_token', '')")
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('auto_react', 'off')")
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('auto_welcome', 'off')")
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('auto_reply', 'off')")
    conn.commit()
    conn.close()
init_db()

def get_config(key):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value FROM bot_config WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else ''
    except:
        return ''

def set_config(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def get_token():
    return get_config('bot_token')

def set_token(token):
    set_config('bot_token', token)

# ========== থ্রেড ট্র্যাকিং ==========
polling_started = False

# ========== অটো রিপ্লাই ==========
AUTO_REPLIES = {
    'hi': '<b>Hello!</b> <i>How are you?</i> 😊',
    'hello': '<b>Hello!</b> <i>How can I help?</i>',
    'good morning': '<b>🌅 Good Morning!</b> Have a great day!',
    'good night': '<b>🌙 Good Night!</b> Sleep well!',
    'how are you': '<i>I\'m just a bot, but I\'m doing fine!</i> 😄',
}

# ========== রাউট ==========
@bp.route('/', methods=['GET', 'POST'])
def setup_or_dashboard():
    token = get_token()
    if not token:
        if request.method == 'POST':
            new_token = request.form.get('bot_token', '').strip()
            if new_token:
                try:
                    r = requests.get(f"https://api.telegram.org/bot{new_token}/getMe", timeout=5)
                    if r.json().get('ok'):
                        set_token(new_token)
                        start_polling_thread()
                        return redirect(url_for('md_bot.setup_or_dashboard'))
                    else:
                        error = "❌ Invalid token."
                except Exception as e:
                    error = f"❌ Error: {e}"
            else:
                error = "❌ Token cannot be empty."
            return render_template_string(SETUP_HTML, error=error)
        return render_template_string(SETUP_HTML, error=None)
    else:
        if request.method == 'POST':
            set_config('auto_react', request.form.get('auto_react', 'off'))
            set_config('auto_welcome', request.form.get('auto_welcome', 'off'))
            set_config('auto_reply', request.form.get('auto_reply', 'off'))
            return redirect(url_for('md_bot.setup_or_dashboard'))
        status = {
            'auto_react': get_config('auto_react') == 'on',
            'auto_welcome': get_config('auto_welcome') == 'on',
            'auto_reply': get_config('auto_reply') == 'on',
        }
        return render_template_string(DASHBOARD_HTML, status=status)

SETUP_HTML = '''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cyber Tools MD – Setup</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, sans-serif; }
body { background:#0d1117; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
.card { background:#161b22; border-radius:28px; padding:30px 24px; max-width:400px; width:100%; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid #30363d; }
h1 { color:#f0f6fc; font-size:24px; margin-bottom:8px; }
p { color:#8b949e; font-size:14px; margin-bottom:20px; }
input { width:100%; padding:12px; border-radius:10px; border:1px solid #30363d; background:#0d1117; color:#fff; font-size:16px; }
button { width:100%; padding:12px; border-radius:10px; border:0; background:#238636; color:#fff; font-size:16px; font-weight:600; cursor:pointer; margin-top:12px; }
button:hover { background:#2ea043; }
.error { color:#f85149; font-size:14px; margin-bottom:10px; }
</style>
</head>
<body>
<div class="card">
    <h1>🛡️ Cyber Tools MD</h1>
    <p>Enter your Telegram Bot Token to activate.</p>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="post">
        <input type="text" name="bot_token" placeholder="e.g. 123456:ABC-DEF" required>
        <button type="submit">Activate Bot</button>
    </form>
</div>
</body>
</html>
'''

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cyber Tools MD – Dashboard</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, sans-serif; }
body { background:#0d1117; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
.card { background:#161b22; border-radius:28px; padding:30px 24px; max-width:450px; width:100%; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid #30363d; }
h1 { color:#f0f6fc; font-size:24px; margin-bottom:4px; }
.sub { color:#8b949e; font-size:14px; margin-bottom:20px; }
.badge { display:inline-block; background:#238636; color:#fff; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:500; margin-bottom:20px; }
.btn-open { display:block; background:#1f6feb; color:#fff; text-align:center; padding:14px; border-radius:14px; font-size:17px; font-weight:600; text-decoration:none; margin-bottom:24px; }
.btn-open:hover { background:#388bfd; }
.divider { border:none; border-top:1px solid #30363d; margin:20px 0; }
.toggle-item { display:flex; justify-content:space-between; align-items:center; background:#0d1117; padding:12px 16px; border-radius:14px; margin-bottom:10px; }
.toggle-label { color:#c9d1d9; font-size:16px; font-weight:500; }
.toggle-options label { color:#8b949e; font-size:15px; display:flex; align-items:center; gap:6px; cursor:pointer; }
.toggle-options input[type="radio"] { accent-color:#1f6feb; width:18px; height:18px; cursor:pointer; }
.save-btn { width:100%; background:#238636; color:#fff; border:none; padding:14px; border-radius:14px; font-size:17px; font-weight:600; cursor:pointer; margin-top:12px; }
.save-btn:hover { background:#2ea043; }
.footer { text-align:center; color:#484f58; font-size:12px; margin-top:20px; }
</style>
</head>
<body>
<div class="card">
    <h1>🛡️ Cyber Tools MD</h1>
    <div class="sub">Bot Control Panel</div>
    <div class="badge">● Active</div>
    <a href="https://t.me/Arif1222_bot" target="_blank" class="btn-open">📱 Open Bot</a>
    <hr class="divider">
    <form method="post">
        <div class="toggle-item">
            <span class="toggle-label">Auto React</span>
            <div class="toggle-options">
                <label><input type="radio" name="auto_react" value="on" {{ 'checked' if status.auto_react else '' }}> ON</label>
                <label><input type="radio" name="auto_react" value="off" {{ 'checked' if not status.auto_react else '' }}> OFF</label>
            </div>
        </div>
        <div class="toggle-item">
            <span class="toggle-label">Auto Welcome</span>
            <div class="toggle-options">
                <label><input type="radio" name="auto_welcome" value="on" {{ 'checked' if status.auto_welcome else '' }}> ON</label>
                <label><input type="radio" name="auto_welcome" value="off" {{ 'checked' if not status.auto_welcome else '' }}> OFF</label>
            </div>
        </div>
        <div class="toggle-item">
            <span class="toggle-label">Auto Reply</span>
            <div class="toggle-options">
                <label><input type="radio" name="auto_reply" value="on" {{ 'checked' if status.auto_reply else '' }}> ON</label>
                <label><input type="radio" name="auto_reply" value="off" {{ 'checked' if not status.auto_reply else '' }}> OFF</label>
            </div>
        </div>
        <button type="submit" class="save-btn">Save Settings</button>
    </form>
    <div class="footer">Token is hidden for security</div>
</div>
</body>
</html>
'''

# ========== বট ফাংশন ==========
def send_message(chat_id, text, parse_mode='HTML'):
    token = get_token()
    if not token:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}, timeout=5)
        if r.json().get('ok'):
            logger.info(f"✅ Sent message to {chat_id}")
        else:
            logger.error(f"❌ Send failed: {r.text}")
    except Exception as e:
        logger.error(f"Send error: {e}")

def send_reactions(chat_id, message_id):
    if get_config('auto_react') != 'on':
        return
    token = get_token()
    if not token:
        logger.error("❌ No token found.")
        return

    # টেলিগ্রাম-সমর্থিত ইমোজি (নিরাপদ ৬টি)
    emojis = ["👍", "❤️", "🔥", "🥰", "👏", "🎉"]
    try:
        reaction_list = [{"type": "emoji", "emoji": e} for e in emojis]
        url = f"https://api.telegram.org/bot{token}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps(reaction_list)
        }
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if data.get('ok'):
            logger.info(f"✅ {len(emojis)} reactions sent to {message_id}")
        else:
            logger.error(f"❌ React failed: {data}")
    except Exception as e:
        logger.error(f"❌ React exception: {e}")

# ========== কমান্ড ও অটো রিপ্লাই ==========
processed_messages = set()

def handle_auto_reply(msg):
    if get_config('auto_reply') != 'on':
        return
    text = msg.get('text', '').lower().strip()
    if not text:
        return
    chat_id = msg['chat']['id']
    message_id = msg['message_id']
    if message_id in processed_messages:
        return
    processed_messages.add(message_id)
    for keyword, reply in AUTO_REPLIES.items():
        if keyword in text:
            send_message(chat_id, reply)
            break

def handle_welcome(msg):
    if get_config('auto_welcome') != 'on':
        return
    if 'new_chat_members' not in msg:
        return
    chat_id = msg['chat']['id']
    for member in msg['new_chat_members']:
        name = member.get('first_name', 'Guest')
        welcome = f"<b>🎉 Welcome {name}!</b> 🥳\nGlad to have you here. Type /start to see what I can do."
        send_message(chat_id, welcome)

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
/bot/ - Control all features

<b>💬 Auto Reply:</b>
I reply to hi, good morning, good night, etc. (if enabled)."""
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
    if reply:
        send_message(chat_id, reply)

# ========== পোলিং ==========
def polling_worker():
    logger.info("🔄 Polling thread started.")
    last_update_id = 0
    while True:
        token = get_token()
        if not token:
            time.sleep(5)
            continue
        try:
            requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=5)
        except:
            pass
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={'offset': last_update_id + 1, 'timeout': 30}
            )
            data = resp.json()
            if not data.get('ok'):
                if data.get('error_code') == 409:
                    logger.warning("⚠️ 409 Conflict – another instance is running. Will retry...")
                else:
                    logger.error(f"API error: {data}")
                time.sleep(5)
                continue
            for update in data.get('result', []):
                last_update_id = update['update_id']
                msg = update.get('message')
                if not msg:
                    continue
                logger.info(f"📩 Received: {msg.get('text', '')}")
                send_reactions(msg['chat']['id'], msg['message_id'])
                handle_commands(msg)
                handle_auto_reply(msg)
                handle_welcome(msg)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

def start_polling_thread():
    global polling_started
    if polling_started:
        return
    threading.Thread(target=polling_worker, daemon=True).start()
    polling_started = True
    logger.info("🚀 Polling thread started (first time).")

if get_token():
    start_polling_thread()
else:
    logger.info("⏳ No token found. Bot will start after token is set.")

try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)
    bp.register_blueprint(converter.bp)
    bp.register_blueprint(formatter.bp)
    logger.info("✅ md_tools loaded.")
except:
    pass
