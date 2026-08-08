from flask import Blueprint, request, render_template_string
import os
import sqlite3
import logging
import threading
import requests
import time

# ========== লগিং সেটআপ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

# ========== ডেটাবেস ফাংশন (টোকেন রাখার জন্য) ==========
def init_bot_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
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

# ========== টোকেন সেভ হওয়ার সাথে সাথে "Live" মেসেজ পাঠানোর ফাংশন ==========
def send_live_notification(token):
    """সেভ করা টোকেন দিয়ে বটকে 'Live' মেসেজ পাঠানোর চেষ্টা করি"""
    try:
        # ১. ইউজারের সবচেয়ে সাম্প্রতিক চ্যাট আইডি বের করি
        get_url = f"https://api.telegram.org/bot{token}/getUpdates"
        resp = requests.get(get_url, params={'limit': 1, 'offset': -1}, timeout=5)
        data = resp.json()
        
        if data.get('ok') and data.get('result'):
            chat_id = data['result'][0]['message']['chat']['id']
            # ২. ওই চ্যাটে মেসেজ পাঠাই
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': '🛡️ *Cyber MD Bot is live!* 🚀\nআমি এখন সক্রিয়। /start দিয়ে কমান্ড দেখুন।',
                'parse_mode': 'MarkdownV2'
            }
            requests.post(send_url, json=payload, timeout=5)
            logger.info("✅ লাইভ নোটিফিকেশন সফলভাবে পাঠানো হয়েছে!")
        else:
            logger.info("ℹ️ কোনো পুরোনো চ্যাট পাওয়া যায়নি। ইউজার /start দিলে নোটিফিকেশন পাবে।")
    except Exception as e:
        logger.warning(f"⚠️ লাইভ নোটিফিকেশন পাঠাতে ব্যর্থ (ইউজার হয়তো এখনো বট ওপেন করেনি): {e}")

# ========== ওয়েব সেটআপ পেজ (টোকেন দেওয়ার ফর্ম) ==========
@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if not token:
            return render_template_string(ERROR_PAGE, msg="❌ টোকেন খালি রাখা যাবে না!")
        
        # টোকেন সেভ করো
        set_token(token)
        
        # 🔥 টোকেন সেভ হওয়ার সাথে সাথে "Live" মেসেজ পাঠানোর চেষ্টা করো
        send_live_notification(token)
        
        return render_template_string(SUCCESS_PAGE, msg="✅ টোকেন সেভ হয়েছে! বট সক্রিয় হচ্ছে।", token=token[:10]+'...')
    
    current_token = get_token()
    return render_template_string(SETUP_PAGE, has_token=bool(current_token))

