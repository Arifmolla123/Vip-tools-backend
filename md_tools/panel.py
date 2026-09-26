import json
from .config import (
    get_group, get_group_setting, set_group_setting,
    send_message, edit_message, answer_callback,
    is_admin, logger
)

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

def show_panel(chat_id, user_id):
    if not is_admin(chat_id, user_id):
        send_message(chat_id, "⛔ <b>Admins only.</b>")
        return
    send_message(chat_id, get_panel_text(chat_id), reply_markup=get_panel_keyboard(chat_id))

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