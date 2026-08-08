from flask import Blueprint, request, render_template_string
import os
import sqlite3
import time
import threading
import requests
import logging
import json

# ========== লগিং ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')
DB_PATH = '/tmp/phish_data.db'

# ========== ডেটাবেস ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('bot_token', '')")
    conn.commit()
    conn.close()
init_db()

def get_token():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_config WHERE key='bot_token'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

def set_token(token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value=? WHERE key='bot_token'", (token,))
    conn.commit()
    conn.close()

# ========== হেল্পার ফাংশন (ইউজার আইডি বের করা) ==========
def get_target_user(update):
    """রিপ্লাই করা মেসেজ থেকে ইউজার আইডি বের করে"""
    msg = update.get('message')
    if not msg:
        return None, None
    
    # ১. রিপ্লাই করা মেসেজ থেকে
    if 'reply_to_message' in msg:
        target = msg['reply_to_message']['from']
        return target['id'], target.get('username', 'Unknown')
    
    # ২. কমান্ডের সাথে ইউজারনেম দেওয়া থাকলে (যেমন: /ban @username)
    text = msg.get('text', '')
    parts = text.split()
    if len(parts) > 1:
        username = parts[1].strip()
        if username.startswith('@'):
            username = username[1:]
        # টেলিগ্রাম API দিয়ে ইউজারনেম খুঁজি
        token = get_token()
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getChatMember",
                                params={'chat_id': msg['chat']['id'], 'user_id': '@' + username})
            data = resp.json()
            if data.get('ok') and data.get('result'):
                return data['result']['user']['id'], username
        except:
            pass
    return None, None

# ========== ওয়েব সেটআপ পেজ (আগের মতোই) ==========
@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if not token:
            return "<h2 style='color:red;'>❌ Token cannot be empty!</h2><a href='/bot/setup'>Try Again</a>"
        set_token(token)
        logger.info("✅ Token saved.")
        try:
            me = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if not me.json().get('ok'):
                return f"<h2 style='color:red;'>❌ Invalid Token!</h2><a href='/bot/setup'>Try Again</a>"
        except Exception as e:
            return f"<h2 style='color:red;'>❌ Error: {e}</h2><a href='/bot/setup'>Try Again</a>"
        return f"""
        <h2 style='color:green;'>✅ Setup Complete!</h2>
        <p>Token: <code>{token[:10]}...</code></p>
        <p>Now add me as Admin in your channel/group, then type <code>/start</code>.</p>
        <a href='/bot/setup'>Go Back</a>
        """
    current = get_token()
    return f"""
    <!DOCTYPE html>
    <html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;background:#0d1117;color:#c9d1d9;padding:20px;border-radius:10px;">
    <h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
    <h3>🤖 Bot Setup</h3>
    {'<p style="color:#3fb950;">✅ Token exists. Enter new to update:</p>' if current else '<p>Paste your token from @BotFather:</p>'}
    <form method="post">
    <input type="text" name="bot_token" placeholder="e.g. 123456:ABC-DEF" style="width:100%;padding:10px;background:#161b22;color:#fff;border:1px solid #30363d;border-radius:6px;">
    <button type="submit" style="margin-top:10px;background:#238636;color:#fff;padding:10px 20px;border:0;border-radius:6px;cursor:pointer;">Save & Activate</button>
    </form>
    </body></html>
    """

