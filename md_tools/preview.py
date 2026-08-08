from flask import Blueprint, request, render_template_string
import markdown
import logging

bp = Blueprint('md_preview', __name__, url_prefix='/md/preview')
logger = logging.getLogger(__name__)

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Cyber Tools MD - Live Preview</title></head>
<body style="font-family:sans-serif;max-width:800px;margin:30px auto;padding:20px;background:#0d1117;color:#c9d1d9;border-radius:10px;">
<h2 style="color:#58a6ff;">🛡️ Cyber Tools MD</h2>
<h3>📝 Live Markdown Preview</h3>
<form method="post">
<textarea name="content" rows="10" style="width:100%;padding:10px;background:#161b22;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;">{{ content or '' }}</textarea>
<br><button type="submit" style="margin-top:10px;padding:10px 20px;background:#238636;color:#fff;border:0;border-radius:6px;cursor:pointer;">Preview</button>
</form>
{% if html %}
<div style="border:1px solid #30363d;padding:20px;margin-top:20px;border-radius:6px;background:#161b22;">
<h4 style="color:#58a6ff;">Output:</h4>
{{ html|safe }}
</div>
{% endif %}
</body></html>
'''

@bp.route('/', methods=['GET', 'POST'])
def index():
    content = html = ''
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            try:
                html = markdown.markdown(content)
                logger.info(f"Preview converted: {len(content)} characters")
            except Exception as e:
                html = f"<p style='color:#f85149;'>Conversion error: {e}</p>"
                logger.error(f"Markdown conversion error: {e}")
    return render_template_string(TEMPLATE, content=content, html=html)
