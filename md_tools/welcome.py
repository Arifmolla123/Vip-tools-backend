import requests
import logging

logger = logging.getLogger(__name__)
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1cpus1Z2iz6kOORo"

def handle_new_member(msg):
    if 'new_chat_members' not in msg:
        return
    chat_id = msg['chat']['id']
    for member in msg['new_chat_members']:
        name = member.get('first_name', 'Guest')
        logger.info(f"👤 New member: {name}")
        welcome = f"<b>🎉 Welcome {name}!</b> 🥳\nGlad to have you here. Type /start to see what I can do."
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={
                'chat_id': chat_id,
                'text': welcome,
                'parse_mode': 'HTML'
            }, timeout=5)
            if r.json().get('ok'):
                logger.info(f"✅ Welcome sent to {name}")
            else:
                logger.error(f"❌ Welcome failed: {r.text}")
        except Exception as e:
            logger.error(f"Welcome error: {e}")