# ==========================================================
# ========== পোলিং ইঞ্জিন (নতুন মডারেশন কমান্ডসহ) ==========
# ==========================================================
def polling_worker():
    logger.info("🔄 [WORKER] Polling started.")
    last_update_id = 0
    while True:
        token = get_token()
        if not token:
            time.sleep(5)
            continue
        
        # ওয়েবহুক ডিলিট
        try:
            requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=5)
        except:
            pass

        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            resp = requests.get(url, params={'offset': last_update_id + 1, 'timeout': 30})
            data = resp.json()
            
            if not data.get('ok'):
                logger.error(f"API Error: {data}")
                time.sleep(5)
                continue
            
            if data.get('result'):
                for update in data['result']:
                    last_update_id = update['update_id']
                    msg = update.get('message')
                    if not msg:
                        continue
                    
                    chat_id = msg['chat']['id']
                    text = msg.get('text', '')
                    username = msg['from'].get('username', 'Unknown')
                    logger.info(f"📩 Received: '{text}' from {username}")
                    
                    reply = None
                    parse_mode = 'HTML'
                    
                    # ========== ইউজার কমান্ড ==========
                    if text == '/start':
                        reply = """<b>🛡️ Cyber MD Bot is LIVE!</b> 🚀

<b>📝 Formatting Commands:</b>
/bold [text] - <b>Bold</b>
/italic [text] - <i>Italic</i>
/code [text] - <code>Code</code>
/strike [text] - <s>Strike</s>
/echo [text] - All formats

<b>👮 Admin Commands (Reply to a user/message):</b>
/ban - Ban the user
/kick - Kick the user
/mute - Mute the user
/unmute - Unmute the user
/promote - Make user Admin
/demote - Remove Admin
/del - Delete replied message
/pin - Pin replied message
/unpin - Unpin replied message

<b>🔧 Conditions:</b> I must be an <b>Admin</b> in this group/channel!"""
                    
                    elif text == '/help':
                        reply = "Send /start to see all commands."
                    
                    # ---------- ফরম্যাটিং ----------
                    elif text.startswith('/bold '):
                        reply = f"<b>{text[6:]}</b>"
                    elif text.startswith('/italic '):
                        reply = f"<i>{text[8:]}</i>"
                    elif text.startswith('/code '):
                        reply = f"<code>{text[6:]}</code>"
                    elif text.startswith('/strike '):
                        reply = f"<s>{text[8:]}</s>"
                    elif text.startswith('/echo '):
                        reply = f"<b>{text[6:]}</b>, <code>code</code>, <s>strike</s>"
                    
                    # ---------- মডারেশন (অ্যাডমিন কমান্ড) ----------
                    # এগুলোর জন্য বটকে অ্যাডমিন হতে হবে
                    elif text.startswith('/ban') or text.startswith('/kick') or text.startswith('/mute') or text.startswith('/unmute') or text.startswith('/promote') or text.startswith('/demote'):
                        target_id, target_name = get_target_user(update)
                        if not target_id:
                            reply = "❌ দয়া করে একটি ইউজারের মেসেজে রিপ্লাই করুন অথবা @username দিন।"
                        else:
                            action = text.split()[0][1:]  # /ban -> ban
                            api_method = None
                            params = {'chat_id': chat_id, 'user_id': target_id}
                            
                            if action == 'ban':
                                api_method = 'banChatMember'
                                reply = f"✅ {target_name} কে ব্যান করা হয়েছে।"
                            elif action == 'kick':
                                api_method = 'banChatMember'
                                # কিক করার জন্য ব্যান করে আবার আনবান করতে হয়
                                try:
                                    requests.get(f"https://api.telegram.org/bot{token}/banChatMember", params=params, timeout=5)
                                    requests.get(f"https://api.telegram.org/bot{token}/unbanChatMember", params=params, timeout=5)
                                    reply = f"✅ {target_name} কে কিক করা হয়েছে।"
                                except Exception as e:
                                    reply = f"❌ কিক করতে ব্যর্থ: {e}"
                                api_method = None # নিজেই করেছি
                            elif action == 'mute':
                                api_method = 'restrictChatMember'
                                params['permissions'] = json.dumps({'can_send_messages': False})
                                reply = f"🔇 {target_name} কে মিউট করা হয়েছে।"
                            elif action == 'unmute':
                                api_method = 'restrictChatMember'
                                params['permissions'] = json.dumps({'can_send_messages': True})
                                reply = f"🔊 {target_name} এর মিউট তুলে নেওয়া হয়েছে।"
                            elif action == 'promote':
                                api_method = 'promoteChatMember'
                                params['can_manage_chat'] = True
                                params['can_delete_messages'] = True
                                params['can_restrict_members'] = True
                                params['can_pin_messages'] = True
                                reply = f"👑 {target_name} কে অ্যাডমিন বানানো হয়েছে।"
                            elif action == 'demote':
                                api_method = 'promoteChatMember'
                                params['can_manage_chat'] = False
                                params['can_delete_messages'] = False
                                params['can_restrict_members'] = False
                                params['can_pin_messages'] = False
                                reply = f"🛡️ {target_name} এর অ্যাডমিন রাইটস তুলে নেওয়া হয়েছে।"
                            
                            if api_method:
                                try:
                                    r = requests.get(f"https://api.telegram.org/bot{token}/{api_method}", params=params, timeout=5)
                                    if not r.json().get('ok'):
                                        reply = f"❌ ব্যর্থ: {r.json().get('description', 'অজানা ত্রুটি')}\n⚠️ নিশ্চিত করুন আমি অ্যাডমিন!"
                                except Exception as e:
                                    reply = f"❌ API ত্রুটি: {e}"
                    
                    # ---------- মেসেজ পিন/ডিলিট ----------
                    elif text.startswith('/del'):
                        if 'reply_to_message' in msg:
                            target_msg_id = msg['reply_to_message']['message_id']
                            try:
                                r = requests.get(f"https://api.telegram.org/bot{token}/deleteMessage", 
                                                 params={'chat_id': chat_id, 'message_id': target_msg_id}, timeout=5)
                                if r.json().get('ok'):
                                    reply = "🗑️ মেসেজ ডিলিট করা হয়েছে।"
                                else:
                                    reply = f"❌ ডিলিট করতে পারিনি: {r.json().get('description')}"
                            except Exception as e:
                                reply = f"❌ ত্রুটি: {e}"
                        else:
                            reply = "❌ ডিলিট করতে একটি মেসেজে রিপ্লাই করুন।"
                    
                    elif text.startswith('/pin'):
                        if 'reply_to_message' in msg:
                            target_msg_id = msg['reply_to_message']['message_id']
                            try:
                                r = requests.get(f"https://api.telegram.org/bot{token}/pinChatMessage", 
                                                 params={'chat_id': chat_id, 'message_id': target_msg_id}, timeout=5)
                                if r.json().get('ok'):
                                    reply = "📌 মেসেজ পিন করা হয়েছে।"
                                else:
                                    reply = f"❌ পিন করতে পারিনি: {r.json().get('description')}"
                            except Exception as e:
                                reply = f"❌ ত্রুটি: {e}"
                        else:
                            reply = "❌ পিন করতে একটি মেসেজে রিপ্লাই করুন।"
                    
                    elif text.startswith('/unpin'):
                        try:
                            if 'reply_to_message' in msg:
                                target_msg_id = msg['reply_to_message']['message_id']
                                r = requests.get(f"https://api.telegram.org/bot{token}/unpinChatMessage", 
                                                 params={'chat_id': chat_id, 'message_id': target_msg_id}, timeout=5)
                            else:
                                r = requests.get(f"https://api.telegram.org/bot{token}/unpinAllChatMessages", 
                                                 params={'chat_id': chat_id}, timeout=5)
                            if r.json().get('ok'):
                                reply = "📌 আনপিন করা হয়েছে।"
                            else:
                                reply = f"❌ আনপিন করতে পারিনি: {r.json().get('description')}"
                        except Exception as e:
                            reply = f"❌ ত্রুটি: {e}"
                    
                    # ---------- রিপ্লাই পাঠানো ----------
                    if reply:
                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                        r = requests.post(send_url, json={
                            'chat_id': chat_id,
                            'text': reply,
                            'parse_mode': parse_mode
                        }, timeout=5)
                        if r.json().get('ok'):
                            logger.info(f"✅ Replied to {chat_id}")
                        else:
                            logger.error(f"❌ Failed: {r.text}")
            
            time.sleep(1)
        except Exception as e:
            logger.error(f"⚠️ Polling error: {e}")
            time.sleep(5)

# ========== থ্রেড স্টার্ট ==========
threading.Thread(target=polling_worker, daemon=True).start()
logger.info("🚀 [MAIN] Polling worker launched.")

# ========== md_tools লোড ==========
try:
    from md_tools import preview, converter, formatter
    bp.register_blueprint(preview.bp)
    bp.register_blueprint(converter.bp)
    bp.register_blueprint(formatter.bp)
    logger.info("✅ md_tools loaded.")
except ImportError:
    logger.warning("⚠️ md_tools not found.")
