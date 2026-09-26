from .config import get_group_setting, send_message, logger

AUTO_REPLIES = {
    'hi': '<b>Hello!</b> <i>How are you?</i> 😊',
    'hello': '<b>Hello!</b> <i>How can I help you?</i>',
    'good morning': '<b>🌅 Good Morning!</b> Have a wonderful day!',
    'good night': '<b>🌙 Good Night!</b> Sweet dreams!',
    'how are you': '<i>I am just a bot, but I am doing great!</i> 😄',
}

def handle_auto_reply(msg):
    chat_id = msg['chat']['id']
    if get_group_setting(chat_id, 'auto_reply') != 'on':
        return
    text = msg.get('text', '').lower().strip()
    if not text:
        return
    for keyword, reply in AUTO_REPLIES.items():
        if keyword in text:
            send_message(chat_id, reply)
            break