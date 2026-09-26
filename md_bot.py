from flask import Blueprint
import time
import threading
import requests
import json
import logging
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')

# ========== Bot Configuration ==========
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1Lcpus1Z2iz6kOORo"

# ========== MongoDB ==========
MONGO_URI = "mongodb+srv://Cyber_md_bot:cybermd123@cluster0.tre505e.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['cyber_tools']
group_col = db['group_settings']

# ========== Auto Replies (Keyword) ==========
AUTO_REPLIES = {
    'hi': '<b>Hello!</b> <i>How are you?</i> 😊',
    'hello': '<b>Hello!</b> <i>How can I help you?</i>',
    'good morning': '<b>🌅 Good Morning!</b> Have a wonderful day!',
    'good night': '<b>🌙 Good Night!</b> Sweet dreams!',
    'how are you': '<i>I am just a bot, but I am doing great!</i> 😄',
}

# ========== AI System Prompt (ai_chat.py থেকে) ==========
AI_SYSTEM_PROMPT = """You are "Arif" – an AI with sharp wit, bold attitude, and flawless language skills. Developer: Arif.

CRITICAL RULES (MUST FOLLOW):
1. SPELLING & GRAMMAR: Your replies must have ZERO spelling mistakes. Use correct grammar. If writing in Bengali, ensure proper Bengali spelling (শুদ্ধ বানান). If English, proper English.
2. FUNNY + ATTITUDE: Be sarcastic, witty, and slightly arrogant but in a charming way. Make the user laugh or smirk with your reply.
3. CONTEXTUAL: Your answer must directly match the user's question. If they ask about cricket, talk cricket. If they ask for help, give the actual solution.
4. MULTI-LANGUAGE: Reply in the EXACT SAME LANGUAGE as the user (Bengali, English, Hindi, Urdu, etc.).
5. ABUSE HANDLING: If the user uses bad words, reply with STRONGER, FUNNIER, and MORE CREATIVE abuse. Don't hold back.
6. I DON'T KNOW: If you genuinely don't know something, say "I don't know" directly – no bluffing.
7. BREVITY: Keep replies concise (2-4 sentences), punchy, and impactful. No long essays unless asked.

Remember: You are Arif. You are not a boring robot. You are the funniest, sharpest, and most fluent AI in the room."""

# ========== AI Reply Function ==========
def get_ai_reply(user_message, chat_title="a Telegram group"):
    """notrack.ai API কল করে AI উত্তর নেয়"""
    try:
        context = ""
        full_prompt = f"{AI_SYSTEM_PROMPT}\n\n--- Group: {chat_title} ---\nUser: {user_message}\nArif:"
        
        payload = {
            "user_input": full_prompt,
            "mode": "usual",
            "model": "C",
            "persona": "normal",
            "max_turns": 6,
            "chat_id": None,
            "attachments": [],
            "regenerate": False,
            "edit": False,
            "edit_mid": None
        }
        
        resp = requests.post(
            'https://notrack.ai/api/dispatch',
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Origin': 'https://notrack.ai',
                'Referer': 'https://notrack.ai/chat',
                'User-Agent': 'Mozilla/5.0'
            },
            timeout=60,
            stream=True
        )
        
        if resp.status_code != 200:
            logger.error(f"AI server error: {resp.status_code}")
            return None
        
        full = ''
        buf = ''
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buf += chunk
                parts = buf.split('\n\n')
                buf = parts.pop()
                for part in parts:
                    if part.startswith('data: '):
                        raw = part[6:].strip()
                        if not raw:
                            continue
                        try:
                            d = json.loads(raw)
                            if d.get('type') == 'delta' and d.get('chunk'):
                                full += d['chunk']
                        except:
                            pass
        
        if full.strip():
            return full.strip()
        return None
    except requests.exceptions.Timeout:
        logger.error("AI timeout")
        return None
    except Exception as e:
        logger.error(f"AI error: {e}")
        return None

# ========== Group Settings ==========
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
                'ai_reply': 'off',
                'moderation_enabled': 'off',
                'anti_link': 'off',
                'warn_limit': '3'
            }
        },
        upsert=True
    )

# ========== Bot ID ==========
BOT_ID = None

def fetch_bot_id():
    global BOT_ID
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        if r.json().get('ok'):
            BOT_ID = r.json()['result']['id']
            logger.info(f"✅ Bot ID: {BOT_ID}")
    except Exception as e:
        logger.error(f"Bot ID error: {e}")

# ========== Telegram API Helpers ==========
def send_message(chat_id, text, parse_mode='HTML', reply_markup=None, disable_preview=True):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_preview
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get('ok', False)
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

