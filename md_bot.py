from flask import Blueprint, request, render_template_string
import os, time, threading, requests, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
bp = Blueprint('md_bot', __name__, url_prefix='/bot')

# টোকেন এনভায়রনমেন্ট বা ফর্ম থেকে নেওয়া হবে
TOKEN = os.environ.get('BOT_TOKEN', '')

@bp.route('/setup', methods=['GET','POST'])
def setup():
    global TOKEN
    if request.method == 'POST':
        token = request.form.get('bot_token', '').strip()
        if token:
            TOKEN = token
            os.environ['BOT_TOKEN'] = token
            return "<h2>✅ Token Saved!</h2><a href='/bot/setup'>Back</a>"
    return '''
    <form method="post">
    <input type="text" name="bot_token" placeholder="Enter token" style="width:300px;">
    <button type="submit">Save</button>
    </form>
    '''

def polling_loop():
    logger.info("🔄 Polling started")
    last = 0
    while True:
        token = os.environ.get('BOT_TOKEN', '')
        if not token:
            time.sleep(5)
            continue
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", 
                                params={'offset': last+1, 'timeout': 20})
            data = resp.json()
            if data.get('ok') and data.get('result'):
                for upd in data['result']:
                    last = upd['update_id']
                    msg = upd.get('message')
                    if msg:
                        cid = msg['chat']['id']
                        txt = msg.get('text', '')
                        if txt == '/start':
                            reply = "🛡️ Live! Send /help"
                        else:
                            reply = f"You said: {txt}"
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                      json={'chat_id': cid, 'text': reply})
                        logger.info(f"Replied to {cid}")
        except Exception as e:
            logger.error(f"Polling error: {e}")
        time.sleep(1)

threading.Thread(target=polling_loop, daemon=True).start()
logger.info("✅ Polling thread started")
