import requests
import json
import random
import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)

BOT_TOKEN = "8193376363:AAFyMyVmK7gryI4H1ZxZOobwFt_wzeFwJrM"  # নতুন টোকেন বসান

MONGO_URI = "mongodb+srv://Cyber_md_bot:cybermd123@cluster0.tre505e.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['cyber_tools']
group_col = db['group_settings']

def get_group_setting(chat_id, key, default='off'):
    doc = group_col.find_one({'chat_id': chat_id})
    return doc.get(key, default) if doc else default

def handle_reaction(msg):
    chat_id = msg['chat']['id']
    message_id = msg['message_id']

    if get_group_setting(chat_id, 'auto_react') != 'on':
        return

    # ✅ শুধু ১টি এমোজি (TOO_MANY_REACTIONS এড়াতে)
    emojis = ["👍", "❤️", "🔥"]
    chosen = random.choice(emojis)

    try:
        reaction_list = [{"type": "emoji", "emoji": chosen}]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': json.dumps(reaction_list)  # স্ট্রিং হিসেবে
        }
        # ✅ data= ব্যবহার (json= নয়)
        r = requests.post(url, data=payload, timeout=5)
        data = r.json()

        if data.get('ok'):
            logger.info(f"✅ Reaction '{chosen}' sent to msg {message_id} in {chat_id}")
        else:
            logger.error(f"❌ React failed: {data}")
    except Exception as e:
        logger.error(f"Reaction error: {e}")
