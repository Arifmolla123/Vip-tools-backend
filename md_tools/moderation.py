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
def ensure_mod_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS mod_config (key TEXT PRIMARY KEY, value TEXT)')
    defaults = {
        'anti_link': 'off',
        'bad_words': '[]',
        'warn_limit': '3',
        'auto_purge': 'off'
    }
    for key, val in defaults.items():
        c.execute("INSERT OR IGNORE INTO mod_config (key, value) VALUES (?, ?)", (key, val))
    c.execute('''CREATE TABLE IF NOT EXISTS warnings 
                 (user_id INTEGER, chat_id INTEGER, count INTEGER, 
                 PRIMARY KEY (user_id, chat_id))''')
    conn.commit()
    conn.close()
ensure_mod_table()

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

# ========== অ্যাডমিন চেক ==========
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

# ========== লিংক ডিটেক্ট ==========
def is_link(text):
    patterns = [
        r'https?://\S+',
        r'www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}',
        r'[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(/\S*)?'
    ]
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False

# ========== মডারেশন হ্যান্ডলার ==========
def handle_moderation(msg, token):
    if not token:
        return
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    message_id = msg['message_id']
    text = msg.get('text', '')

    if is_admin(chat_id, user_id, token):
        logger.info(f"⏩ Admin/Owner {user_id} skipped moderation")
        return

    if get_mod_config('anti_link') == 'on' and is_link(text):
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
                        r = requests.get(url, params=params, timeout=5)
                        if r.json().get('ok'):
                            send_message(chat_id, f"🔨 <b>User banned!</b> Reason: Exceeded warning limit ({warn_limit}).", token)
                            delete_warn(user_id, chat_id)
                        else:
                            send_message(chat_id, f"⚠️ Failed to ban user (maybe admin/owner).", token)
                    except Exception as e:
                        logger.error(f"Ban error: {e}")
                        send_message(chat_id, f"⚠️ Warning limit reached, but ban failed.", token)
                else:
                    send_message(chat_id, f"⚠️ <b>Warning {current_warn}/{warn_limit}</b>\nPlease avoid using bad words!", token)
                logger.info(f"⚠️ Warned {user_id} for bad word (count: {current_warn})")
                return True
        except Exception as e:
            logger.error(f"Bad word filter error: {e}")

    return False

# ========== অ্যাডমিন কমান্ড ==========
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
                r = requests.get(url, params=params, timeout=5)
                if r.json().get('ok'):
                    reply = f"🔨 <b>{target_name}</b> banned automatically (warn limit {warn_limit} reached)."
                    delete_warn(target_id, chat_id)
                else:
                    reply = f"⚠️ Cannot ban {target_name} (maybe owner)."
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

