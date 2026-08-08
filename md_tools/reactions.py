import requests
import json
import logging
import sqlite3

logger = logging.getLogger(__name__)
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1cpus1Z2iz6kOORo"
DB_PATH = '/tmp/phish_data.db'

def get_auto_react():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_config WHERE key='auto_react'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'off'

def handle_reaction(msg):
    if get_auto_react() != 'on':
        return
    chat_id = msg['chat']['id']
    message_id = msg['message_id']
    
    # ১১টি ইমোজি (টেলিগ্রাম সর্বোচ্চ ১১টি অনুমতি দেয়)
    emojis = ["❤️", "🔥", "👍", "🎉", "😂", "😍", "👏", "💯", "🤩", "🥳", "✨"]
    
    try:
        reaction_list = [{"type": "emoji", "emoji": e} for e in emojis]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps(reaction_list)
        }
        r = requests.post(url, json=payload, timeout=5)
        if r.json().get('ok'):
            logger.info(f"✅ 11 reactions sent to msg {message_id}")
        else:
            logger.error(f"❌ Reaction failed: {r.text}")
    except Exception as e:
        logger.error(f"Reaction error: {e}")
