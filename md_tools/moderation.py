from flask import Blueprint, request, redirect, render_template_string
import time
import re
import json
import logging
import requests
from pymongo import MongoClient

logger = logging.getLogger(__name__)
bp = Blueprint('moderation', __name__, url_prefix='/mod')

# ========== MongoDB ==========
MONGO_URI = "mongodb+srv://Cyber_md_bot:cybermd123@cluster0.tre505e.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['cyber_tools']
group_col = db['group_settings']
warn_col = db['warnings']

# ========== গ্রুপ-নির্দিষ্ট সেটিংস ==========
def get_mod_setting(chat_id, key, default='off'):
    doc = group_col.find_one({'chat_id': chat_id})
    return doc.get(key, default) if doc else default

def set_mod_setting(chat_id, key, value):
    group_col.update_one({'chat_id': chat_id}, {'$set': {key: value}}, upsert=True)

def get_warn_count(user_id, chat_id):
    doc = warn_col.find_one({'user_id': user_id, 'chat_id': chat_id})
    return doc['count'] if doc else 0

def set_warn_count(user_id, chat_id, count):
    warn_col.update_one(
        {'user_id': user_id, 'chat_id': chat_id},
        {'$set': {'count': count}}, upsert=True
    )

def delete_warn(user_id, chat_id):
    warn_col.delete_one({'user_id': user_id, 'chat_id': chat_id})

# ========== অ্যাডমিন চেক ==========
def is_admin(chat_id, user_id, token):
    try:
        url = f"https://api.telegram.org/bot{token}/getChatMember"
        r = requests.get(url, params={'chat_id': chat_id, 'user_id': user_id}, timeout=5)
        data = r.json()
        if data.get('ok'):
            return data['result'].get('status') in ('administrator', 'creator')
    except:
        pass
    return False

def delete_message(chat_id, message_id, token):
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/deleteMessage",
                         params={'chat_id': chat_id, 'message_id': message_id}, timeout=5)
        return r.json().get('ok', False)
    except:
        return False