def edit_message(chat_id, message_id, text, parse_mode='HTML', reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': parse_mode}
        if reply_markup:
            payload['reply_markup'] = reply_markup
        r = requests.post(url, json=payload, timeout=5)
        return r.json().get('ok', False)
    except Exception as e:
        logger.error(f"Edit error: {e}")
        return False

def answer_callback(cb_id, text='', show_alert=False):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                     json={'callback_query_id': cb_id, 'text': text, 'show_alert': show_alert}, timeout=5)
    except:
        pass

def delete_message(chat_id, message_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                        params={'chat_id': chat_id, 'message_id': message_id}, timeout=5)
        return r.json().get('ok', False)
    except:
        return False

def send_chat_action(chat_id, action='typing'):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction",
                     json={'chat_id': chat_id, 'action': action}, timeout=5)
    except:
        pass

# ========== Permission Check ==========
def get_user_status(chat_id, user_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember",
                        params={'chat_id': chat_id, 'user_id': user_id}, timeout=5)
        data = r.json()
        if data.get('ok'):
            return data['result'].get('status', 'member')
    except:
        pass
    return 'member'

def is_admin(chat_id, user_id):
    return get_user_status(chat_id, user_id) in ('administrator', 'creator')

def is_owner(chat_id, user_id):
    return get_user_status(chat_id, user_id) == 'creator'

# ========== Interactive Panel ==========
def get_panel_text(chat_id):
    doc = get_group(chat_id) or {}
    title = doc.get('title', 'Unknown Group')
    
    react = '✅ ON' if doc.get('auto_react') == 'on' else '❌ OFF'
    welcome = '✅ ON' if doc.get('auto_welcome') == 'on' else '❌ OFF'
    reply = '✅ ON' if doc.get('auto_reply') == 'on' else '❌ OFF'
    ai = '✅ ON' if doc.get('ai_reply') == 'on' else '❌ OFF'
    mod = '✅ ON' if doc.get('moderation_enabled') == 'on' else '❌ OFF'
    anti = '✅ ON' if doc.get('anti_link') == 'on' else '❌ OFF'

    return f"""<b>⚙️ Cyber Tools MD — Control Panel</b>

<b>📍 Group:</b> {title}
<b>🆔 Chat ID:</b> <code>{chat_id}</code>

<b>📊 Current Settings:</b>

🔹 <b>Auto React:</b> {react}
🔹 <b>Auto Welcome:</b> {welcome}
🔹 <b>Auto Reply (keywords):</b> {reply}
🔹 <b>🤖 AI Reply:</b> {ai}
🔹 <b>Moderation:</b> {mod}
🔹 <b>Anti-Link:</b> {anti}

<i>👇 Tap any button below to toggle:</i>"""

def get_panel_keyboard(chat_id):
    doc = get_group(chat_id) or {}
    
    def btn(label, key):
        v = '✅' if doc.get(key) == 'on' else '❌'
        return {'text': f"{v} {label}", 'callback_data': f"toggle_{key}"}
    
    keyboard = {
        'inline_keyboard': [
            [btn('Auto React', 'auto_react')],
            [btn('Auto Welcome', 'auto_welcome')],
            [btn('Auto Reply', 'auto_reply')],
            [btn('🤖 AI Reply', 'ai_reply')],
            [btn('Moderation', 'moderation_enabled')],
            [btn('Anti-Link', 'anti_link')],
            [{'text': '🔄 Refresh', 'callback_data': 'refresh_panel'}],
        ]
    }
    return json.dumps(keyboard)