# ========== HTML টেমপ্লেট (সুন্দর ডার্ক থিম) ==========
SETUP_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Cyber Tools MD - Setup</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
<h3>🤖 Bot Setup (Polling Mode)</h3>
{% if has_token %}<p style="color:#3fb950;">✅ টোকেন সেভ আছে। নতুন দিতে চাইলে দিন:</p>
{% else %}<p>@BotFather থেকে পাওয়া টোকেনটি দিন:</p>{% endif %}
<form method="post">
<input type="text" name="bot_token" placeholder="যেমন: 7234567890:AAHdqTcv..." style="width:100%;padding:10px;margin:10px 0;background:#161b22;color:#fff;border:1px solid #30363d;border-radius:6px;">
<button type="submit" style="margin-top:10px;background:#238636;color:#fff;padding:10px 20px;border:0;border-radius:6px;cursor:pointer;">Save & Activate</button>
</form>
</body></html>
'''
SUCCESS_PAGE = '''
<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#3fb950;">✅ Setup Complete!</h2><p>{{ msg }}</p><p>Token: <code>{{ token }}</code></p>
<p>আপনার টেলিগ্রাম বটে এখন "Cyber MD Bot is live" মেসেজ চেক করুন।</p>
<a href="/bot/setup" style="color:#58a6ff;">Go Back</a></body></html>
'''
ERROR_PAGE = '''
<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#f85149;">⚠️ Error</h2><p>{{ msg }}</p><a href="/bot/setup" style="color:#58a6ff;">Try Again</a></body></html>
'''

# ======================================================
# ========== পোলিং বট (টেলিগ্রাম লাইব্রেরি) ==========
# ======================================================
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    
    # ----- অ্যাসিঙ্ক হ্যান্ডলারগুলো -----
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("""
🛡️ *Cyber MD Bot is live!* 🚀  
আমি টেক্সট ফরম্যাটিং আর মার্কডাউন টুলসের বট।

*Commands:*  
/bold [text] - **Bold**  
/italic [text] - _Italic_  
/code [text] - `Code`  
/strike [text] - ~Strike~  
/echo [text] - All formats  
/markdown - Cheat sheet  
/help - This message

*Web Tools:* /bot/md/preview, /bot/md/format
""", parse_mode='MarkdownV2')

    async def bold(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = ' '.join(context.args)
        if text: await update.message.reply_text(f"*{text}*", parse_mode='MarkdownV2')
        else: await update.message.reply_text("দয়া করে টেক্সট দিন। যেমন: /bold Hello")

    async def italic(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = ' '.join(context.args)
        if text: await update.message.reply_text(f"_{text}_", parse_mode='MarkdownV2')
        else: await update.message.reply_text("দয়া করে টেক্সট দিন। যেমন: /italic Hello")

    async def code(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = ' '.join(context.args)
        if text: await update.message.reply_text(f"`{text}`", parse_mode='MarkdownV2')
        else: await update.message.reply_text("দয়া করে টেক্সট দিন। যেমন: /code Hello")

    async def strike(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = ' '.join(context.args)
        if text: await update.message.reply_text(f"~{text}~", parse_mode='MarkdownV2')
        else: await update.message.reply_text("দয়া করে টেক্সট দিন। যেমন: /strike Hello")

    async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = ' '.join(context.args)
        if text: await update.message.reply_text(f"*{text}*, `code`, ~strike~", parse_mode='MarkdownV2')
        else: await update.message.reply_text("দয়া করে টেক্সট দিন। যেমন: /echo Hello")

    async def markdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("""
*Markdown Cheat Sheet:*  
Bold: `*text*`  
Italic: `_text_`  
Code: `` `text` ``  
Strike: `~text~`
""", parse_mode='MarkdownV2')

    async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await start(update, context)

    async def reply_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"আপনি লিখেছেন: _{update.message.text}_\n\nকমান্ড পেতে /start লিখুন।", parse_mode='MarkdownV2')

    def run_polling():
        """এটি আলাদা থ্রেডে চলে (ব্যাকগ্রাউন্ডে)"""
        token = get_token()
        if not token:
            logger.warning("⛔ পোলিং শুরু হয়নি: টোকেন নেই। /bot/setup-এ গিয়ে সেট করুন।")
            return
        
        logger.info("⏳ পোলিং বট শুরু হচ্ছে...")
        app = Application.builder().token(token).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help))
        app.add_handler(CommandHandler("bold", bold))
        app.add_handler(CommandHandler("italic", italic))
        app.add_handler(CommandHandler("code", code))
        app.add_handler(CommandHandler("strike", strike))
        app.add_handler(CommandHandler("echo", echo))
        app.add_handler(CommandHandler("markdown", markdown))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_all))
        
        logger.info("✅ পোলিং চালু! বট এখন লাইভ। ইউজার /start দিলে রেসপন্স পাবে।")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    # Flask অ্যাপ চালু হওয়ার সাথে সাথে পোলিং থ্রেড স্টার্ট করুন
    threading.Thread(target=run_polling, daemon=True).start()
    logger.info("🚀 অ্যাপ চালু হয়েছে। পোলিং থ্রেড স্টার্ট হচ্ছে...")

except ImportError:
    logger.error("❌ 'python-telegram-bot' প্যাকেজ ইনস্টল নেই! requirements.txt-এ এটি যোগ করুন।")

# ======================================================
# ========== md_tools ফোল্ডার থেকে টুলস লোড ==========
# ======================================================
try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)      # URL: /bot/md/preview
    bp.register_blueprint(converter.bp)    # URL: /bot/md/convert
    bp.register_blueprint(formatter.bp)    # URL: /bot/md/format
    logger.info("✅ md_tools ব্লুপ্রিন্ট সফলভাবে রেজিস্টার হয়েছে")
except ImportError as e:
    logger.warning(f"⚠️ md_tools ফোল্ডার পাওয়া যায়নি বা লোড হয়নি: {e}")