def send_message(chat_id, text, token, parse_mode='HTML'):
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}, timeout=5)
        return r.json().get('ok', False)
    except:
        return False

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
        return

    if get_mod_setting(chat_id, 'anti_link') == 'on' and is_link(text):
        delete_message(chat_id, message_id, token)
        send_message(chat_id, "🚫 <b>Anti-Link:</b> Links are not allowed here!", token)
        return True

    if get_mod_setting(chat_id, 'bad_words') != '[]':
        try:
            bad_words_list = json.loads(get_mod_setting(chat_id, 'bad_words', '[]'))
            if any(word.lower() in text.lower() for word in bad_words_list):
                delete_message(chat_id, message_id, token)
                current_warn = get_warn_count(user_id, chat_id) + 1
                set_warn_count(user_id, chat_id, current_warn)
                warn_limit = int(get_mod_setting(chat_id, 'warn_limit', '3'))
                if current_warn >= warn_limit:
                    try:
                        r = requests.get(f"https://api.telegram.org/bot{token}/banChatMember",
                                         params={'chat_id': chat_id, 'user_id': user_id}, timeout=5)
                        if r.json().get('ok'):
                            send_message(chat_id, f"🔨 <b>User banned!</b> Warn limit ({warn_limit}) exceeded.", token)
                            delete_warn(user_id, chat_id)
                    except:
                        pass
                else:
                    send_message(chat_id, f"⚠️ <b>Warning {current_warn}/{warn_limit}</b>", token)
                return True
        except:
            pass
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
        username = parts[1].strip().lstrip('@')
        try:
            r = requests.get(f"https://api.telegram.org/bot{token}/getChatMember",
                             params={'chat_id': chat_id, 'user_id': '@' + username}, timeout=5)
            d = r.json()
            if d.get('ok') and d.get('result'):
                target_id = d['result']['user']['id']
                target_name = username
        except:
            pass

    if not target_id and cmd not in ['purge']:
        send_message(chat_id, "❌ Reply or use @username.", token)
        return

    if cmd == 'ban':
        try:
            r = requests.get(f"https://api.telegram.org/bot{token}/banChatMember",
                             params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
            if r.json().get('ok'):
                reply = f"🔨 <b>{target_name}</b> banned."
                delete_warn(target_id, chat_id)
            else:
                reply = f"❌ {r.json().get('description')}"
        except Exception as e:
            reply = f"❌ {e}"
    elif cmd == 'kick':
        try:
            r = requests.get(f"https://api.telegram.org/bot{token}/banChatMember",
                             params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
            if r.json().get('ok'):
                requests.get(f"https://api.telegram.org/bot{token}/unbanChatMember",
                             params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
                reply = f"🚪 <b>{target_name}</b> kicked."
                delete_warn(target_id, chat_id)
        except Exception as e:
            reply = f"❌ {e}"
    elif cmd == 'mute':
        r = requests.get(f"https://api.telegram.org/bot{token}/restrictChatMember",
                         params={'chat_id': chat_id, 'user_id': target_id,
                                 'permissions': json.dumps({'can_send_messages': False})}, timeout=5)
        reply = f"🔇 <b>{target_name}</b> muted." if r.json().get('ok') else f"❌ {r.json().get('description')}"
    elif cmd == 'unmute':
        r = requests.get(f"https://api.telegram.org/bot{token}/restrictChatMember",
                         params={'chat_id': chat_id, 'user_id': target_id,
                                 'permissions': json.dumps({'can_send_messages': True})}, timeout=5)
        reply = f"🔊 <b>{target_name}</b> unmuted." if r.json().get('ok') else f"❌ {r.json().get('description')}"
    elif cmd == 'warn':
        current = get_warn_count(target_id, chat_id) + 1
        set_warn_count(target_id, chat_id, current)
        limit = int(get_mod_setting(chat_id, 'warn_limit', '3'))
        reply = f"⚠️ <b>{target_name}</b> warned ({current}/{limit})"
    elif cmd == 'warns':
        reply = f"📊 <b>{target_name}</b> has {get_warn_count(target_id, chat_id)} warnings."
    elif cmd == 'delwarn':
        delete_warn(target_id, chat_id)
        reply = f"✅ Warnings reset for <b>{target_name}</b>."
    elif cmd == 'purge':
        if 'reply_to_message' in msg:
            if delete_message(chat_id, msg['reply_to_message']['message_id'], token):
                reply = "🗑️ Deleted."
            else:
                reply = "❌ Failed to delete."
        else:
            reply = "❌ Reply to a message."

    if reply:
        send_message(chat_id, reply, token)

# ========== মডারেশন ড্যাশবোর্ড (গ্রুপ-নির্দিষ্ট) ==========
@bp.route('/dashboard', methods=['GET', 'POST'])
def mod_dashboard():
    chat_id = request.args.get('chat_id', type=int)
    if not chat_id:
        return "<h2 style='color:red;'>❌ Missing chat_id. <a href='/bot/'>Go Back</a></h2>"

    if request.method == 'POST':
        set_mod_setting(chat_id, 'anti_link', request.form.get('anti_link', 'off'))
        set_mod_setting(chat_id, 'auto_purge', request.form.get('auto_purge', 'off'))
        set_mod_setting(chat_id, 'warn_limit', request.form.get('warn_limit', '3'))
        words = request.form.get('bad_words', '')
        words_list = [w.strip() for w in words.split(',') if w.strip()]
        set_mod_setting(chat_id, 'bad_words', json.dumps(words_list))
        return redirect(f'/bot/mod/dashboard?chat_id={chat_id}')

    anti_link = get_mod_setting(chat_id, 'anti_link') == 'on'
    auto_purge = get_mod_setting(chat_id, 'auto_purge') == 'on'
    warn_limit = get_mod_setting(chat_id, 'warn_limit', '3')
    bad_words = json.loads(get_mod_setting(chat_id, 'bad_words', '[]'))
    bad_words_str = ', '.join(bad_words)
    group = group_col.find_one({'chat_id': chat_id})
    title = group.get('title', 'Unknown') if group else 'Unknown'

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Moderation – {{ title }}</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background:#0b0e14; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
            .glass-card { background:rgba(22,27,34,0.85); backdrop-filter:blur(12px); border-radius:40px; padding:32px 28px; max-width:520px; width:100%; border:1px solid rgba(48,54,61,0.6); box-shadow:0 25px 50px -12px rgba(0,0,0,0.8); }
            .header { display:flex; align-items:center; gap:14px; margin-bottom:8px; }
            .header-icon { background:linear-gradient(135deg,#1f6feb,#58a6ff); width:52px; height:52px; border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:28px; box-shadow:0 8px 16px rgba(31,111,235,0.3); }
            h1 { color:#f0f6fc; font-size:22px; font-weight:700; word-break:break-word; }
            .sub { color:#8b949e; font-size:14px; margin-left:66px; margin-top:-6px; margin-bottom:24px; }
            .badge-group { display:flex; gap:10px; margin-bottom:24px; flex-wrap:wrap; }
            .badge { background:#1c2333; padding:6px 16px; border-radius:40px; font-size:13px; font-weight:500; color:#c9d1d9; border:1px solid #30363d; }
            .badge-active { background:#238636; color:#fff; border-color:#238636; }
            .divider { border:none; border-top:1px solid #21262d; margin:20px 0 24px 0; }
            .control-item { background:#0d1117; border-radius:20px; padding:16px 18px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; border:1px solid #21262d; }
            .control-item:hover { border-color:#30363d; }
            .control-label { display:flex; align-items:center; gap:12px; color:#c9d1d9; font-weight:500; font-size:16px; }
            .control-label span { font-size:20px; }
            .toggle-group { display:flex; background:#161b22; border-radius:40px; padding:3px; border:1px solid #30363d; }
            .toggle-group label { padding:4px 14px; border-radius:30px; font-size:13px; font-weight:600; cursor:pointer; color:#8b949e; transition:all 0.2s; }
            .toggle-group input[type="radio"] { display:none; }
            .toggle-group input[type="radio"]:checked + label { background:#1f6feb; color:#fff; box-shadow:0 4px 8px rgba(31,111,235,0.3); }
            .input-field { background:#0d1117; border:1px solid #21262d; border-radius:16px; padding:14px 16px; width:100%; color:#f0f6fc; font-size:15px; margin-top:6px; }
            .input-field:focus { outline:none; border-color:#58a6ff; box-shadow:0 0 0 3px rgba(88,166,255,0.15); }
            .input-group { margin-bottom:18px; }
            .input-group label { color:#8b949e; font-size:14px; font-weight:500; display:block; margin-bottom:4px; }
            .helper-text { color:#484f58; font-size:12px; margin-top:6px; }
            .save-btn { background:linear-gradient(135deg,#238636,#2ea043); border:none; width:100%; padding:16px; border-radius:30px; font-size:17px; font-weight:700; color:#fff; cursor:pointer; margin-top:8px; box-shadow:0 8px 18px rgba(35,134,54,0.25); }
            .save-btn:hover { transform:scale(1.01); box-shadow:0 10px 24px rgba(35,134,54,0.4); }
            .footer { display:flex; justify-content:space-between; align-items:center; margin-top:22px; color:#484f58; font-size:12px; border-top:1px solid #21262d; padding-top:18px; }
            .footer a { color:#58a6ff; text-decoration:none; font-weight:500; font-size:14px; }
            .footer a:hover { text-decoration:underline; }
            .back-link { display:inline-block; margin-bottom:16px; color:#58a6ff; text-decoration:none; font-size:14px; }
            .back-link:hover { text-decoration:underline; }
            .info-box { background:#1c2333; border-left:4px solid #58a6ff; padding:12px 16px; border-radius:12px; margin-bottom:18px; font-size:13px; color:#c9d1d9; display:flex; align-items:center; gap:10px; }
        </style>
    </head>
    <body>
        <div class="glass-card">
            <a href="/bot/?chat_id={{ chat_id }}" class="back-link">← Back to Group Settings</a>
            <div class="header">
                <div class="header-icon">🛡️</div>
                <h1>{{ title }}</h1>
            </div>
            <div class="sub">Advanced Moderation • Group Specific</div>
            <div class="badge-group">
                <span class="badge badge-active">● Active</span>
                <span class="badge">🔒 Admin/Owner exempt</span>
            </div>
            <div class="info-box">
                ℹ️ <span>These settings apply <b>only to this group</b>. Admins & Owner are NOT affected.</span>
            </div>
            <hr class="divider">
            <form method="post" action="/bot/mod/dashboard?chat_id={{ chat_id }}">
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
                    <input type="text" name="bad_words" class="input-field" placeholder="e.g. spam, porn, abuse" value="{{ bad_words_str }}">
                    <div class="helper-text">These words will trigger auto-delete + warning.</div>
                </div>
                <div class="input-group">
                    <label>⚠️ Warn Limit</label>
                    <input type="number" name="warn_limit" class="input-field" min="1" max="10" value="{{ warn_limit }}">
                    <div class="helper-text">Users reaching this limit will be auto-banned (except admins/owner).</div>
                </div>
                <button type="submit" class="save-btn">💾 Save Moderation Settings</button>
            </form>
            <div class="footer">
                <span>🛡️ Cyber Tools MD</span>
                <a href="/bot/">← All Groups</a>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(
        html,
        chat_id=chat_id,
        title=title,
        anti_link=anti_link,
        auto_purge=auto_purge,
        warn_limit=warn_limit,
        bad_words_str=bad_words_str
    )