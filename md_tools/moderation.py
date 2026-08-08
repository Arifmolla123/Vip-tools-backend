from flask import Blueprint, request, redirect, url_for, render_template_string
import sqlite3
import time
import re
import json
import logging
import requests

logger = logging.getLogger(__name__)
bp = Blueprint('moderation', __name__, url_prefix='/mod')
DB_PATH = '/tmp/phish_data.db'

# ========== ডেটাবেস ==========
def init_mod_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS mod_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO mod_config (key, value) VALUES ('anti_link', 'off')")
    c.execute("INSERT OR IGNORE INTO mod_config (key, value) VALUES ('bad_words', '[]')")
    c.execute("INSERT OR IGNORE INTO mod_config (key, value) VALUES ('warn_limit', '3')")
    c.execute("INSERT OR IGNORE INTO mod_config (key, value) VALUES ('auto_purge', 'off')")
    c.execute('''CREATE TABLE IF NOT EXISTS warnings 
                 (user_id INTEGER, chat_id INTEGER, count INTEGER, 
                 PRIMARY KEY (user_id, chat_id))''')
    conn.commit()
    conn.close()
init_mod_db()

def get_mod_config(key):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value FROM mod_config WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else ''
    except:
        return ''

def set_mod_config(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE mod_config SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def get_warn_count(user_id, chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count FROM warnings WHERE user_id=? AND chat_id=?", (user_id, chat_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def set_warn_count(user_id, chat_id, count):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO warnings (user_id, chat_id, count) VALUES (?, ?, ?)", (user_id, chat_id, count))
    conn.commit()
    conn.close()

def delete_warn(user_id, chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id=? AND chat_id=?", (user_id, chat_id))
    conn.commit()
    conn.close()

def is_admin(chat_id, user_id, token):
    try:
        url = f"https://api.telegram.org/bot{token}/getChatMember"
        params = {'chat_id': chat_id, 'user_id': user_id}
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if data.get('ok'):
            status = data['result'].get('status')
            return status in ('administrator', 'creator')
    except:
        pass
    return False

def delete_message(chat_id, message_id, token):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteMessage"
        params = {'chat_id': chat_id, 'message_id': message_id}
        r = requests.get(url, params=params, timeout=5)
        return r.json().get('ok', False)
    except:
        return False

def send_message(chat_id, text, token, parse_mode='HTML'):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}, timeout=5)
        return r.json().get('ok', False)
    except:
        return False

# ========== মডারেশন হ্যান্ডলার (শুধু চালু থাকলে) ==========
def handle_moderation(msg, token):
    if not token:
        return
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    message_id = msg['message_id']
    text = msg.get('text', '')

    if is_admin(chat_id, user_id, token):
        return

    action_taken = False

    if get_mod_config('anti_link') == 'on':
        if re.search(r'(https?://|t\.me/|bit\.ly/|tinyurl\.com/)', text, re.IGNORECASE):
            delete_message(chat_id, message_id, token)
            send_message(chat_id, "🚫 <b>Anti-Link:</b> You are not allowed to send links here!", token)
            logger.info(f"🚫 Deleted link from {user_id}")
            return True

    if get_mod_config('bad_words') != '[]':
        try:
            bad_words_list = json.loads(get_mod_config('bad_words'))
            if any(word.lower() in text.lower() for word in bad_words_list):
                delete_message(chat_id, message_id, token)
                current_warn = get_warn_count(user_id, chat_id) + 1
                set_warn_count(user_id, chat_id, current_warn)
                warn_limit = int(get_mod_config('warn_limit') or 3)
                
                if current_warn >= warn_limit:
                    try:
                        url = f"https://api.telegram.org/bot{token}/banChatMember"
                        params = {'chat_id': chat_id, 'user_id': user_id}
                        requests.get(url, params=params, timeout=5)
                        send_message(chat_id, f"🔨 <b>User banned!</b> Reason: Exceeded warning limit ({warn_limit}).", token)
                        delete_warn(user_id, chat_id)
                    except:
                        pass
                else:
                    send_message(chat_id, f"⚠️ <b>Warning {current_warn}/{warn_limit}</b>\nPlease avoid using bad words!", token)
                logger.info(f"⚠️ Warned {user_id} for bad word (count: {current_warn})")
                return True
        except:
            pass

    return False

