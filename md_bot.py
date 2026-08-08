from flask import Blueprint, request, redirect, url_for
import sqlite3
import time
import threading
import requests
import json
import logging

# ========== Logging ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

# ========== আপনার বটের টোকেন (হার্ডকোডেড) ==========
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1Lcpus1Z2iz6kOORo"
BOT_LINK = "https://t.me/Arif1222_bot"  # শুধু লিংক, ইউজারনেম দেখানো হবে না

# ========== Database (অটো রিঅ্যাক্ট সেটিংস) ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('auto_react', 'off')")
    conn.commit()
    conn.close()
init_db()

def get_auto_react():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_config WHERE key='auto_react'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'off'

def set_auto_react(status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value=? WHERE key='auto_react'", (status,))
    conn.commit()
    conn.close()

# ========== ড্যাশবোর্ড (মোবাইল অ্যাপ ডিজাইন) ==========
@bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        status = request.form.get('auto_react', 'off')
        set_auto_react(status)
        logger.info(f"🔄 Auto-react set to: {status}")
        return redirect(url_for('md_bot.dashboard'))
    
    current_status = get_auto_react()
    is_on = current_status == 'on'
    
    # HTML – মোবাইল অ্যাপের মত ডিজাইন, শুধু "Open Bot" বাটন
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Cyber Tools MD</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}
            body {{
                background: #0d1117;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}
            .card {{
                background: #161b22;
                border-radius: 28px;
                padding: 30px 24px;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 12px 40px rgba(0,0,0,0.6);
                border: 1px solid #30363d;
            }}
            .app-icon {{
                background: #1f6feb;
                width: 64px;
                height: 64px;
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 32px;
                margin-bottom: 16px;
            }}
            h1 {{
                font-size: 24px;
                font-weight: 600;
                color: #f0f6fc;
                margin-bottom: 4px;
            }}
            .sub {{
                color: #8b949e;
                font-size: 14px;
                margin-bottom: 24px;
            }}
            .status-badge {{
                display: inline-block;
                background: #238636;
                color: #fff;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 500;
                margin-bottom: 20px;
            }}
            .btn-open {{
                display: block;
                background: #1f6feb;
                color: #fff;
                text-align: center;
                padding: 14px;
                border-radius: 14px;
                font-size: 17px;
                font-weight: 600;
                text-decoration: none;
                margin-bottom: 24px;
                transition: background 0.2s;
            }}
            .btn-open:hover {{
                background: #388bfd;
            }}
            .divider {{
                border: none;
                border-top: 1px solid #30363d;
                margin: 20px 0;
            }}
            .toggle-group {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #0d1117;
                padding: 12px 16px;
                border-radius: 14px;
                margin-bottom: 8px;
            }}
            .toggle-label {{
                color: #c9d1d9;
                font-size: 16px;
                font-weight: 500;
            }}
            .toggle-options {{
                display: flex;
                gap: 12px;
            }}
            .toggle-options label {{
                color: #8b949e;
                font-size: 15px;
                display: flex;
                align-items: center;
                gap: 6px;
                cursor: pointer;
            }}
            .toggle-options input[type="radio"] {{
                accent-color: #1f6feb;
                width: 18px;
                height: 18px;
                cursor: pointer;
            }}
            .btn-save {{
                width: 100%;
                background: #238636;
                color: #fff;
                border: none;
                padding: 14px;
                border-radius: 14px;
                font-size: 17px;
                font-weight: 600;
                cursor: pointer;
                margin-top: 12px;
                transition: background 0.2s;
            }}
            .btn-save:hover {{
                background: #2ea043;
            }}
            .footer {{
                text-align: center;
                color: #484f58;
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="app-icon">🛡️</div>
            <h1>Cyber Tools MD</h1>
            <div class="sub">Bot Control Panel</div>
            <div class="status-badge">● Active</div>

            <a href="{BOT_LINK}" target="_blank" class="btn-open">📱 Open Bot</a>

            <hr class="divider">

            <form method="post">
                <div class="toggle-group">
                    <span class="toggle-label">Auto React</span>
                    <div class="toggle-options">
                        <label>
                            <input type="radio" name="auto_react" value="on" {'checked' if is_on else ''}> ON
                        </label>
                        <label>
                            <input type="radio" name="auto_react" value="off" {'checked' if not is_on else ''}> OFF
                        </label>
                    </div>
                </div>
                <button type="submit" class="btn-save">Save Settings</button>
            </form>
            <div class="footer">Token is hidden for security</div>
        </div>
    </body>
    </html>
    """

# ========== Helper: Send reactions (ONLY if auto_react is ON) ==========
def send_reactions(chat_id, message_id, emojis=None):
    # প্রতিবার ডেটাবেস থেকে রিয়েল-টাইম স্ট্যাটাস পড়ি
    if get_auto_react() != 'on':
        return
    if emojis is None:
        emojis = ["❤️", "🔥", "👍", "🎉"]
    try:
        reaction_list = [{"type": "emoji", "emoji": emoji} for emoji in emojis]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps(reaction_list)
        }
        r = requests.post(url, json=payload, timeout=5)
        if r.json().get('ok'):
            logger.info(f"✅ Reacted with {len(emojis)} reactions")
        else:
            logger.error(f"❌ Reaction failed: {r.text}")
    except Exception as e:
        logger.error(f"Reaction error: {e}")

# ========== Polling Worker ==========
def polling_worker():
    logger.info("🔄 [WORKER] Polling started.")
    last_update_id = 0

    while True:
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
        except:
            pass

        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
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
                    message_id = msg['message_id']
                    text = msg.get('text', '')
                    username = msg['from'].get('username', 'Unknown')
                    logger.info(f"📩 Received: '{text}' from {username}")

                    # ---------- AUTO REACTION (ডেটাবেস চেক করে) ----------
                    send_reactions(chat_id, message_id)

                    reply = None
                    parse_mode = 'HTML'

                    # ---------- /start ----------
                    if text == '/start':
                        reply = """<b>🛡️ Cyber MD Bot is LIVE!</b> 🚀

<b>📝 Formatting Commands:</b>
/bold [text] - <b>Bold</b>
/italic [text] - <i>Italic</i>
/code [text] - <code>Code</code>
/strike [text] - <s>Strike</s>
/echo [text] - All formats combined

<b>⚙️ Dashboard:</b>
/bot/dashboard - Control auto‑react ON/OFF

<b>👋 Welcome:</b>
I automatically welcome new members.

<b>🌐 Web Tools:</b>
/bot/md/preview (if md_tools is installed)"""

                    # ---------- /help ----------
                    elif text == '/help':
                        reply = "Send /start to see all available commands."

                    # ---------- Manual Formatting Commands ----------
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

                    # ---------- Welcome message ----------
                    if 'new_chat_members' in msg:
                        for member in msg['new_chat_members']:
                            first_name = member.get('first_name', 'Guest')
                            logger.info(f"👤 New member detected: {first_name}")
                            welcome_text = f"<b>🎉 Welcome {first_name}!</b> 🥳\nGlad to have you here. Type /start to see what I can do."
                            try:
                                send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                                r = requests.post(send_url, json={
                                    'chat_id': chat_id,
                                    'text': welcome_text,
                                    'parse_mode': 'HTML'
                                }, timeout=5)
                                if r.json().get('ok'):
                                    logger.info(f"✅ Welcome sent to {first_name}")
                                else:
                                    logger.error(f"❌ Welcome failed: {r.text}")
                            except Exception as e:
                                logger.error(f"Welcome exception: {e}")

                    # ---------- Send reply if any ----------
                    if reply:
                        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                        r = requests.post(send_url, json={
                            'chat_id': chat_id,
                            'text': reply,
                            'parse_mode': parse_mode
                        }, timeout=5)
                        if r.json().get('ok'):
                            logger.info(f"✅ Replied to {chat_id}")
                        else:
                            logger.error(f"❌ Failed: {r.text}")

            time.sleep(1)

        except Exception as e:
            logger.error(f"⚠️ Polling error: {e}")
            time.sleep(5)

# ========== Start Polling Thread ==========
threading.Thread(target=polling_worker, daemon=True).start()
logger.info("🚀 [MAIN] Polling worker launched.")

# ========== Load md_tools (if available) ==========
try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)
    bp.register_blueprint(converter.bp)
    bp.register_blueprint(formatter.bp)
    logger.info("✅ md_tools loaded.")
except ImportError:
    logger.warning("⚠️ md_tools not found (web tools unavailable).")