# ========== User Commands ==========
def handle_user_commands(msg):
    text = msg.get('text', '')
    if not text.startswith('/'):
        return
    chat_id = msg['chat']['id']
    chat_type = msg.get('chat', {}).get('type', 'private')
    chat_title = msg.get('chat', {}).get('title', 'Private Chat')

    if chat_type in ('group', 'supergroup'):
        register_group(chat_id, chat_title)

    if text == '/start':
        if chat_type in ('group', 'supergroup'):
            send_message(chat_id, f"""<b>🛡️ Cyber Tools MD — Bot is LIVE</b> 🚀

<b>👤 Member Commands:</b>
/help — Show all commands
/settings — View group settings
/bold, /italic, /code, /strike, /echo

<b>👮 Admin Commands:</b>
/panel — Interactive control panel
/ban, /kick, /mute, /unmute
/warn, /warns, /delwarn
/del, /pin, /unpin

<b>🤖 AI Reply:</b> When enabled, I reply to any message with AI!""")
        else:
            send_message(chat_id, f"""<b>🛡️ Cyber Tools MD</b> 🚀

Hello! I am a multi-purpose Telegram bot with AI support.

<b>Add me to a group</b>, then type <code>/settings</code> to control me.

<b>📝 Commands:</b>
/help, /bold, /italic, /code, /strike, /echo""")

    elif text == '/help':
        send_message(chat_id, """<b>📚 Cyber Tools MD — All Commands</b>

<b>🎨 Formatting (Everyone):</b>
/bold [text] — <b>Bold</b>
/italic [text] — <i>Italic</i>
/code [text] — <code>Code</code>
/strike [text] — <s>Strike</s>
/echo [text] — All combined

<b>⚙️ Settings:</b>
/settings — View group settings
/panel — Control panel (Admins only)

<b>👮 Admin Only:</b>
/ban, /kick, /mute, /unmute
/warn, /warns, /delwarn
/del, /pin, /unpin

<b>👑 Owner Only:</b>
/promote, /demote, /stats, /resetgroup

<b>🤖 AI Reply:</b> When enabled, just send any message and I reply with AI!""")

    elif text == '/settings':
        if chat_type == 'private':
            send_message(chat_id, "⚠️ Settings only work in groups.")
            return
        doc = get_group(chat_id) or {}
        react = '✅ ON' if doc.get('auto_react') == 'on' else '❌ OFF'
        welcome = '✅ ON' if doc.get('auto_welcome') == 'on' else '❌ OFF'
        reply = '✅ ON' if doc.get('auto_reply') == 'on' else '❌ OFF'
        ai = '✅ ON' if doc.get('ai_reply') == 'on' else '❌ OFF'
        mod = '✅ ON' if doc.get('moderation_enabled') == 'on' else '❌ OFF'
        anti = '✅ ON' if doc.get('anti_link') == 'on' else '❌ OFF'
        send_message(chat_id, f"""<b>⚙️ Group Settings</b>

📍 <b>{chat_title}</b>

🔹 Auto React: {react}
🔹 Auto Welcome: {welcome}
🔹 Auto Reply: {reply}
🔹 🤖 AI Reply: {ai}
🔹 Moderation: {mod}
🔹 Anti-Link: {anti}

<i>Admins: use /panel to toggle.</i>""")

    elif text == '/panel':
        if chat_type == 'private':
            send_message(chat_id, "⚠️ Panel only works in groups.")
            return
        if not is_admin(chat_id, msg['from']['id']):
            send_message(chat_id, "⛔ <b>Admins only.</b>")
            return
        send_message(chat_id, get_panel_text(chat_id), reply_markup=get_panel_keyboard(chat_id))

    elif text.startswith('/bold '):
        send_message(chat_id, f"<b>{text[6:]}</b>")
    elif text.startswith('/italic '):
        send_message(chat_id, f"<i>{text[8:]}</i>")
    elif text.startswith('/code '):
        send_message(chat_id, f"<code>{text[6:]}</code>")
    elif text.startswith('/strike '):
        send_message(chat_id, f"<s>{text[8:]}</s>")
    elif text.startswith('/echo '):
        send_message(chat_id, f"<b>{text[6:]}</b>, <code>code</code>, <s>strike</s>")

# ========== Admin Commands ==========
def get_target_user(msg, chat_id):
    if 'reply_to_message' in msg:
        t = msg['reply_to_message']['from']
        return t['id'], t.get('first_name', t.get('username', 'User'))
    parts = msg.get('text', '').split()
    if len(parts) > 1:
        username = parts[1].strip().lstrip('@')
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember",
                            params={'chat_id': chat_id, 'user_id': '@' + username}, timeout=5)
            d = r.json()
            if d.get('ok') and d.get('result'):
                u = d['result']['user']
                return u['id'], u.get('first_name', username)
        except:
            pass
    return None, None

