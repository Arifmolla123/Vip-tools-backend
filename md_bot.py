from flask import Blueprint, request, jsonify, render_template_string
import requests
import os
import sqlite3
import logging

# ====== লগিং সেটআপ (Render-এর Log-এ দেখানোর জন্য) ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== ব্লুপ্রিন্ট ও ডেটাবেস সেটআপ ======
bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

def init_bot_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('bot_token', '')")
    conn.commit()
    conn.close()
init_bot_table()

def get_token():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_config WHERE key = 'bot_token'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

def set_token(new_token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value = ? WHERE key = 'bot_token'", (new_token,))
    conn.commit()
    conn.close()

def send_telegram_message(chat_id, text, parse_mode='MarkdownV2'):
    """টেলিগ্রামে মেসেজ পাঠানোর হেল্পার ফাংশন"""
    token = get_token()
    if not token:
        logger.error("টোকেন নেই, মেসেজ পাঠানো যাচ্ছে না")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.json().get('ok'):
            logger.error(f"টেলিগ্রাম API ত্রুটি: {resp.text}")
    except Exception as e:
        logger.error(f"মেসেজ পাঠাতে ব্যর্থ: {e}")

# ========== ১. সেটআপ ওয়েব পেজ (টোকেন দেওয়ার ফর্ম) ==========
@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if not token:
            return render_template_string(ERROR_PAGE, msg="❌ Token cannot be empty!")
        
        # টোকেন সেভ করো
        set_token(token)
        
        # ওয়েবহুক সেট করো
        render_url = os.environ.get('RENDER_EXTERNAL_URL')
        if not render_url:
            return render_template_string(ERROR_PAGE, msg="RENDER_EXTERNAL_URL পরিবেশ চলকটি সেট করা নেই!")
        
        webhook_url = f"{render_url}/bot/webhook"
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}", timeout=10)
            data = resp.json()
            if data.get('ok'):
                return render_template_string(SUCCESS_PAGE, msg="Webhook set successfully ✅", token=token[:10]+'...')
            else:
                return render_template_string(ERROR_PAGE, msg=f"Webhook ব্যর্থ: {data.get('description')}")
        except Exception as e:
            return render_template_string(ERROR_PAGE, msg=f"নেটওয়ার্ক ত্রুটি: {str(e)}")
    
    current_token = get_token()
    return render_template_string(SETUP_PAGE, has_token=bool(current_token))