def handle_admin_commands(msg, token):
    text = msg.get('text', '')
    if not text.startswith('/'):
        return
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    
    if not is_admin(chat_id, user_id, token):
        return

    reply = None
    parts = text.split()
    cmd = parts[0][1:]

    target_id = None
    target_name = 'User'
    if 'reply_to_message' in msg:
        target_id = msg['reply_to_message']['from']['id']
        target_name = msg['reply_to_message']['from'].get('username', 'User')
    elif len(parts) > 1:
        username = parts[1].strip()
        if username.startswith('@'):
            username = username[1:]
        try:
            url = f"https://api.telegram.org/bot{token}/getChatMember"
            params = {'chat_id': chat_id, 'user_id': '@' + username}
            r = requests.get(url, params=params, timeout=5)
            data = r.json()
            if data.get('ok') and data.get('result'):
                target_id = data['result']['user']['id']
                target_name = username
        except:
            pass

    if not target_id and cmd not in ['purge']:
        send_message(chat_id, "❌ Please reply to a user or provide @username.", token)
        return

    if cmd == 'ban':
        try:
            url = f"https://api.telegram.org/bot{token}/banChatMember"
            params = {'chat_id': chat_id, 'user_id': target_id}
            r = requests.get(url, params=params, timeout=5)
            if r.json().get('ok'):
                reply = f"🔨 <b>{target_name}</b> has been banned."
                delete_warn(target_id, chat_id)
            else:
                reply = f"❌ Failed to ban: {r.json().get('description')}"
        except Exception as e:
            reply = f"❌ Error: {e}"

    elif cmd == 'kick':
        try:
            url = f"https://api.telegram.org/bot{token}/banChatMember"
            params = {'chat_id': chat_id, 'user_id': target_id}
            r = requests.get(url, params=params, timeout=5)
            if r.json().get('ok'):
                requests.get(f"https://api.telegram.org/bot{token}/unbanChatMember", params=params, timeout=5)
                reply = f"🚪 <b>{target_name}</b> has been kicked."
                delete_warn(target_id, chat_id)
            else:
                reply = f"❌ Failed to kick: {r.json().get('description')}"
        except Exception as e:
            reply = f"❌ Error: {e}"

    elif cmd == 'mute':
        try:
            url = f"https://api.telegram.org/bot{token}/restrictChatMember"
            params = {
                'chat_id': chat_id,
                'user_id': target_id,
                'permissions': json.dumps({'can_send_messages': False})
            }
            r = requests.get(url, params=params, timeout=5)
            if r.json().get('ok'):
                reply = f"🔇 <b>{target_name}</b> has been muted."
            else:
                reply = f"❌ Failed to mute: {r.json().get('description')}"
        except Exception as e:
            reply = f"❌ Error: {e}"

    elif cmd == 'unmute':
        try:
            url = f"https://api.telegram.org/bot{token}/restrictChatMember"
            params = {
                'chat_id': chat_id,
                'user_id': target_id,
                'permissions': json.dumps({'can_send_messages': True})
            }
            r = requests.get(url, params=params, timeout=5)
            if r.json().get('ok'):
                reply = f"🔊 <b>{target_name}</b> has been unmuted."
            else:
                reply = f"❌ Failed to unmute: {r.json().get('description')}"
        except Exception as e:
            reply = f"❌ Error: {e}"

    elif cmd == 'warn':
        current_warn = get_warn_count(target_id, chat_id) + 1
        set_warn_count(target_id, chat_id, current_warn)
        warn_limit = int(get_mod_config('warn_limit') or 3)
        if current_warn >= warn_limit:
            try:
                url = f"https://api.telegram.org/bot{token}/banChatMember"
                params = {'chat_id': chat_id, 'user_id': target_id}
                requests.get(url, params=params, timeout=5)
                reply = f"🔨 <b>{target_name}</b> banned automatically (warn limit {warn_limit} reached)."
                delete_warn(target_id, chat_id)
            except Exception as e:
                reply = f"❌ Ban failed: {e}"
        else:
            reply = f"⚠️ <b>{target_name}</b> warned! ({current_warn}/{warn_limit})"

    elif cmd == 'warns':
        count = get_warn_count(target_id, chat_id)
        reply = f"📊 <b>{target_name}</b> has {count} warnings."

    elif cmd == 'delwarn':
        delete_warn(target_id, chat_id)
        reply = f"✅ Warnings for <b>{target_name}</b> have been reset."

    elif cmd == 'purge':
        if 'reply_to_message' in msg:
            del_id = msg['reply_to_message']['message_id']
            if delete_message(chat_id, del_id, token):
                reply = "🗑️ Message deleted."
            else:
                reply = "❌ Failed to delete."
        else:
            reply = "❌ Reply to a message to delete it."

    if reply:
        send_message(chat_id, reply, token)

