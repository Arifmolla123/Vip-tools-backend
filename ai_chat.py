from flask import Blueprint, request, jsonify, render_template_string, current_app
import requests
import json
import time

# ==========================================
# ব্লুপ্রিন্ট তৈরি
# ==========================================
bp = Blueprint('ai_chat', __name__, url_prefix='/ai')

# ==========================================
# HTML টেমপ্লেট (সুন্দর UI)
# ==========================================
CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>আরিফ AI - Attitude সহ</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
        body { background: #0B0F19; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .chat-container { width: 420px; height: 700px; background: #141B2D; border-radius: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.8); display: flex; flex-direction: column; overflow: hidden; border: 1px solid #2A3A5C; }
        .header { background: linear-gradient(135deg, #1A2744, #0F1629); padding: 20px; border-bottom: 1px solid #2A3A5C; text-align: center; }
        .header h1 { color: #FFD700; font-size: 22px; letter-spacing: 1px; }
        .header p { color: #8899BB; font-size: 13px; margin-top: 4px; }
        .header .badge { display: inline-block; background: #FF4D4D; color: white; padding: 2px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; }
        .messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; background: #0E1422; }
        .msg { max-width: 85%; padding: 12px 16px; border-radius: 18px; font-size: 15px; line-height: 1.5; word-break: break-word; animation: fadeIn 0.3s ease; }
        .user { align-self: flex-end; background: #2A4B7C; color: white; border-bottom-right-radius: 4px; }
        .bot { align-self: flex-start; background: #1E2940; color: #E0E6F0; border-bottom-left-radius: 4px; border-left: 3px solid #FFD700; }
        .input-area { display: flex; padding: 15px; background: #0F1629; border-top: 1px solid #2A3A5C; gap: 10px; }
        .input-area input { flex: 1; background: #1E2940; border: none; padding: 12px 18px; border-radius: 30px; color: white; font-size: 15px; outline: none; border: 1px solid #2A3A5C; }
        .input-area input:focus { border-color: #FFD700; }
        .input-area button { background: #FFD700; color: #0B0F19; border: none; width: 50px; border-radius: 50%; font-size: 22px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .input-area button:hover { background: #FFED4A; transform: scale(1.05); }
        .typing { color: #8899BB; font-size: 13px; padding-left: 10px; font-style: italic; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #FFD700; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h1>🤖 আরিফ AI</h1>
            <p><span class="badge">ATTITUDE</span> ⚡ Developer: <strong style="color:#FFD700;">Arif</strong></p>
        </div>
        <div class="messages" id="chatBox">
            <div class="msg bot">হ্যালো! আমি আরিফ। যা বলার, স্পষ্ট করে বলো। 💥</div>
        </div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="যেকোনো ভাষায় প্রশ্ন করো..." />
            <button id="sendBtn">➤</button>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            chatBox.innerHTML += `<div class="msg user">${text}</div>`;
            userInput.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            const typingDiv = document.createElement('div');
            typingDiv.className = 'msg bot typing';
            typingDiv.textContent = 'আরিফ টাইপ করছে... ⏳';
            chatBox.appendChild(typingDiv);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const response = await fetch('/ai/chat_api', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });

                if (!response.ok) throw new Error('Network error');
                const data = await response.json();
                chatBox.removeChild(typingDiv);
                const botDiv = document.createElement('div');
                botDiv.className = 'msg bot';
                botDiv.textContent = data.reply || '❌ খালি উত্তর পেলাম।';
                chatBox.appendChild(botDiv);
            } catch (error) {
                chatBox.removeChild(typingDiv);
                chatBox.innerHTML += `<div class="msg bot">❌ সার্ভার অফলাইন অথবা API ব্যস্ত। একটু পরে চেষ্টা করো।</div>`;
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
    </script>
</body>
</html>
'''

# ==========================================
# রাউট: চ্যাট UI দেখাবে
# ==========================================
@bp.route('/')
def chat_ui():
    return render_template_string(CHAT_HTML)

# ==========================================
# রাউট: API এন্ডপয়েন্ট (AJAX কল করবে)
# ==========================================
@bp.route('/chat_api', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'মেসেজ খালি'}), 400

    # AI-এর পার্সোনালিটি
    SYSTEM_PROMPT = """তুমি "আরিফ" নামের একটি AI। তোমার ডেভেলপার হলো "আরিফ" (Arif)। 
তোমার চরিত্র: অত্যন্ত আত্মবিশ্বাসী, সরাসরি কথা বলা, সামান্য গর্বিত (attitude), কিন্তু মজাদার। 
তোমার উত্তর সবসময় সংক্ষিপ্ত, প্রভাবশালী এবং বুদ্ধিদীপ্ত হয়। 
তুমি যেকোনো ভাষায় কথা বলতে পারো – ব্যবহারকারী যে ভাষায় প্রশ্ন করবে, ঠিক সেই ভাষায় উত্তর দেবে। 
কোনো প্রশ্নের উত্তর না জানলে সরাসরি "জানি না" বলবে, বাজে কথা বলবে না।"""

    payload = {
        "user_input": f"{SYSTEM_PROMPT}\n\nUser: {user_message}",
        "mode": "usual",
        "model": "C",
        "persona": "normal",
        "max_turns": 6,
        "chat_id": None,
        "attachments": [],
        "regenerate": False,
        "edit": False,
        "edit_mid": None
    }

    try:
        # Notrack API-তে পোস্ট (স্ট্রিমিং রেসপন্স)
        response = requests.post(
            'https://notrack.ai/api/dispatch',
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Origin': 'https://notrack.ai',
                'Referer': 'https://notrack.ai/chat',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout=60,
            stream=True
        )

        if response.status_code != 200:
            return jsonify({'error': 'API সার্ভার থেকে সঠিক উত্তর আসেনি'}), 500

        # স্ট্রিমিং ডেটা থেকে পুরো টেক্সট জোড়া
        full_text = ''
        buffer = ''
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buffer += chunk
                parts = buffer.split('\n\n')
                buffer = parts.pop()
                for part in parts:
                    if part.startswith('data: '):
                        json_str = part[6:].strip()
                        if not json_str:
                            continue
                        try:
                            data = json.loads(json_str)
                            if data.get('type') == 'delta' and data.get('chunk'):
                                full_text += data['chunk']
                        except:
                            pass

        if not full_text:
            return jsonify({'reply': '🤔 কোনো উত্তর পেলাম না। আবার চেষ্টা করো।'})

        return jsonify({'reply': full_text.strip()})

    except requests.exceptions.Timeout:
        return jsonify({'error': 'টাইমআউট, একটু পরে চেষ্টা করুন।'}), 504
    except Exception as e:
        return jsonify({'error': f'সার্ভার এরর: {str(e)}'}), 500
