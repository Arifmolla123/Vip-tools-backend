from flask import Blueprint, request, render_template_string, redirect, url_for
import os
import sqlite3
import time
import threading
import requests
import json
import logging
import random

# ========== Logging ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

# ========== আপনার বটের টোকেন (হার্ডকোডেড) ==========
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1Lcpus1Z2iz6kOORo"
BOT_USERNAME = "Arif1222_bot"  # @ চিহ্ন ছাড়া

# ========== Database (শুধু অটো রিঅ্যাক্ট সেটিংস) ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('auto_react', 'on')")
    conn.commit()
    conn.close()
init_db()

def get_auto_react():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_config WHERE key='auto_react'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'on'

def set_auto_react(status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value=? WHERE key='auto_react'", (status,))
    conn.commit()
    conn.close()

# ========== ড্যাশবোর্ড (অটো রিঅ্যাক্ট টগল + বট লিংক) ==========
@bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        status = request.form.get('auto_react', 'off')
        set_auto_react(status)
        logger.info(f"🔄 Auto-react set to: {status}")
        return redirect(url_for('md_bot.dashboard'))
    
    current_status = get_auto_react()
    is_on = current_status == 'on'
    
    # বটের লিংক তৈরি করছি
    bot_link = f"https://t.me/{BOT_USERNAME}"
    
    return f"""
    <!DOCTYPE html>
    <html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;background:#0d1117;color:#c9d1d9;padding:20px;border-radius:10px;">
    <h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
    <h3>📊 Dashboard</h3>
    <p><strong>Bot Status:</strong> ✅ Active</p>
    
    <!-- বট লিংক বাটন -->
    <p style="margin: 20px 0;">
        <a href="{bot_link}" target="_blank" 
           style="background:#1f6feb;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;">
           📱 Open Telegram Bot (@{BOT_USERNAME})
        </a>
    </p>

    <hr style="border-color:#30363d;">

    <form method="post">
    <p><strong>Auto React:</strong>
    <label>
        <input type="radio" name="auto_react" value="on" {'checked' if is_on else ''}> ON
    </label>
    <label>
        <input type="radio" name="auto_react" value="off" {'checked' if not is_on else ''}> OFF
    </label>
    </p>
    <button type="submit" style="margin-top:10px;background:#238636;color:#fff;padding:10px 20px;border:0;border-radius:6px;cursor:pointer;">Save Settings</button>
    </form>
    <p style="margin-top:20px;color:#8b949e;">Token is hidden for security.</p>
    <a href='/' style="color:#58a6ff;">Go Home</a>
    </body></html>
    """

# ========== Helper: Send multiple reactions ==========
def send_reactions(chat_id, message_id, emojis=None):
    if get_auto_react() != 'on':
        logger.info("⏸️ Auto-react is OFF, skipping reactions.")
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
            logger.info(f"✅ Reacted with {len(emojis)} reactions to message {message_id}")
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

                    # ---------- AUTO REACTION ----------
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

<b>✨ Auto Style:</b>
Just type any text and I'll reply with a <b>random</b> style (bold/italic/code/strike)!

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

                    # ---------- AUTO STYLE (Random one style) ----------
                    elif not text.startswith('/') and text.strip() != '':
                        styles = [
                            ("<b>{}</b>", "bold"),
                            ("<i>{}</i>", "italic"),
                            ("<code>{}</code>", "code"),
                            ("<s>{}</s>", "strike")
                        ]
                        format_str, style_name = random.choice(styles)
                        reply = format_str.format(text)
                        logger.info(f"🎨 Auto-styled with {style_name}")

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