# ========== মডারেশন ড্যাশবোর্ড ==========
@bp.route('/dashboard', methods=['GET', 'POST'])
def mod_dashboard():
    if request.method == 'POST':
        set_mod_config('anti_link', request.form.get('anti_link', 'off'))
        set_mod_config('auto_purge', request.form.get('auto_purge', 'off'))
        set_mod_config('warn_limit', request.form.get('warn_limit', '3'))
        words = request.form.get('bad_words', '')
        words_list = [w.strip() for w in words.split(',') if w.strip()]
        set_mod_config('bad_words', json.dumps(words_list))
        return redirect(url_for('moderation.mod_dashboard'))

    anti_link = get_mod_config('anti_link') == 'on'
    auto_purge = get_mod_config('auto_purge') == 'on'
    warn_limit = get_mod_config('warn_limit') or '3'
    bad_words = json.loads(get_mod_config('bad_words') or '[]')
    bad_words_str = ', '.join(bad_words)

    html = '''
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyber Tools MD – Moderation</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, sans-serif; }
        body { background:#0d1117; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
        .card { background:#161b22; border-radius:28px; padding:30px 24px; max-width:500px; width:100%; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid #30363d; }
        h1 { color:#f0f6fc; font-size:24px; margin-bottom:4px; }
        .sub { color:#8b949e; font-size:14px; margin-bottom:20px; }
        .divider { border:none; border-top:1px solid #30363d; margin:20px 0; }
        .toggle-item { display:flex; justify-content:space-between; align-items:center; background:#0d1117; padding:12px 16px; border-radius:14px; margin-bottom:10px; }
        .toggle-label { color:#c9d1d9; font-size:16px; font-weight:500; }
        .options label { color:#8b949e; font-size:15px; display:flex; align-items:center; gap:6px; cursor:pointer; }
        .options input[type="radio"] { accent-color:#1f6feb; width:18px; height:18px; cursor:pointer; }
        input[type="text"], input[type="number"] { width:100%; padding:10px; border-radius:10px; border:1px solid #30363d; background:#0d1117; color:#fff; margin-top:8px; }
        .save-btn { width:100%; background:#238636; color:#fff; border:none; padding:14px; border-radius:14px; font-size:17px; font-weight:600; cursor:pointer; margin-top:20px; }
        .save-btn:hover { background:#2ea043; }
        .footer { text-align:center; color:#484f58; font-size:12px; margin-top:20px; }
        .info-text { color:#8b949e; font-size:13px; margin-top:4px; }
        .back-link { display:inline-block; margin-top:10px; color:#58a6ff; text-decoration:none; font-size:14px; }
        .back-link:hover { text-decoration:underline; }
    </style>
    </head>
    <body>
    <div class="card">
        <h1>🛡️ Moderation Tools</h1>
        <div class="sub">Anti-Spam & Admin Controls</div>
        <hr class="divider">
        <form method="post">
            <div class="toggle-item">
                <span class="toggle-label">Anti-Link</span>
                <div class="options">
                    <label><input type="radio" name="anti_link" value="on" {{ "checked" if anti_link else "" }}> ON</label>
                    <label><input type="radio" name="anti_link" value="off" {{ "checked" if not anti_link else "" }}> OFF</label>
                </div>
            </div>
            <div class="toggle-item">
                <span class="toggle-label">Auto Purge (beta)</span>
                <div class="options">
                    <label><input type="radio" name="auto_purge" value="on" {{ "checked" if auto_purge else "" }}> ON</label>
                    <label><input type="radio" name="auto_purge" value="off" {{ "checked" if not auto_purge else "" }}> OFF</label>
                </div>
            </div>
            <div style="margin:10px 0;">
                <label style="color:#c9d1d9;">Bad Words (comma separated)</label>
                <input type="text" name="bad_words" placeholder="e.g. spam, porn, abuse" value="{{ bad_words_str }}">
                <div class="info-text">These words will trigger a warning + auto-delete.</div>
            </div>
            <div style="margin:10px 0;">
                <label style="color:#c9d1d9;">Warn Limit</label>
                <input type="number" name="warn_limit" value="{{ warn_limit }}" min="1" max="10">
            </div>
            <button type="submit" class="save-btn">Save Moderation Settings</button>
        </form>
        <div class="footer">Admins can use: /ban, /kick, /mute, /unmute, /warn, /warns, /delwarn, /purge (reply)</div>
        <a href="/bot/" class="back-link">← Back to Main Dashboard</a>
    </div>
    </body>
    </html>
    '''
    return render_template_string(html, anti_link=anti_link, auto_purge=auto_purge, 
                                  warn_limit=warn_limit, bad_words_str=bad_words_str)