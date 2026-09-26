import logging
from pymongo import MongoClient

# ========== Logging (শুধু ERROR দেখাবে) ==========
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('pymongo').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

# ========== Bot Configuration ==========
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1Lcpus1Z2iz6kOORo"
BOT_LINK = "https://t.me/Arif1222_bot"
DASHBOARD_BASE = "https://vip-tools-backend.onrender.com"

# ========== MongoDB ==========
MONGO_URI = "mongodb+srv://Cyber_md_bot:cybermd123@cluster0.tre505e.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['cyber_tools']
group_col = db['group_settings']

# ========== Bot ID ==========
BOT_ID = None

# ========== Group Settings Helpers ==========
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

# ========== Telegram API Helpers ==========
def send_message(chat_id, text, parse_mode='HTML', reply_markup=None):
    import requests
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode, 'disable_web_page_preview': True}
        if reply_markup:
            payload['reply_markup'] = reply_markup
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get('ok', False)
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

def edit_message(chat_id, message_id, text, parse_mode='HTML', reply_markup=None):
    import requests
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
    import requests
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                     json={'callback_query_id': cb_id, 'text': text, 'show_alert': show_alert}, timeout=5)
    except:
        pass

def delete_message(chat_id, message_id):
    import requests
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                        params={'chat_id': chat_id, 'message_id': message_id}, timeout=5)
        return r.json().get('ok', False)
    except:
        return False

def send_chat_action(chat_id, action='typing'):
    import requests
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction",
                     json={'chat_id': chat_id, 'action': action}, timeout=5)
    except:
        pass

# ========== Permission Check ==========
def get_user_status(chat_id, user_id):
    import requests
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