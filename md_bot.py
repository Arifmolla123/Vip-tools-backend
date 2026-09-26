from flask import Blueprint
import time
import threading
import requests
import json
from md_tools.config import (
    BOT_TOKEN, BOT_ID, logger,
    register_group, group_col, is_admin, is_owner,
    send_message, delete_message, get_group_setting,
    get_user_status
)
from md_tools import ai_reply, auto_reply, welcome, reactions, panel

# Bot ID আপডেট করার জন্য গ্লোবাল
import md_tools.config as config

bp = Blueprint('md_bot', __name__, url_prefix='/bot')

def fetch_bot_id():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        if r.json().get('ok'):
            config.BOT_ID = r.json()['result']['id']
    except Exception as e:
        logger.error(f"Bot ID error: {e}")

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

Hello! Add me to a group, then type <code>/settings</code> to control me.

<b>📝 Commands:</b>
/help, /bold, /italic, /code, /strike, /echo""")

    elif text == '/help':
        send_message(chat_id, """<b>📚 All Commands</b>

<b>🎨 Formatting:</b>
/bold, /italic, /code, /strike, /echo

<b>⚙️ Settings:</b>
/settings — View group settings
/panel — Control panel (Admins)

<b>👮 Admin:</b>
/ban, /kick, /mute, /unmute
/warn, /warns, /delwarn
/del, /pin, /unpin

<b>👑 Owner:</b>
/promote, /demote, /stats, /resetgroup""")

    elif text == '/settings':
        if chat_type == 'private':
            send_message(chat_id, "⚠️ Settings only work in groups.")
            return
        from md_tools.config import get_group
        doc = get_group(chat_id) or {}
        react = '✅ ON' if doc.get('auto_react') == 'on' else '❌ OFF'
        welcome_s = '✅ ON' if doc.get('auto_welcome') == 'on' else '❌ OFF'
        reply = '✅ ON' if doc.get('auto_reply') == 'on' else '❌ OFF'
        ai = '✅ ON' if doc.get('ai_reply') == 'on' else '❌ OFF'
        mod = '✅ ON' if doc.get('moderation_enabled') == 'on' else '❌ OFF'
        anti = '✅ ON' if doc.get('anti_link') == 'on' else '❌ OFF'
        send_message(chat_id, f"""<b>⚙️ Group Settings</b>

📍 <b>{chat_title}</b>

🔹 Auto React: {react}
🔹 Auto Welcome: {welcome_s}
🔹 Auto Reply: {reply}
🔹 🤖 AI Reply: {ai}
🔹 Moderation: {mod}
🔹 Anti-Link: {anti}

<i>Admins: use /panel to toggle.</i>""")

    elif text == '/panel':
        if chat_type == 'private':
            send_message(chat_id, "⚠️ Panel only works in groups.")
            return
        panel.show_panel(chat_id, msg['from']['id'])

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
            delete_message(chat_id, msg['reply_to_message']['message_id'])
        return

    if cmd == '/pin':
        if 'reply_to_message' in msg:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage",
                        params={'chat_id': chat_id, 'message_id': msg['reply_to_message']['message_id']}, timeout=5)
        return

    if cmd == '/unpin':
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/unpinAllChatMessages",
                    params={'chat_id': chat_id}, timeout=5)
        return

    if cmd == '/stats':
        from md_tools.config import get_group
        doc = get_group(chat_id) or {}
        send_message(chat_id, f"""<b>📊 Group Statistics</b>

📍 <b>{doc.get('title', 'Unknown')}</b>
🆔 <code>{chat_id}</code>

🔹 Auto React: {doc.get('auto_react', 'off').upper()}
🔹 AI Reply: {doc.get('ai_reply', 'off').upper()}
🔹 Moderation: {doc.get('moderation_enabled', 'off').upper()}""")
        return

    if cmd == '/resetgroup':
        from md_tools.config import set_group_setting
        for k in ['auto_react', 'auto_welcome', 'auto_reply', 'ai_reply', 'moderation_enabled', 'anti_link']:
            set_group_setting(chat_id, k, 'off')
        send_message(chat_id, "✅ All settings reset.")
        return

    target_id, target_name = get_target_user(msg, chat_id)
    if not target_id:
        send_message(chat_id, "❌ Reply or use @username.")
        return

    if cmd == '/ban':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
        send_message(chat_id, f"🔨 <b>{target_name}</b> banned." if r.json().get('ok') else "❌ Failed.")
    elif cmd == '/kick':
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
        if r.json().get('ok'):
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
                        params={'chat_id': chat_id, 'user_id': target_id}, timeout=5)
            send_message(chat_id, f"🚪 <b>{target_name}</b> kicked.")
    elif cmd == '/mute':
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/restrictChatMember",
                    params={'chat_id': chat_id, 'user_id': target_id,
                            'permissions': json.dumps({'can_send_messages': False})}, timeout=5)
        send_message(chat_id, f"🔇 <b>{target_name}</b> muted.")
    elif cmd == '/unmute':
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/restrictChatMember",
                    params={'chat_id': chat_id, 'user_id': target_id,
                            'permissions': json.dumps({'can_send_messages': True})}, timeout=5)
        send_message(chat_id, f"🔊 <b>{target_name}</b> unmuted.")
    elif cmd == '/promote':
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/promoteChatMember",
                    params={'chat_id': chat_id, 'user_id': target_id,
                            'can_manage_chat': True, 'can_delete_messages': True,
                            'can_restrict_members': True, 'can_pin_messages': True}, timeout=5)
        send_message(chat_id, f"👑 <b>{target_name}</b> promoted.")
    elif cmd == '/demote':
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/promoteChatMember",
                    params={'chat_id': chat_id, 'user_id': target_id,
                            'can_manage_chat': False, 'can_delete_messages': False,
                            'can_restrict_members': False, 'can_pin_messages': False}, timeout=5)
        send_message(chat_id, f"🛡️ <b>{target_name}</b> demoted.")

# ========== AI Reply Handler ==========
def handle_ai_reply(msg):
    chat_id = msg['chat']['id']
    if get_group_setting(chat_id, 'ai_reply') != 'on':
        return
    text = msg.get('text', '').strip()
    if not text or text.startswith('/'):
        return
    from md_tools.config import send_chat_action
    send_chat_action(chat_id, 'typing')
    chat_title = msg['chat'].get('title', 'a group')
    ai_response = ai_reply.get_ai_reply(text, chat_title)
    if ai_response:
        send_message(chat_id, ai_response)

# ========== Polling ==========
def polling_worker():
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
                    logger.warning("409 Conflict — retry...")
                else:
                    logger.error(f"API error: {data}")
                time.sleep(5)
                continue

            for update in data.get('result', []):
                last_update_id = update['update_id']

                if 'callback_query' in update:
                    try:
                        panel.handle_callback(update['callback_query'])
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
                        if config.BOT_ID and member.get('id') == config.BOT_ID:
                            send_message(chat_id, "🛡️ <b>Thanks for adding me!</b>\n\n<b>Admins:</b> Use /panel\n<b>Everyone:</b> Use /help")

                if 'left_chat_member' in msg:
                    if config.BOT_ID and msg['left_chat_member'].get('id') == config.BOT_ID:
                        group_col.delete_one({'chat_id': chat_id})

                handle_user_commands(msg)
                handle_admin_commands(msg)
                reactions.send_reaction(chat_id, msg['message_id'])
                handle_ai_reply(msg)
                auto_reply.handle_auto_reply(msg)
                welcome.handle_welcome(msg)

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

start_polling_thread()