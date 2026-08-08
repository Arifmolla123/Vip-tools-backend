from flask import Blueprint, request, render_template_string
import logging

bp = Blueprint('md_formatter', __name__, url_prefix='/md/format')
logger = logging.getLogger(__name__)

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Cyber Tools MD - Formatter</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:30px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
<h3>✏️ Telegram Text Formatter</h3>
<form method="post">
<input type="text" name="text" placeholder="Enter your text here" value="{{ text or '' }}" style="width:100%;padding:10px;margin:10px 0;background:#161b22;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;">
<div style="margin:10px 0;">
<label><input type="checkbox" name="bold" {% if bold %}checked{% endif %}> Bold</label> &nbsp;
<label><input type="checkbox" name="italic" {% if italic %}checked{% endif %}> Italic</label> &nbsp;
<label><input type="checkbox" name="code" {% if code %}checked{% endif %}> Code</label> &nbsp;
<label><input type="checkbox" name="strike" {% if strike %}checked{% endif %}> Strike</label>
</div>
<button type="submit" style="padding:10px 20px;background:#238636;color:#fff;border:0;border-radius:6px;cursor:pointer;">Format Now</button>
</form>
{% if result %}
<div style="border:1px solid #30363d;padding:15px;margin-top:20px;border-radius:6px;background:#161b22;">
<strong>Result:</strong> <span>{{ result|safe }}</span>
<br><br><textarea rows="2" style="width:100%;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;">{{ result }}</textarea>
</div>
{% endif %}
</body></html>
'''

@bp.route('/', methods=['GET', 'POST'])
def index():
    text = result = ''
    bold = italic = code = strike = False
    
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        bold = 'bold' in request.form
        italic = 'italic' in request.form
        code = 'code' in request.form
        strike = 'strike' in request.form
        
        if text:
            if bold: text = f'*{text}*'
            if italic: text = f'_{text}_'
            if code: text = f'`{text}`'
            if strike: text = f'~{text}~'
            result = text
            logger.info(f"Formatted: {result}")
    
    return render_template_string(TEMPLATE, text=text, result=result, bold=bold, italic=italic, code=code, strike=strike)
