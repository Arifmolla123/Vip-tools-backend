from flask import Blueprint, request, jsonify
import markdown
import logging

bp = Blueprint('md_converter', __name__, url_prefix='/md/convert')
logger = logging.getLogger(__name__)

@bp.route('/', methods=['POST'])
def convert():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'html': ''})
        
        html = markdown.markdown(text)
        logger.info(f"API conversion: {len(text)} characters -> {len(html)} chars")
        return jsonify({'html': html})
    
    except Exception as e:
        logger.error(f"API conversion error: {e}")
        return jsonify({'error': str(e)}), 500
