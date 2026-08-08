from flask import Blueprint, request, redirect, url_for
import sqlite3

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
DB_PATH = '/tmp/phish_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bot_config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('auto_react', 'off')")
    conn.commit()
    conn.close()
init_db()

def get_auto_react():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_config WHERE key='auto_react'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'off'

def set_auto_react(status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bot_config SET value=? WHERE key='auto_react'", (status,))
    conn.commit()
    conn.close()

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        status = request.form.get('auto_react', 'off')
        set_auto_react(status)
        return redirect(url_for('dashboard.index'))
    
    is_on = get_auto_react() == 'on'
    bot_link = "https://t.me/Arif1222_bot"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Cyber Tools MD</title>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
            body {{ background:#0d1117; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }}
            .card {{ background:#161b22; border-radius:28px; padding:30px 24px; max-width:400px; width:100%; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid #30363d; }}
            .icon {{ background:#1f6feb; width:64px; height:64px; border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:32px; margin-bottom:16px; }}
            h1 {{ font-size:24px; font-weight:600; color:#f0f6fc; margin-bottom:4px; }}
            .sub {{ color:#8b949e; font-size:14px; margin-bottom:24px; }}
            .badge {{ display:inline-block; background:#238636; color:#fff; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:500; margin-bottom:20px; }}
            .btn {{ display:block; background:#1f6feb; color:#fff; text-align:center; padding:14px; border-radius:14px; font-size:17px; font-weight:600; text-decoration:none; margin-bottom:24px; }}
            .btn:hover {{ background:#388bfd; }}
            .divider {{ border:none; border-top:1px solid #30363d; margin:20px 0; }}
            .toggle {{ display:flex; justify-content:space-between; align-items:center; background:#0d1117; padding:12px 16px; border-radius:14px; margin-bottom:8px; }}
            .toggle-label {{ color:#c9d1d9; font-size:16px; font-weight:500; }}
            .options {{ display:flex; gap:12px; }}
            .options label {{ color:#8b949e; font-size:15px; display:flex; align-items:center; gap:6px; cursor:pointer; }}
            .options input[type="radio"] {{ accent-color:#1f6feb; width:18px; height:18px; cursor:pointer; }}
            .save {{ width:100%; background:#238636; color:#fff; border:none; padding:14px; border-radius:14px; font-size:17px; font-weight:600; cursor:pointer; margin-top:12px; }}
            .save:hover {{ background:#2ea043; }}
            .footer {{ text-align:center; color:#484f58; font-size:12px; margin-top:20px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">🛡️</div>
            <h1>Cyber Tools MD</h1>
            <div class="sub">Bot Control</div>
            <div class="badge">● Active</div>
            <a href="{bot_link}" target="_blank" class="btn">📱 Open Bot</a>
            <hr class="divider">
            <form method="post">
                <div class="toggle">
                    <span class="toggle-label">Auto React</span>
                    <div class="options">
                        <label><input type="radio" name="auto_react" value="on" {'checked' if is_on else ''}> ON</label>
                        <label><input type="radio" name="auto_react" value="off" {'checked' if not is_on else ''}> OFF</label>
                    </div>
                </div>
                <button type="submit" class="save">Save Settings</button>
            </form>
            <div class="footer">Token hidden</div>
        </div>
    </body>
    </html>
    """
