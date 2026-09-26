from flask import Blueprint, request, redirect, render_template_string
import time
import threading
import requests
import json
import logging
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')

# ========== 🔑 আপনার বটের টোকেন ==========
BOT_TOKEN = "8193376363:AAFyMyVmK7gryI4H1ZxZOobwFt_wzeFwJrM"
BOT_LINK = "https://t.me/Arif1222_bot"
DASHBOARD_BASE = "https://vip-tools-backend.onrender.com"

# ========== MongoDB ==========
MONGO_URI = "mongodb+srv://Cyber_md_bot:cybermd123@cluster0.tre505e.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['cyber_tools']
group_col = db['group_settings']

# ========== অটো রিপ্লাই ==========
AUTO_REPLIES = {
    'hi': '<b>Hello!</b> <i>How are you?</i> 😊',
    'hello': '<b>Hello!</b> <i>How can I help?</i>',
    'good morning': '<b>🌅 Good Morning!</b> Have a great day!',
    'good night': '<b>🌙 Good Night!</b> Sleep well!',
    'how are you': '<i>I\'m just a bot, but I\'m doing fine!</i> 😄',
}

# ========== গ্রুপ সেটিংস ==========
def get_group(chat_id):
    return group_col.find_one({'chat_id': chat_id})

def get_group_setting(chat_id, key, default='off'):
    doc = group_col.find_one({'chat_id': chat_id})
    return doc.get(key, default) if doc else default

def set_group_setting(chat_id, key, value):
    group_col.update_one({'chat_id': chat_id}, {'$set': {key: value}}, upsert=True)

def register_group(chat_id, title):
    group_col.update_one(
        {'chat_id': chat_id},
        {
            '$set': {'title': title},
            '$setOnInsert': {
                'auto_react': 'off',
                'auto_welcome': 'off',
                'auto_reply': 'off',
                'moderation_enabled': 'off'
            }
        },
        upsert=True
    )

def get_all_groups():
    return list(group_col.find({}, {'chat_id': 1, 'title': 1}))

def remove_group(chat_id):
    group_col.delete_one({'chat_id': chat_id})

# ========== বটের আইডি ==========
BOT_ID = None

def fetch_bot_id():
    global BOT_ID
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        if r.json().get('ok'):
            BOT_ID = r.json()['result']['id']
            logger.info(f"✅ Bot ID: {BOT_ID}")
    except Exception as e:
        logger.error(f"Bot ID fetch error: {e}")

# ========== ড্যাশবোর্ড রাউট ==========
@bp.route('/', methods=['GET', 'POST'])
def dashboard():
    chat_id = request.args.get('chat_id', type=int)

    if request.method == 'POST' and chat_id:
        set_group_setting(chat_id, 'auto_react', request.form.get('auto_react', 'off'))
        set_group_setting(chat_id, 'auto_welcome', request.form.get('auto_welcome', 'off'))
        set_group_setting(chat_id, 'auto_reply', request.form.get('auto_reply', 'off'))
        set_group_setting(chat_id, 'moderation_enabled', request.form.get('moderation_enabled', 'off'))
        return redirect(f'/bot/?chat_id={chat_id}')

    if not chat_id:
        groups = get_all_groups()
        return render_template_string(GROUP_LIST_HTML, groups=groups, bot_link=BOT_LINK)

    group = get_group(chat_id)
    if not group:
        return "<h2 style='color:red;'>❌ Group not found. <a href='/bot/'>Go Back</a></h2>"

    status = {
        'auto_react': group.get('auto_react', 'off') == 'on',
        'auto_welcome': group.get('auto_welcome', 'off') == 'on',
        'auto_reply': group.get('auto_reply', 'off') == 'on',
        'moderation_enabled': group.get('moderation_enabled', 'off') == 'on',
    }
    return render_template_string(
        DASHBOARD_HTML,
        status=status,
        chat_id=chat_id,
        title=group.get('title', 'Unknown Group')
    )

# ========== 🗑️ গ্রুপ ডিলিট রাউট ==========
@bp.route('/delete_group', methods=['POST'])
def delete_group():
    chat_id = request.form.get('chat_id', type=int)
    if chat_id:
        remove_group(chat_id)
        logger.info(f"🗑️ Deleted group {chat_id} from dashboard")
    return redirect('/bot/')