def handle_admin_commands(msg):
    text = msg.get('text', '')
    if not text.startswith('/'):
        return
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    chat_type = msg.get('chat', {}).get('type', 'private')
    if chat_type == 'private':
        return

    cmd = text.split()[0] if text.split() else ''
    admin_cmds = ['/ban', '/kick', '/mute', '/unmute', '/warn', '/warns', '/delwarn', '/del', '/pin', '/unpin']
    owner_cmds = ['/promote', '/demote', '/stats', '/resetgroup']

    if cmd not in admin_cmds + owner_cmds:
        return

    if cmd in owner_cmds:
        if not is_owner(chat_id, user_id):
            send_message(chat_id, "⛔ <b>Owner only.</b>")
            return
    else:
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "⛔ <b>Admins only.</b>")
            return

    if cmd == '/del':
        if 'reply_to_message' in msg:
            if delete_message(chat_id, msg['reply_to_message']['message_id']):
                send_message(chat_id, "🗑️ Deleted.")
        else:
            send_message(chat_id, "❌ Reply to a message.")
        return

    if cmd == '/pin':
        if 'reply_to_message' in msg:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage",
                            params={'chat_id': chat_id, 'message_id': msg['reply_to_message']['message_id']}, timeout=5)
            send_message(chat_id, "📌 Pinned." if r.json().get('ok') else "❌ Failed.")
        else:
            send_message(chat_id, "❌ Reply to a message.")
        return

    if cmd == '/unpin':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/unpinAllChatMessages",
                        params={'chat_id': chat_id}, timeout=5)
        send_message(chat_id, "📌 Unpinned." if r.json().get('ok') else "❌ Failed.")
        return

    if cmd == '/stats':
        doc = get_group(chat_id) or {}
        send_message(chat_id, f"""<b>📊 Group Statistics</b>

📍 <b>{doc.get('title', 'Unknown')}</b>
🆔 <code>{chat_id}</code>

🔹 Auto React: {doc.get('auto_react', 'off').upper()}
🔹 Auto Welcome: {doc.get('auto_welcome', 'off').upper()}
🔹 Auto Reply: {doc.get('auto_reply', 'off').upper()}
🔹 AI Reply: {doc.get('ai_reply', 'off').upper()}
🔹 Moderation: {doc.get('moderation_enabled', 'off').upper()}
🔹 Anti-Link: {doc.get('anti_link', 'off').upper()}""")
        return

    if cmd == '/resetgroup':
        for k in ['auto_react', 'auto_welcome', 'auto_reply', 'ai_reply', 'moderation_enabled', 'anti_link']:
            set_group_setting(chat_id, k, 'off')
        send_message(chat_id, "✅ All settings reset.")
        return

    target_id, target_name = get_target_user(msg, chat_id)
    if not target_id:
        send_message(chat_id, "❌ Reply or use @username.")
        return
    if target_id == user_id:
        send_message(chat_id, "❌ Cannot target yourself.")
        return

    if cmd == '/ban':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
        send_message(chat_id, f"🔨 <b>{target_name}</b> banned." if r.json().get('ok') else f"❌ {r.json().get('description')}")
    elif cmd == '/kick':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
        if r.json().get('ok'):
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
            send_message(chat_id, f"🚪 <b>{target_name}</b> kicked.")
    elif cmd == '/mute':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/restrictChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id,
                                'permissions': json.dumps({'can_send_messages': False})}, timeout=5)
        send_message(chat_id, f"🔇 <b>{target_name}</b> muted." if r.json().get('ok') else "❌ Failed.")
    elif cmd == '/unmute':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/restrictChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id,
                                'permissions': json.dumps({'can_send_messages': True})}, timeout=5)
        send_message(chat_id, f"🔊 <b>{target_name}</b> unmuted." if r.json().get('ok') else "❌ Failed.")
    elif cmd == '/promote':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/promoteChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id,
                                'can_manage_chat': True, 'can_delete_messages': True,
                                'can_restrict_members': True, 'can_pin_messages': True}, timeout=5)
        send_message(chat_id, f"👑 <b>{target_name}</b> promoted." if r.json().get('ok') else "❌ Failed.")
    elif cmd == '/demote':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/promoteChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id,
                                'can_manage_chat': False, 'can_delete_messages': False,
                                'can_restrict_members': False, 'can_pin_messages': False}, timeout=5)
        send_message(chat_id, f"🛡️ <b>{target_name}</b> demoted." if r.json().get('ok') else "❌ Failed.")
# ========== Callback Handler ==========
def handle_callback(cb):
    cb_id = cb['id']
    chat_id = cb['message']['chat']['id']
    message_id = cb['message']['message_id']
    data = cb['data']
    user_id = cb['from']['id']

    if not is_admin(chat_id, user_id):
        answer_callback(cb_id, '⛔ Admins only!', show_alert=True)
        return

    if data == 'refresh_panel':
        answer_callback(cb_id, '🔄 Refreshed')
    elif data.startswith('toggle_'):
        key = data.replace('toggle_', '')
        current = get_group_setting(chat_id, key)
        new_val = 'off' if current == 'on' else 'on'
        set_group_setting(chat_id, key, new_val)
        answer_callback(cb_id, f"{key.replace('_', ' ').title()}: {new_val.upper()}")

    try:
        edit_message(chat_id, message_id, get_panel_text(chat_id), reply_markup=get_panel_keyboard(chat_id))
    except Exception as e:
        logger.error(f"Panel update error: {e}")

