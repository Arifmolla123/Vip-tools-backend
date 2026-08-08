from flask import Blueprint, request, render_template_string
import os
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

# ========== Database ==========
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

# ========== Web Setup ==========
@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if not token:
            return "<h2 style='color:red;'>❌ Token cannot be empty!</h2><a href='/bot/setup'>Try Again</a>"
        set_token(token)
        logger.info("✅ Token saved.")
        try:
            me = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if not me.json().get('ok'):
                return f"<h2 style='color:red;'>❌ Invalid Token!</h2><a href='/bot/setup'>Try Again</a>"
        except Exception as e:
            return f"<h2 style='color:red;'>❌ Error: {e}</h2><a href='/bot/setup'>Try Again</a>"
        return f"""
        <h2 style='color:green;'>✅ Setup Complete!</h2>
        <p>Token: <code>{token[:10]}...</code></p>
        <p>Now add me to your group/channel. Type <code>/start</code> to begin.</p>
        <a href='/bot/setup'>Go Back</a>
        """
    current = get_token()
    return f"""
    <!DOCTYPE html>
    <html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;background:#0d1117;color:#c9d1d9;padding:20px;border-radius:10px;">
    <h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
    <h3>🤖 Bot Setup</h3>
    {'<p style="color:#3fb950;">✅ Token exists. Enter new to update:</p>' if current else '<p>Paste your token from @BotFather:</p>'}
    <form method="post">
    <input type="text" name="bot_token" placeholder="e.g. 123456:ABC-DEF" style="width:100%;padding:10px;background:#161b22;color:#fff;border:1px solid #30363d;border-radius:6px;">
    <button type="submit" style="margin-top:10px;background:#238636;color:#fff;padding:10px 20px;border:0;border-radius:6px;cursor:pointer;">Save & Activate</button>
    </form>
    </body></html>
    """

# ========== Helper: Send reaction ==========
def send_reaction(chat_id, message_id, token, emoji="❤️"):
    """Send a reaction to a specific message"""
    try:
        url = f"https://api.telegram.org/bot{token}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps([{'type': 'emoji', 'emoji': emoji}])
        }
        r = requests.post(url, json=payload, timeout=5)
        if r.json().get('ok'):
            logger.info(f"✅ Reacted with {emoji} to message {message_id}")
        else:
            logger.error(f"❌ Reaction failed: {r.text}")
    except Exception as e:
        logger.error(f"Reaction error: {e}")

# ========== Polling Worker ==========
def polling_worker():
    logger.info("🔄 [WORKER] Polling started.")
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
                    message_id = msg['message_id']
                    text = msg.get('text', '')
                    username = msg['from'].get('username', 'Unknown')
                    logger.info(f"📩 Received: '{text}' from {username}")

                    # ---------- AUTO REACTION ----------
                    send_reaction(chat_id, message_id, token, "❤️")

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

<b>✨ Auto Style:</b>
Just type any text and I'll reply with it beautifully formatted!

<b>👋 Welcome:</b>
I automatically welcome new members.

<b>🌐 Web Tools:</b>
/bot/md/preview (if md_tools is installed)"""

                    # ---------- /help ----------
                    elif text == '/help':
                        reply = "Send /start to see all available commands."

                    # ---------- Formatting Commands ----------
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

                    # ---------- AUTO STYLE: Any non-command text ----------
                    elif not text.startswith('/') and text.strip() != '':
                        # Format the text with all styles
                        styled = f"<b>{text}</b>\n<i>{text}</i>\n<code>{text}</code>\n<s>{text}</s>"
                        reply = f"✨ <b>Auto‑styled version:</b>\n\n{styled}"

                    # ---------- Welcome message ----------
                    if 'new_chat_members' in msg:
                        for member in msg['new_chat_members']:
                            first_name = member.get('first_name', 'Guest')
                            logger.info(f"👤 New member detected: {first_name}")
                            welcome_text = f"<b>🎉 Welcome {first_name}!</b> 🥳\nGlad to have you here. Type /start to see what I can do."
                            try:
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
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
                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
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