# ========== HTML: গ্রুপ লিস্ট (ডিলিট বাটনসহ) ==========
GROUP_LIST_HTML = '''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cyber Tools MD – Groups</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, sans-serif; }
body { background:#0d1117; display:flex; justify-content:center; align-items:flex-start; min-height:100vh; padding:20px; }
.card { background:#161b22; border-radius:28px; padding:30px 24px; max-width:500px; width:100%; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid #30363d; margin-top:30px; }
h1 { color:#f0f6fc; font-size:24px; margin-bottom:4px; }
.sub { color:#8b949e; font-size:14px; margin-bottom:20px; }
.badge { display:inline-block; background:#238636; color:#fff; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:500; margin-bottom:20px; }
.btn-open { display:block; background:#1f6feb; color:#fff; text-align:center; padding:14px; border-radius:14px; font-size:17px; font-weight:600; text-decoration:none; margin-bottom:24px; }
.btn-open:hover { background:#388bfd; }
.divider { border:none; border-top:1px solid #30363d; margin:20px 0; }
.group-row { display:flex; gap:8px; margin-bottom:10px; align-items:stretch; }
.group-item { flex:1; display:flex; justify-content:space-between; align-items:center; background:#0d1117; padding:14px 18px; border-radius:14px; text-decoration:none; color:#c9d1d9; border:1px solid #21262d; transition:all 0.2s; }
.group-item:hover { background:#1c2333; border-color:#58a6ff; }
.group-title { font-weight:500; font-size:15px; color:#f0f6fc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.group-arrow { color:#58a6ff; font-size:18px; margin-left:8px; }
.delete-btn { background:#21262d; color:#f85149; border:1px solid #30363d; padding:0 16px; border-radius:14px; font-size:16px; cursor:pointer; transition:all 0.2s; }
.delete-btn:hover { background:#f85149; color:#fff; border-color:#f85149; }
.empty { text-align:center; color:#8b949e; padding:30px 10px; font-size:14px; line-height:1.7; }
.footer { text-align:center; color:#484f58; font-size:12px; margin-top:20px; }
</style>
</head>
<body>
<div class="card">
    <h1>🛡️ Cyber Tools MD</h1>
    <div class="sub">Select a group to configure</div>
    <div class="badge">● Active</div>
    <a href="{{ bot_link }}" target="_blank" class="btn-open">📱 Open Bot</a>
    <hr class="divider">
    {% if groups %}
        {% for g in groups %}
        <div class="group-row">
            <a href="/bot/?chat_id={{ g.chat_id }}" class="group-item">
                <span class="group-title">🏠 {{ g.title or 'Unnamed Group' }}</span>
                <span class="group-arrow">→</span>
            </a>
            <form method="post" action="/bot/delete_group" style="margin:0;" onsubmit="return confirm('Are you sure you want to delete this group?');">
                <input type="hidden" name="chat_id" value="{{ g.chat_id }}">
                <button type="submit" class="delete-btn" title="Delete">🗑️</button>
            </form>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty">
            📭 No groups yet.<br>
            Add <b>@Arif1222_bot</b> to a Telegram group<br>to get started.
        </div>
    {% endif %}
    <div class="footer">🛡️ Cyber Tools MD</div>
</div>
</body>
</html>
'''

