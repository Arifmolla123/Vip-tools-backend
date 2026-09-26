from .config import get_group_setting, send_message

def handle_welcome(msg):
    chat_id = msg['chat']['id']
    if get_group_setting(chat_id, 'auto_welcome') != 'on':
        return
    if 'new_chat_members' not in msg:
        return
    for member in msg['new_chat_members']:
        name = member.get('first_name', 'Guest')
        welcome = f"<b>🎉 Welcome {name}!</b> 🥳\n\nGlad to have you here. Type /help to see what I can do!"
        send_message(chat_id, welcome)