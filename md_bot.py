from flask import Blueprint, request, render_template_string
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

# ========== IMPROVED GIF SEARCH (Two APIs for reliability) ==========
def search_gif(query):
    """Search for a GIF using multiple free APIs."""
    try:
        # Try Giphy first (free, no key required)
        url = "https://api.giphy.com/v1/gifs/search"
        params = {
            'api_key': 'dc6zaTOxFJmzC',  # public beta key
            'q': query,
            'limit': 10,
            'rating': 'pg-13'
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        if data.get('meta', {}).get('status') == 200 and data.get('data'):
            # Pick a random GIF from the results
            gif_data = random.choice(data['data'])
            return gif_data['images']['original']['url']
    except Exception as e:
        logger.warning(f"Giphy failed: {e}")

    # If Giphy fails, try Tenor (another free API)
    try:
        url = "https://g.tenor.com/v1/search"
        params = {
            'q': query,
            'key': 'LIVDSRZULELA',  # public Tenor key
            'limit': 10
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        if data.get('results'):
            gif = random.choice(data['results'])
            return gif['media'][0]['gif']['url']
    except Exception as e:
        logger.warning(f"Tenor failed: {e}")

    return None  # No GIF found

# ========== Web Setup Page ==========
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
        <p>Now add me as Admin in your group/channel, then type <code>/start</code>.</p>
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

# ========== IMPROVED get_target_user (works with @username, name, or reply) ==========
def get_target_user(update, token):
    """Extract target user ID from reply or @username (with or without @)."""
    msg = update.get('message')
    if not msg:
        return None, None

    # 1. If replying to a message
    if 'reply_to_message' in msg:
        target = msg['reply_to_message']['from']
        return target['id'], target.get('username', target.get('first_name', 'User'))

    # 2. Parse command text for username
    text = msg.get('text', '')
    parts = text.split()
    if len(parts) > 1:
        username = parts[1].strip()
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
        
        # Try to get user_id using getChatMember
        try:
            # First, try to get by username
            resp = requests.get(f"https://api.telegram.org/bot{token}/getChatMember",
                                params={'chat_id': msg['chat']['id'], 'user_id': '@' + username})
            data = resp.json()
            if data.get('ok') and data.get('result'):
                return data['result']['user']['id'], username
        except:
            pass
        
        # If that fails, try searching chat members by name (limited)
        # Telegram API doesn't support direct search by first name, so we can only use this fallback.
        # In practice, users should use @username or reply.
        pass

    return None, None

# ========== Polling Worker (with fixed GIF & user targeting) ==========
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
                    text = msg.get('text', '')
                    username = msg['from'].get('username', 'Unknown')
                    logger.info(f"📩 Received: '{text}' from {username}")

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
/echo [text] - All formats

<b>🎨 GIF Command:</b>
/gif [query] - Send a GIF (e.g. /gif happy dog)

<b>👮 Admin Commands (Reply to a user or use @username):</b>
/ban @username - Ban the user
/kick @username - Kick the user
/mute @username - Mute the user
/unmute @username - Unmute the user
/promote @username - Make Admin
/demote @username - Remove Admin
/del - (reply) Delete replied message
/pin - (reply) Pin replied message
/unpin - (reply) Unpin replied message

<b>🔧 Conditions:</b> I must be an <b>Admin</b> in this group/channel!"""

                    # ---------- Formatting ----------
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

                    # ---------- FIXED GIF COMMAND ----------
                    elif text.startswith('/gif '):
                        query = text[5:].strip()
                        if not query:
                            reply = "❌ Please provide a search term. Example: `/gif happy dog`"
                        else:
                            gif_url = search_gif(query)
                            if gif_url:
                                try:
                                    send_gif_url = f"https://api.telegram.org/bot{token}/sendAnimation"
                                    r = requests.post(send_gif_url, json={
                                        'chat_id': chat_id,
                                        'animation': gif_url,
                                        'caption': f"🎬 GIF for: {query}"
                                    }, timeout=10)
                                    if r.json().get('ok'):
                                        logger.info(f"✅ GIF sent to {chat_id}")
                                    else:
                                        reply = f"❌ Failed to send GIF: {r.json().get('description')}"
                                except Exception as e:
                                    reply = f"❌ Error sending GIF: {e}"
                            else:
                                reply = f"❌ No GIF found for: {query}"

                    # ---------- FIXED ADMIN COMMANDS (with better targeting) ----------
                    elif text.startswith('/ban') or text.startswith('/kick') or text.startswith('/mute') or text.startswith('/unmute') or text.startswith('/promote') or text.startswith('/demote'):
                        target_id, target_name = get_target_user(update, token)
                        if not target_id:
                            reply = "❌ Please reply to a user's message OR provide @username (e.g. /ban @username)"
                        else:
                            action = text.split()[0][1:]
                            api_method = None
                            params = {'chat_id': chat_id, 'user_id': target_id}

                            if action == 'ban':
                                api_method = 'banChatMember'
                                reply = f"✅ {target_name} has been banned."
                            elif action == 'kick':
                                try:
                                    requests.get(f"https://api.telegram.org/bot{token}/banChatMember", params=params, timeout=5)
                                    requests.get(f"https://api.telegram.org/bot{token}/unbanChatMember", params=params, timeout=5)
                                    reply = f"✅ {target_name} has been kicked."
                                except Exception as e:
                                    reply = f"❌ Kick failed: {e}"
                                api_method = None
                            elif action == 'mute':
                                api_method = 'restrictChatMember'
                                params['permissions'] = json.dumps({'can_send_messages': False})
                                reply = f"🔇 {target_name} has been muted."
                            elif action == 'unmute':
                                api_method = 'restrictChatMember'
                                params['permissions'] = json.dumps({'can_send_messages': True})
                                reply = f"🔊 {target_name} has been unmuted."
                            elif action == 'promote':
                                api_method = 'promoteChatMember'
                                params['can_manage_chat'] = True
                                params['can_delete_messages'] = True
                                params['can_restrict_members'] = True
                                params['can_pin_messages'] = True
                                reply = f"👑 {target_name} has been promoted to Admin."
                            elif action == 'demote':
                                api_method = 'promoteChatMember'
                                params['can_manage_chat'] = False
                                params['can_delete_messages'] = False
                                params['can_restrict_members'] = False
                                params['can_pin_messages'] = False
                                reply = f"🛡️ {target_name}'s Admin rights have been revoked."

                            if api_method:
                                try:
                                    r = requests.get(f"https://api.telegram.org/bot{token}/{api_method}", params=params, timeout=5)
                                    if not r.json().get('ok'):
                                        reply = f"❌ Failed: {r.json().get('description')}\n⚠️ Make sure I am an Admin!"
                                except Exception as e:
                                    reply = f"❌ API error: {e}"

                    # ---------- Delete / Pin (unchanged) ----------
                    elif text.startswith('/del'):
                        if 'reply_to_message' in msg:
                            target_msg_id = msg['reply_to_message']['message_id']
                            try:
                                r = requests.get(f"https://api.telegram.org/bot{token}/deleteMessage",
                                                 params={'chat_id': chat_id, 'message_id': target_msg_id}, timeout=5)
                                if r.json().get('ok'):
                                    reply = "🗑️ Message deleted."
                                else:
                                    reply = f"❌ Could not delete: {r.json().get('description')}"
                            except Exception as e:
                                reply = f"❌ Error: {e}"
                        else:
                            reply = "❌ Reply to a message to delete it."

                    elif text.startswith('/pin'):
                        if 'reply_to_message' in msg:
                            target_msg_id = msg['reply_to_message']['message_id']
                            try:
                                r = requests.get(f"https://api.telegram.org/bot{token}/pinChatMessage",
                                                 params={'chat_id': chat_id, 'message_id': target_msg_id}, timeout=5)
                                if r.json().get('ok'):
                                    reply = "📌 Message pinned."
                                else:
                                    reply = f"❌ Could not pin: {r.json().get('description')}"
                            except Exception as e:
                                reply = f"❌ Error: {e}"
                        else:
                            reply = "❌ Reply to a message to pin it."

                    elif text.startswith('/unpin'):
                        try:
                            if 'reply_to_message' in msg:
                                target_msg_id = msg['reply_to_message']['message_id']
                                r = requests.get(f"https://api.telegram.org/bot{token}/unpinChatMessage",
                                                 params={'chat_id': chat_id, 'message_id': target_msg_id}, timeout=5)
                            else:
                                r = requests.get(f"https://api.telegram.org/bot{token}/unpinAllChatMessages",
                                                 params={'chat_id': chat_id}, timeout=5)
                            if r.json().get('ok'):
                                reply = "📌 Unpinned successfully."
                            else:
                                reply = f"❌ Could not unpin: {r.json().get('description')}"
                        except Exception as e:
                            reply = f"❌ Error: {e}"

                    # ---------- Auto-Welcome (unchanged) ----------
                    if 'new_chat_members' in msg:
                        for member in msg['new_chat_members']:
                            first_name = member.get('first_name', 'Guest')
                            welcome_text = f"🎉 *Welcome* {first_name}! 🥳\nGlad to have you here. Type /start to see what I can do."
                            try:
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(send_url, json={
                                    'chat_id': chat_id,
                                    'text': welcome_text,
                                    'parse_mode': 'MarkdownV2'
                                })
                                logger.info(f"✅ Welcome sent to {first_name}")
                            except Exception as e:
                                logger.error(f"Welcome failed: {e}")

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

# ========== Start Thread ==========
threading.Thread(target=polling_worker, daemon=True).start()
logger.info("🚀 [MAIN] Polling worker launched.")

# ========== Load md_tools ==========
try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)
    bp.register_blueprint(converter.bp)
    bp.register_blueprint(formatter.bp)
    logger.info("✅ md_tools loaded.")
except ImportError:
    logger.warning("⚠️ md_tools not found.")
