from flask import Blueprint, request, render_template_string
import os
import sqlite3
import logging
import time
import requests
from multiprocessing import Process

# ========== লগিং সেটআপ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

# ========== ডেটাবেস ফাংশন (টোকেন সংরক্ষণ) ==========
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

# ========== টোকেন সেভ হওয়ার সাথে সাথে "Live" মেসেজ ==========
def send_live_notification(token):
    try:
        get_url = f"https://api.telegram.org/bot{token}/getUpdates"
        resp = requests.get(get_url, params={'limit': 1, 'offset': -1}, timeout=5)
        data = resp.json()
        if data.get('ok') and data.get('result'):
            chat_id = data['result'][0]['message']['chat']['id']
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': '🛡️ *Cyber MD Bot is live!* 🚀\nআমি এখন সক্রিয়। /start দিয়ে কমান্ড দেখুন।',
                'parse_mode': 'MarkdownV2'
            }
            requests.post(send_url, json=payload, timeout=5)
            logger.info("✅ লাইভ নোটিফিকেশন পাঠানো হয়েছে!")
    except:
        logger.info("ℹ️ ইউজার হয়তো এখনো বট ওপেন করেনি।")

# ========== ওয়েব সেটআপ পেজ ==========
@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if not token:
            return render_template_string(ERROR_PAGE, msg="❌ টোকেন খালি রাখা যাবে না!")
        set_token(token)
        send_live_notification(token)
        return render_template_string(SUCCESS_PAGE, msg="✅ টোকেন সেভ হয়েছে! বট সক্রিয় হচ্ছে।", token=token[:10]+'...')
    current_token = get_token()
    return render_template_string(SETUP_PAGE, has_token=bool(current_token))

# ========== HTML টেমপ্লেট ==========
SETUP_PAGE = '''
<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
<h3>🤖 Bot Setup (Polling Mode)</h3>
{% if has_token %}<p style="color:#3fb950;">✅ টোকেন সেভ আছে। নতুন দিতে চাইলে দিন:</p>{% endif %}
<form method="post">
<input type="text" name="bot_token" placeholder="যেমন: 7234567890:AAHdqTcv..." style="width:100%;padding:10px;background:#161b22;color:#fff;border:1px solid #30363d;border-radius:6px;">
<button type="submit" style="margin-top:10px;background:#238636;color:#fff;padding:10px 20px;border:0;border-radius:6px;cursor:pointer;">Save & Activate</button>
</form></body></html>
'''
SUCCESS_PAGE = '''
<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#3fb950;">✅ Setup Complete!</h2><p>{{ msg }}</p><p>Token: <code>{{ token }}</code></p>
<p>আপনার টেলিগ্রাম বটে "Live" মেসেজ চেক করুন।</p>
<a href="/bot/setup" style="color:#58a6ff;">Go Back</a></body></html>
'''
ERROR_PAGE = '''
<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#f85149;">⚠️ Error</h2><p>{{ msg }}</p><a href="/bot/setup" style="color:#58a6ff;">Try Again</a></body></html>
'''

# ======================================================
# ========== পোলিং বট (সবচেয়ে শক্তিশালী ভার্সন) ==========
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

    # ===== পোলিং ফাংশন (এটি আলাদা প্রসেসে চলে) =====
    def run_polling_forever():
        logger.info("🔄 পোলিং লুপ শুরু হয়েছে (প্রসেস আইডি: %s)", os.getpid())
        while True:
            token = get_token()
            if not token:
                logger.info("⏳ টোকেন নেই। ১০ সেকেন্ড পর আবার চেক করা হবে...")
                time.sleep(10)
                continue

            # 🔥 পুরোনো ওয়েবহুক জোর করে ডিলিট করো
            try:
                resp = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=5)
                if resp.json().get('ok'):
                    logger.info("🔴 পুরোনো ওয়েবহুক ডিলিট করা হয়েছে।")
                else:
                    logger.warning(f"⚠️ ওয়েবহুক ডিলিট সমস্যা: {resp.text}")
            except Exception as e:
                logger.warning(f"ওয়েবহুক ডিলিট রিকোয়েস্ট ব্যর্থ: {e}")

            logger.info("⏳ পোলিং বট কানেক্ট হচ্ছে...")
            try:
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
                
                logger.info("✅ পোলিং চালু! বট এখন লাইভ।")
                app.run_polling(allowed_updates=Update.ALL_TYPES)
            except Exception as e:
                logger.error(f"❌ পোলিং থেমে গেছে (ত্রুটি: {e}). ১০ সেকেন্ড পর আবার চেষ্টা করবে...")
                time.sleep(10)
                continue

    # ===== অ্যাপ চালু হওয়ার সাথে সাথে পোলিং প্রসেস স্টার্ট করো =====
    # এটি Flask এর main থ্রেডকে ব্লক করবে না
    polling_process = Process(target=run_polling_forever, daemon=True)
    polling_process.start()
    logger.info("🚀 অ্যাপ চালু হয়েছে। পোলিং প্রসেস স্টার্ট হয়েছে (PID: %s)", polling_process.pid)

except ImportError:
    logger.error("❌ 'python-telegram-bot' প্যাকেজ ইনস্টল নেই! requirements.txt চেক করুন।")

# ======================================================
# ========== md_tools ফোল্ডার থেকে টুলস লোড ==========
# ======================================================
try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)
    bp.register_blueprint(converter.bp)
    bp.register_blueprint(formatter.bp)
    logger.info("✅ md_tools ব্লুপ্রিন্ট সফলভাবে রেজিস্টার হয়েছে")
except ImportError as e:
    logger.warning(f"⚠️ md_tools ফোল্ডার পাওয়া যায়নি: {e}")