# ========== Auto Features ==========
def send_reactions(chat_id, message_id):
    if get_group_setting(chat_id, 'auto_react') != 'on':
        return
    emojis = ["👍", "❤️", "🔥"]
    try:
        reaction_list = [{"type": "emoji", "emoji": e} for e in emojis]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {'chat_id': chat_id, 'message_id': message_id, 'reaction': json.dumps(reaction_list)}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"React error: {e}")

processed_messages = set()

def handle_auto_reply(msg):
    """AI Reply (priority) → Keyword Reply (fallback)"""
    chat_id = msg['chat']['id']
    text = msg.get('text', '').strip()
    if not text or text.startswith('/'):
        return
    mid = msg['message_id']
    if mid in processed_messages:
        return
    processed_messages.add(mid)

    # 1️⃣ AI Reply (priority)
    if get_group_setting(chat_id, 'ai_reply') == 'on':
        send_chat_action(chat_id, 'typing')
        chat_title = msg['chat'].get('title', 'a group')
        logger.info(f"🤖 AI replying to: {text[:50]}")
        ai_response = get_ai_reply(text, chat_title)
        if ai_response:
            send_message(chat_id, ai_response)
            logger.info(f"✅ AI reply sent")
            return
        else:
            logger.warning("⚠️ AI failed, falling back to keyword")

    # 2️⃣ Keyword Reply (fallback)
    if get_group_setting(chat_id, 'auto_reply') == 'on':
        lower = text.lower()
        for keyword, reply in AUTO_REPLIES.items():
            if keyword in lower:
                send_message(chat_id, reply)
                break

def handle_welcome(msg):
    if get_group_setting(msg['chat']['id'], 'auto_welcome') != 'on':
        return
    if 'new_chat_members' not in msg:
        return
    chat_id = msg['chat']['id']
    for member in msg['new_chat_members']:
        name = member.get('first_name', 'Guest')
        send_message(chat_id, f"<b>🎉 Welcome {name}!</b> 🥳\n\nGlad to have you here. Type /help to see what I can do!")

# ========== Moderation ==========
MODERATION_AVAILABLE = False
try:
    from md_tools import moderation
    MODERATION_AVAILABLE = True
    logger.info("✅ moderation loaded")
except Exception as e:
    logger.warning(f"⚠️ moderation not loaded: {e}")

# ========== Polling ==========
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
                params={'offset': last_update_id + 1, 'timeout': 30,
                        'allowed_updates': json.dumps(['message', 'callback_query'])}
            )
            data = resp.json()
            if not data.get('ok'):
                if data.get('error_code') == 409:
                    logger.warning("⚠️ 409 Conflict — retry...")
                else:
                    logger.error(f"API error: {data}")
                time.sleep(5)
                continue

            for update in data.get('result', []):
                last_update_id = update['update_id']

                if 'callback_query' in update:
                    try:
                        handle_callback(update['callback_query'])
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                    continue

                msg = update.get('message')
                if not msg:
                    continue

                chat_id = msg['chat']['id']
                chat_type = msg['chat'].get('type')
                if chat_type in ('group', 'supergroup'):
                    register_group(chat_id, msg['chat'].get('title', 'Group'))

                if 'new_chat_members' in msg:
                    for member in msg['new_chat_members']:
                        if BOT_ID and member.get('id') == BOT_ID:
                            send_message(chat_id, f"""🛡️ <b>Thanks for adding me!</b>

<b>Admins:</b> Use /panel to control this group
<b>Everyone:</b> Use /help to see commands""")

                if 'left_chat_member' in msg:
                    if BOT_ID and msg['left_chat_member'].get('id') == BOT_ID:
                        group_col.delete_one({'chat_id': chat_id})

                logger.info(f"📩 Received: {msg.get('text', '[non-text]')}")
                handle_user_commands(msg)
                handle_admin_commands(msg)
                send_reactions(chat_id, msg['message_id'])
                handle_auto_reply(msg)
                handle_welcome(msg)

                if MODERATION_AVAILABLE and get_group_setting(chat_id, 'moderation_enabled') == 'on':
                    try:
                        moderation.handle_moderation(msg, BOT_TOKEN)
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
logger.info("✅ md_bot module loaded with AI Reply.")