# ========== HTML: নির্দিষ্ট গ্রুপের ড্যাশবোর্ড ==========
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} – Dashboard</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, sans-serif; }
body { background:#0d1117; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
.card { background:#161b22; border-radius:28px; padding:30px 24px; max-width:450px; width:100%; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid #30363d; }
h1 { color:#f0f6fc; font-size:22px; margin-bottom:4px; word-break:break-word; }
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
.top-bar { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.back-link { color:#58a6ff; text-decoration:none; font-size:14px; }
.back-link:hover { text-decoration:underline; }
.delete-top { background:#21262d; color:#f85149; border:1px solid #30363d; padding:6px 14px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; }
.delete-top:hover { background:#f85149; color:#fff; border-color:#f85149; }
.mod-link { display:inline-block; margin-top:10px; color:#58a6ff; text-decoration:none; font-size:14px; }
.mod-link:hover { text-decoration:underline; }
</style>
</head>
<body>
<div class="card">
    <div class="top-bar">
        <a href="/bot/" class="back-link">← All Groups</a>
        <form method="post" action="/bot/delete_group" style="margin:0;" onsubmit="return confirm('Delete this group from dashboard?');">
            <input type="hidden" name="chat_id" value="{{ chat_id }}">
            <button type="submit" class="delete-top">🗑️ Delete</button>
        </form>
    </div>
    <h1>🛡️ {{ title }}</h1>
    <div class="sub">Group Control Panel</div>
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
        <div class="toggle-item">
            <span class="toggle-label">🛡️ Moderation</span>
            <div class="toggle-options">
                <label><input type="radio" name="moderation_enabled" value="on" {{ 'checked' if status.moderation_enabled else '' }}> ON</label>
                <label><input type="radio" name="moderation_enabled" value="off" {{ 'checked' if not status.moderation_enabled else '' }}> OFF</label>
            </div>
        </div>
        <button type="submit" class="save-btn">Save Settings</button>
    </form>
    <a href="/bot/mod/dashboard?chat_id={{ chat_id }}" class="mod-link">⚙️ Advanced Moderation Settings →</a>
    <div class="footer">🛡️ Cyber Tools MD</div>
</div>
</body>
</html>
'''

# ========== বট ফাংশন ==========
def send_message(chat_id, text, parse_mode='HTML'):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}, timeout=5)
        return r.json().get('ok', False)
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

def send_reactions(chat_id, message_id):
    setting = get_group_setting(chat_id, 'auto_react')
    logger.info(f"🔍 React check: chat_id={chat_id}, auto_react='{setting}'")
    if setting != 'on':
        return
    emojis = ["👍", "❤️", "🔥"]
    try:
        reaction_list = [{"type": "emoji", "emoji": e} for e in emojis]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {'chat_id': chat_id, 'message_id': message_id, 'reaction': json.dumps(reaction_list)}
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if data.get('ok'):
            logger.info(f"✅ Reactions sent to {message_id}")
        else:
            logger.error(f"❌ React failed: {data}")
    except Exception as e:
        logger.error(f"❌ React exception: {e}")

processed_messages = set()

def handle_auto_reply(msg):
    chat_id = msg['chat']['id']
    if get_group_setting(chat_id, 'auto_reply') != 'on':
        return
    text = msg.get('text', '').lower().strip()
    if not text:
        return
    message_id = msg['message_id']
    if message_id in processed_messages:
        return
    processed_messages.add(message_id)
    for keyword, reply in AUTO_REPLIES.items():
        if keyword in text:
            send_message(chat_id, reply)
            break

def handle_welcome(msg):
    chat_id = msg['chat']['id']
    if get_group_setting(chat_id, 'auto_welcome') != 'on':
        return
    if 'new_chat_members' not in msg:
        return
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
Open /bot/ on the website to control this group.

<b>💬 Auto Reply:</b>
I reply to hi, good morning, good night, etc. (if enabled in your group)."""
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

# ========== মডারেশন (অপশনাল) ==========
MODERATION_AVAILABLE = False
try:
    from md_tools import moderation
    MODERATION_AVAILABLE = True
    bp.register_blueprint(moderation.bp)
    logger.info("✅ moderation loaded")
except Exception as e:
    logger.warning(f"⚠️ moderation not loaded: {e}")

# ========== পোলিং ==========
def polling_worker():
    logger.info("🔄 Polling thread started.")
    fetch_bot_id()
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
                if data.get('error_code') == 409:
                    logger.warning("⚠️ 409 Conflict – retry...")
                else:
                    logger.error(f"API error: {data}")
                time.sleep(5)
                continue

            for update in data.get('result', []):
                last_update_id = update['update_id']
                msg = update.get('message')
                if not msg:
                    continue

                chat_id = msg['chat']['id']
                chat_type = msg['chat'].get('type')
                chat_title = msg['chat'].get('title', 'Private Chat')

                if chat_type in ('group', 'supergroup'):
                    register_group(chat_id, chat_title)

                if 'new_chat_members' in msg:
                    for member in msg['new_chat_members']:
                        if BOT_ID and member.get('id') == BOT_ID:
                            register_group(chat_id, chat_title)
                            send_message(
                                chat_id,
                                f"🛡️ <b>Thanks for adding me!</b>\n\n"
                                f"Configure this group here:\n"
                                f"<a href='{DASHBOARD_BASE}/bot/?chat_id={chat_id}'>"
                                f"👉 Open Dashboard</a>"
                            )
                            logger.info(f"✅ Bot added to group: {chat_title} ({chat_id})")

                if 'left_chat_member' in msg:
                    if BOT_ID and msg['left_chat_member'].get('id') == BOT_ID:
                        remove_group(chat_id)
                        logger.info(f"❌ Bot removed from group: {chat_id}")

                logger.info(f"📩 Received: {msg.get('text', '[non-text]')}")
                send_reactions(chat_id, msg['message_id'])
                handle_commands(msg)
                handle_auto_reply(msg)
                handle_welcome(msg)

                if MODERATION_AVAILABLE and get_group_setting(chat_id, 'moderation_enabled') == 'on':
                    try:
                        moderation.handle_moderation(msg, BOT_TOKEN)
                        moderation.handle_admin_commands(msg, BOT_TOKEN)
                    except Exception as e:
                        logger.error(f"Moderation error: {e}")

            time.sleep(1)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

polling_started = False

def start_polling_thread():
    global polling_started
    if polling_started:
        return
    threading.Thread(target=polling_worker, daemon=True).start()
    polling_started = True
    logger.info("🚀 Polling thread started.")

start_polling_thread()
logger.info("✅ md_bot module loaded.")
