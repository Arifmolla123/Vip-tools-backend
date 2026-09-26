import requests
import json
from .config import BOT_TOKEN, get_group_setting, logger

# ✅ শুধু ১টি ইমোজি - যা নিশ্চিতভাবে কাজ করবে
REACTION_EMOJI = "👍"

def send_reaction(chat_id, message_id):
    """প্রতি গ্রুপের auto_react ON থাকলে ১টি রিয়েক্ট পাঠায়"""
    if get_group_setting(chat_id, 'auto_react') != 'on':
        return
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps([{"type": "emoji", "emoji": REACTION_EMOJI}])
        }
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if not data.get('ok'):
            logger.error(f"React failed: {data}")
    except Exception as e:
        logger.error(f"React error: {e}")