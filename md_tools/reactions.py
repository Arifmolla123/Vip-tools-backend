import requests
import json
import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)

BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1Lcpus1Z2iz6kOORo"

# ========== MongoDB ==========
MONGO_URI = "mongodb+srv://Cyber_md_bot:cybermd123@cluster0.tre505e.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['cyber_tools']
group_col = db['group_settings']

def get_group_setting(chat_id, key, default='off'):
    """গ্রুপের নির্দিষ্ট সেটিং পড়ে"""
    doc = group_col.find_one({'chat_id': chat_id})
    return doc.get(key, default) if doc else default

def handle_reaction(msg):
    """প্রতিটি গ্রুপের নিজস্ব auto_react সেটিং অনুযায়ী রিয়েক্ট পাঠায়"""
    chat_id = msg['chat']['id']
    message_id = msg['message_id']

    # গ্রুপের auto_react সেটিং চেক
    if get_group_setting(chat_id, 'auto_react') != 'on':
        return

    # ৩টি নিশ্চিতভাবে সমর্থিত ইমোজি
    emojis = ["👍", "❤️", "🔥"]

    try:
        reaction_list = [{"type": "emoji", "emoji": e} for e in emojis]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps(reaction_list)
        }
        r = requests.post(url, json=payload, timeout=5)
        data = r.json()
        if data.get('ok'):
            logger.info(f"✅ 3 reactions sent to msg {message_id} in {chat_id}")
        else:
            logger.error(f"❌ React failed: {data}")
    except Exception as e:
        logger.error(f"Reaction error: {e}")
