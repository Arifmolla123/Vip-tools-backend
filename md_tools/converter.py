from flask import Blueprint, request, jsonify
import markdown

bp = Blueprint('md_converter', __name__, url_prefix='/md/convert')

@bp.route('/', methods=['POST'])
def convert():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'html': ''})
    return jsonify({'html': markdown.markdown(text)})
