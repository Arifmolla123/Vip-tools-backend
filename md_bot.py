from flask import Blueprint, request, jsonify, render_template_string
import requests
import os
import sqlite3

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

def set_webhook(token):
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not render_url:
        return False, "RENDER_EXTERNAL_URL not found"
    webhook_url = f"{render_url}/bot/webhook"
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}", timeout=10)
        data = resp.json()
        return data.get('ok', False), data.get('description', '')
    except Exception as e:
        return False, str(e)

def send_message(chat_id, text, parse_mode='MarkdownV2'):
    token = get_token()
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode, 'disable_web_page_preview': True}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

# ========== SETUP PAGE (Token Input) ==========
@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if not token:
            return render_template_string(ERROR_PAGE, msg="❌ Token cannot be empty!")
        set_token(token)
        success, msg = set_webhook(token)
        if success:
            return render_template_string(SUCCESS_PAGE, msg="Webhook set successfully ✅", token=token[:10]+'...')
        else:
            return render_template_string(ERROR_PAGE, msg=f"❌ Webhook failed: {msg}")
    current_token = get_token()
    return render_template_string(SETUP_PAGE, has_token=bool(current_token))

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
<html>
<head><title>Cyber Tools MD - Success</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#3fb950;">✅ Setup Complete!</h2>
<p>{{ msg }}</p>
<p>Token: <code style="background:#161b22;padding:2px 6px;">{{ token }}</code></p>
<p>Now go to your Telegram bot and type <code>/start</code>.</p>
<a href="/bot/setup" style="color:#58a6ff;">Go Back</a>
</body></html>
'''

ERROR_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Cyber Tools MD - Error</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:50px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#f85149;">⚠️ Error</h2>
<p>{{ msg }}</p>
<a href="/bot/setup" style="color:#58a6ff;">Try Again</a>
</body></html>
'''

# ========== TELEGRAM WEBHOOK ==========
@bp.route('/webhook', methods=['POST'])
def webhook():
    token = get_token()
    if not token:
        return jsonify({'status': 'error', 'msg': 'Token not set. Visit /bot/setup'}), 403
    update = request.get_json()
    if not update or 'message' not in update:
        return 'OK', 200
    msg = update['message']
    chat_id = msg['chat']['id']
    text = msg.get('text', '')

    # --- All commands in English ---
    if text == '/start':
        send_message(chat_id, """
*🛡️ Cyber Tools MD Bot*  
Welcome to the Markdown Power Bot 🤖

*Available Commands:*  
/echo [text] - Format your text with bold, code, strike  
/bold [text] - Make text **bold**  
/italic [text] - Make text _italic_  
/markdown - Show Markdown cheat sheet  
/help - Show this message

*Web Tools:*  
/md/preview - Live Markdown preview  
/md/format - Telegram formatter
        """)
    elif text.startswith('/echo '):
        user_text = text[6:]
        send_message(chat_id, f"You sent: *{user_text}*, `code`, ~strike~")
    elif text.startswith('/bold '):
        send_message(chat_id, f"*{text[6:]}*")
    elif text.startswith('/italic '):
        send_message(chat_id, f"_{text[8:]}_")
    elif text == '/markdown':
        send_message(chat_id, """
*Markdown Cheat Sheet:*  
Bold: `*text*`  
Italic: `_text_`  
Code: `` `text` ``  
Strike: `~text~`
        """)
    elif text == '/help':
        send_message(chat_id, "Type /start to see all commands.")

    # Welcome new members in groups
    if 'new_chat_members' in msg:
        for member in msg['new_chat_members']:
            name = member.get('first_name', 'Guest')
            send_message(chat_id, f"🎉 *Welcome!* {name} joined the group.\nPlease follow the rules.")
    return 'OK', 200
