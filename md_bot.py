from flask import Blueprint
import threading
import logging
import requests
import time

# ========== Logging ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('md_bot', __name__, url_prefix='/bot')

# ========== আপনার বটের টোকেন ==========
BOT_TOKEN = "8193376363:AAHTTtXNtQqCZ2a_Hd1cpus1Z2iz6kOORo"

# ========== শুধু dashboard ব্লুপ্রিন্ট রেজিস্টার ==========
from md_tools.dashboard import bp as dashboard_bp
bp.register_blueprint(dashboard_bp)

# ========== বাকি মডিউল ইম্পোর্ট (ব্লুপ্রিন্ট ছাড়া) ==========
from md_tools import reactions, formatter, welcome

# ========== পোলিং ওয়ার্কার ==========
def polling_worker():
    logger.info("🔄 Polling started.")
    last_update_id = 0
    while True:
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
        except:
            pass
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={'offset': last_update_id + 1, 'timeout': 30}
            )
            data = resp.json()
            if not data.get('ok'):
                time.sleep(5)
                continue
            for update in data.get('result', []):
                last_update_id = update['update_id']
                msg = update.get('message')
                if not msg:
                    continue
                # প্রতিটি মেসেজের জন্য আলাদা ফাংশন কল
                reactions.handle_reaction(msg)
                formatter.handle_commands(msg)
                welcome.handle_new_member(msg)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

threading.Thread(target=polling_worker, daemon=True).start()
logger.info("🚀 Bot started.")