# ========== HTML টেমপ্লেট (সাজানো) ==========
SETUP_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Cyber Tools MD - Setup</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
<h3>🤖 Telegram Bot Setup</h3>
{% if has_token %}<p style="color:#3fb950;">✅ Token is already saved. Enter a new one to update:</p>
{% else %}<p>Please paste the token you got from <strong>@BotFather</strong>:</p>{% endif %}
<form method="post">
<input type="text" name="bot_token" placeholder="e.g. 7234567890:AAHdqTcv..." style="width:100%;padding:10px;margin:10px 0;background:#161b22;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;">
<button type="submit" style="background:#238636;color:#fff;padding:10px 20px;border:0;border-radius:6px;cursor:pointer;">Save & Activate</button>
</form>
</body></html>
'''
SUCCESS_PAGE = '''
<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#3fb950;">✅ Setup Complete!</h2><p>{{ msg }}</p><p>Token: <code>{{ token }}</code></p>
<a href="/bot/setup" style="color:#58a6ff;">Go Back</a></body></html>
'''
ERROR_PAGE = '''
<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#f85149;">⚠️ Error</h2><p>{{ msg }}</p><a href="/bot/setup" style="color:#58a6ff;">Try Again</a></body></html>
'''

# ========== ২. টেলিগ্রাম ওয়েবহুক এন্ডপয়েন্ট (সব কমান্ড এখানে) ==========
@bp.route('/webhook', methods=['POST'])
def webhook():
    try:
        # টোকেন চেক
        token = get_token()
        if not token:
            logger.warning("টোকেন নেই, অনুরোধ উপেক্ষা করা হলো")
            return jsonify({'status': 'error', 'msg': 'Token not set'}), 403

        # ইনকামিং ডেটা পার্স
        update = request.get_json()
        if not update or 'message' not in update:
            return 'OK', 200

        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg.get('text', '').strip()
        username = msg['from'].get('username', 'User')

        logger.info(f"মেসেজ পেলাম: {text} (from {username})")

        # ========== কমান্ড লিস্ট (এখানে সবকিছু!) ==========
        # ১. /start - ওয়েলকাম + পুরো হেল্প
        if text == '/start':
            help_text = """
*🛡️ Welcome to Cyber Tools MD Bot!*  
আমি টেক্সট ফরম্যাটিং আর মার্কডাউন টুলসের বট।

*📋 আমার কমান্ডগুলো দেখুন:*

1️⃣ `/bold [text]` - টেক্সটকে **বোল্ড** করে
_উদাহরণ:_ `/bold Hello` → *Hello*

2️⃣ `/italic [text]` - টেক্সটকে _ইটালিক_ করে
_উদাহরণ:_ `/italic Hello` → _Hello_

3️⃣ `/code [text]` - টেক্সটকে `কোড` ফরম্যাটে দেখায়
_উদাহরণ:_ `/code Hello` → `Hello`

4️⃣ `/strike [text]` - টেক্সটের ওপর ~দাগ~ দেয়
_উদাহরণ:_ `/strike Hello` → ~Hello~

5️⃣ `/echo [text]` - সব ফরম্যাট একসাথে দেখায় (বোল্ড+কোড+স্ট্রাইক)
_উদাহরণ:_ `/echo test`

6️⃣ `/markdown` - মার্কডাউন চিটশিট দেখায়

7️⃣ `/help` - এই হেল্প বার্তা দেখায়

*🌐 ওয়েব টুলস (ব্রাউজারে খুলুন):*
- /bot/md/preview (লাইভ প্রিভিউ)
- /bot/md/format (ফরম্যাটার)

🤖 *টিপ:* আমি গ্রুপে নতুন কাউকে দেখলেই স্বাগত জানাই!
            """
            send_telegram_message(chat_id, help_text)

        # ২. /help - শর্টকাট
        elif text == '/help':
            send_telegram_message(chat_id, "সব কমান্ড দেখতে `/start` টাইপ করুন।")

        # ৩. /bold
        elif text.startswith('/bold '):
            content = text[6:]
            send_telegram_message(chat_id, f"*{content}*")

        # ৪. /italic
        elif text.startswith('/italic '):
            content = text[8:]
            send_telegram_message(chat_id, f"_{content}_")

        # ৫. /code
        elif text.startswith('/code '):
            content = text[6:]
            send_telegram_message(chat_id, f"`{content}`")

        # ৬. /strike
        elif text.startswith('/strike '):
            content = text[8:]
            send_telegram_message(chat_id, f"~{content}~")

        # ৭. /echo (সম্মিলিত ফরম্যাট)
        elif text.startswith('/echo '):
            content = text[6:]
            send_telegram_message(chat_id, f"আপনি পাঠিয়েছেন: *{content}*, `কোড` দেখুন, ~এটাও আছে~")

        # ৮. /markdown (চিটশিট)
        elif text == '/markdown':
            send_telegram_message(chat_id, """
*মার্কডাউন চিটশিট:*
বোল্ড: `*টেক্সট*`
ইটালিক: `_টেক্সট_`
কোড: `` `টেক্সট` ``
স্ট্রাইক: `~টেক্সট~`
            """)

        # ৯. গ্রুপে নতুন সদস্য জয়েন করলে স্বাগত
        if 'new_chat_members' in msg:
            for member in msg['new_chat_members']:
                name = member.get('first_name', 'Guest')
                send_telegram_message(chat_id, f"🎉 *স্বাগতম!* {name} গ্রুপে জয়েন করেছেন।\n/start দিয়ে কমান্ড দেখুন।")

        # ১০. অজানা কমান্ড (ফাঁকা থাকলে কিছু না)
        elif not text.startswith('/') and text != '':
            # ইউজার যদি কোনো কমান্ড ছাড়া টেক্সট দেয়
            send_telegram_message(chat_id, f"আপনি লিখেছেন: _{text}_\n\nকমান্ড পেতে `/start` টাইপ করুন।")

        return 'OK', 200

    except Exception as e:
        logger.error(f"ওয়েবহুকে মারাত্মক ত্রুটি: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500

# ========== ৩. (অপশনাল) টুলস ফোল্ডার ইম্পোর্ট - যদি md_tools থাকে ==========
try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)
    bp.register_blueprint(converter.bp)
    bp.register_blueprint(formatter.bp)
    logger.info("✅ md_tools ব্লুপ্রিন্ট সফলভাবে রেজিস্টার হয়েছে")
except ImportError:
    logger.warning("⚠️ md_tools ফোল্ডার পাওয়া যায়নি, ওয়েব টুলস লোড হয়নি")