# ========== ড্যাশবোর্ড (সেভ ফিক্স) ==========
@bp.route('/dashboard', methods=['GET', 'POST'])
def mod_dashboard():
    if request.method == 'POST':
        try:
            set_mod_config('anti_link', request.form.get('anti_link', 'off'))
            set_mod_config('auto_purge', request.form.get('auto_purge', 'off'))
            set_mod_config('warn_limit', request.form.get('warn_limit', '3'))
            words = request.form.get('bad_words', '')
            words_list = [w.strip() for w in words.split(',') if w.strip()]
            set_mod_config('bad_words', json.dumps(words_list))
            # 🔥 সরাসরি URL রিডাইরেক্ট (ব্লুপ্রিন্ট সমস্যা এড়াতে)
            return redirect('/bot/mod/dashboard')
        except Exception as e:
            logger.error(f"Error saving: {e}")
            return f"<h2 style='color:red;'>Error: {e}</h2><a href='/bot/mod/dashboard'>Go Back</a>"

    anti_link = get_mod_config('anti_link') == 'on'
    auto_purge = get_mod_config('auto_purge') == 'on'
    warn_limit = get_mod_config('warn_limit') or '3'
    bad_words = json.loads(get_mod_config('bad_words') or '[]')
    bad_words_str = ', '.join(bad_words)

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Cyber Tools MD – Moderation</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background:#0b0e14; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
            .glass-card { background:rgba(22,27,34,0.85); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px); border-radius:40px; padding:32px 28px; max-width:520px; width:100%; border:1px solid rgba(48,54,61,0.6); box-shadow:0 25px 50px -12px rgba(0,0,0,0.8); }
            .header { display:flex; align-items:center; gap:14px; margin-bottom:8px; }
            .header-icon { background:linear-gradient(135deg,#1f6feb,#58a6ff); width:52px; height:52px; border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:28px; box-shadow:0 8px 16px rgba(31,111,235,0.3); }
            h1 { color:#f0f6fc; font-size:26px; font-weight:700; letter-spacing:-0.5px; }
            .sub { color:#8b949e; font-size:14px; margin-left:66px; margin-top:-6px; margin-bottom:24px; }
            .badge-group { display:flex; gap:10px; margin-bottom:24px; flex-wrap:wrap; }
            .badge { background:#1c2333; padding:6px 16px; border-radius:40px; font-size:13px; font-weight:500; color:#c9d1d9; border:1px solid #30363d; }
            .badge-active { background:#238636; color:#fff; border-color:#238636; }
            .divider { border:none; border-top:1px solid #21262d; margin:20px 0 24px 0; }
            .control-item { background:#0d1117; border-radius:20px; padding:16px 18px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; border:1px solid #21262d; transition:border 0.2s; }
            .control-item:hover { border-color:#30363d; }
            .control-label { display:flex; align-items:center; gap:12px; color:#c9d1d9; font-weight:500; font-size:16px; }
            .control-label span { font-size:20px; }
            .toggle-group { display:flex; background:#161b22; border-radius:40px; padding:3px; border:1px solid #30363d; }
            .toggle-group label { padding:4px 14px; border-radius:30px; font-size:13px; font-weight:600; cursor:pointer; color:#8b949e; transition:all 0.2s; }
            .toggle-group input[type="radio"] { display:none; }
            .toggle-group input[type="radio"]:checked + label { background:#1f6feb; color:#fff; box-shadow:0 4px 8px rgba(31,111,235,0.3); }
            .input-field { background:#0d1117; border:1px solid #21262d; border-radius:16px; padding:14px 16px; width:100%; color:#f0f6fc; font-size:15px; transition:border 0.2s; margin-top:6px; }
            .input-field:focus { outline:none; border-color:#58a6ff; box-shadow:0 0 0 3px rgba(88,166,255,0.15); }
            .input-group { margin-bottom:18px; }
            .input-group label { color:#8b949e; font-size:14px; font-weight:500; display:block; margin-bottom:4px; }
            .helper-text { color:#484f58; font-size:12px; margin-top:6px; }
            .save-btn { background:linear-gradient(135deg,#238636,#2ea043); border:none; width:100%; padding:16px; border-radius:30px; font-size:17px; font-weight:700; color:#fff; cursor:pointer; transition:transform 0.1s, box-shadow 0.2s; margin-top:8px; box-shadow:0 8px 18px rgba(35,134,54,0.25); }
            .save-btn:hover { transform:scale(1.01); box-shadow:0 10px 24px rgba(35,134,54,0.4); }
            .save-btn:active { transform:scale(0.98); }
            .footer { display:flex; justify-content:space-between; align-items:center; margin-top:22px; color:#484f58; font-size:12px; border-top:1px solid #21262d; padding-top:18px; }
            .footer a { color:#58a6ff; text-decoration:none; font-weight:500; font-size:14px; }
            .footer a:hover { text-decoration:underline; }
            .info-box { background:#1c2333; border-left:4px solid #58a6ff; padding:12px 16px; border-radius:12px; margin-bottom:18px; font-size:13px; color:#c9d1d9; display:flex; align-items:center; gap:10px; }
            @media (max-width:480px) { .glass-card { padding:22px 16px; } .control-item { flex-wrap:wrap; gap:10px; } .control-label { width:100%; } .toggle-group { margin-left:auto; } }
        </style>
    </head>
    <body>
        <div class="glass-card">
            <div class="header">
                <div class="header-icon">🛡️</div>
                <h1>Moderation</h1>
            </div>
            <div class="sub">Control Panel • Advanced Security</div>
            <div class="badge-group">
                <span class="badge badge-active">● Active</span>
                <span class="badge">⚡ Real-time</span>
                <span class="badge">🔒 Admin/Owner exempt</span>
            </div>
            <div class="info-box">
                ℹ️ <span><b>Admins & Owner</b> are <b>NOT</b> affected by Anti-Link or Bad Words filters.</span>
            </div>
            <hr class="divider">
            <form method="post">
                <div class="control-item">
                    <span class="control-label"><span>🔗</span> Anti-Link</span>
                    <div class="toggle-group">
                        <input type="radio" name="anti_link" value="on" id="al_on" {{ 'checked' if anti_link else '' }}>
                        <label for="al_on">ON</label>
                        <input type="radio" name="anti_link" value="off" id="al_off" {{ 'checked' if not anti_link else '' }}>
                        <label for="al_off">OFF</label>
                    </div>
                </div>
                <div class="control-item">
                    <span class="control-label"><span>🧹</span> Auto Purge (beta)</span>
                    <div class="toggle-group">
                        <input type="radio" name="auto_purge" value="on" id="ap_on" {{ 'checked' if auto_purge else '' }}>
                        <label for="ap_on">ON</label>
                        <input type="radio" name="auto_purge" value="off" id="ap_off" {{ 'checked' if not auto_purge else '' }}>
                        <label for="ap_off">OFF</label>
                    </div>
                </div>
                <div class="input-group">
                    <label>🛑 Bad Words (comma separated)</label>
                    <input type="text" name="bad_words" class="input-field" placeholder="e.g. spam, abuse" value="{{ bad_words_str }}">
                    <div class="helper-text">These words will trigger auto-delete + warning (for non‑admins).</div>
                </div>
                <div class="input-group">
                    <label>⚠️ Warn Limit</label>
                    <input type="number" name="warn_limit" class="input-field" min="1" max="10" value="{{ warn_limit }}">
                    <div class="helper-text">Non‑admin users reaching this limit will be automatically banned.</div>
                </div>
                <button type="submit" class="save-btn">💾 Save Moderation Settings</button>
            </form>
            <div class="footer">
                <span>🔑 Token hidden for security</span>
                <a href="/bot/">← Back to Main</a>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, anti_link=anti_link, auto_purge=auto_purge, 
                                  warn_limit=warn_limit, bad_words_str=bad_words_str)
