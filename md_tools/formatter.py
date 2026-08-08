import requests
import logging

logger = logging.getLogger(__name__)
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1cpus1Z2iz6kOORo"

def handle_commands(msg):
    text = msg.get('text', '')
    if not text.startswith('/'):
        return
    chat_id = msg['chat']['id']
    reply = None
    parse_mode = 'HTML'

    if text == '/start':
        reply = """<b>🛡️ Cyber MD Bot is LIVE!</b> 🚀

<b>📝 Commands:</b>
/bold [text] - <b>Bold</b>
/italic [text] - <i>Italic</i>
/code [text] - <code>Code</code>
/strike [text] - <s>Strike</s>
/echo [text] - All formats

<b>⚙️ Dashboard:</b>
/bot/dashboard - Control auto‑react

<b>👋 Welcome:</b>
I welcome new members automatically."""
    
    elif text == '/help':
        reply = "Send /start to see commands."
    
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

    if reply:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={
                'chat_id': chat_id,
                'text': reply,
                'parse_mode': parse_mode
            }, timeout=5)
            if r.json().get('ok'):
                logger.info(f"✅ Replied to {chat_id}")
            else:
                logger.error(f"❌ Failed: {r.text}")
        except Exception as e:
            logger.error(f"Send error: {e}")
