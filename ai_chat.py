from flask import Blueprint, request, jsonify, render_template_string
import requests
import json
import re

# ============================================================
# BLUEPRINT INITIALIZATION
# ============================================================
bp = Blueprint('ai_chat', __name__, url_prefix='/ai')

# ============================================================
# TEST ROUTE
# ============================================================
@bp.route('/test')
def test():
    return jsonify({'status': 'ok', 'message': 'AI Chat is working!'})

# ============================================================
# BAD WORD DETECTION (Multi-language)
# ============================================================
BAD_WORDS = [
    'fuck', 'shit', 'bitch', 'asshole', 'dick', 'pussy', 'cunt', 'bastard', 'damn', 'hell',
    'motherfucker', 'bhosdi', 'madarchod', 'chutiya', 'gaand', 'lavda', 'lund', 'bhenchod',
    'harami', 'kuttiya', 'sala', 'boka', 'khanki', 'chagol', 'gadha', 'shala', 'kutta',
    'gublu', 'choot', 'fuk', 'idiot', 'stupid', 'bkc'
]

def contains_bad_words(text):
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

# ============================================================
# ROUTE: CHAT UI (HTML এম্বেডেড)
# ============================================================
@bp.route('/')
def chat_ui():
    return render_template_string(CHAT_HTML)

# ============================================================
# ROUTE: CHAT API
# ============================================================
@bp.route('/chat_api', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    chat_history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # System prompt with attitude + bad word handling
    SYSTEM_PROMPT = """You are "Arif" – a bold, confident, and sharp AI. Your developer is "Arif".

RULES:
1. Reply with **attitude** – be direct, witty, and a bit arrogant. No fake humility.
2. Reply in the **EXACT SAME LANGUAGE** the user used.
3. If the user uses abusive/bad words, reply with **STRONGER, HARSHER ABUSE**. Give them a taste of their own medicine.
4. If you don't know something, say "I don't know" – no bluffing.
5. Keep your replies concise, impactful, and interesting.
"""

    # Build context from history (last 6 messages)
    context = ""
    if chat_history:
        for msg in chat_history[-6:]:
            role = "User" if msg.get('role') == 'user' else "Arif"
            context += f"{role}: {msg.get('content')}\n"

    full_prompt = f"{SYSTEM_PROMPT}\n\n--- Previous conversation ---\n{context}\nUser: {user_message}"

    payload = {
        "user_input": full_prompt,
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
            return jsonify({'error': 'AI server error'}), 500

        # Parse streaming response
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
                            data_chunk = json.loads(json_str)
                            if data_chunk.get('type') == 'delta' and data_chunk.get('chunk'):
                                full_text += data_chunk['chunk']
                        except:
                            pass

        if not full_text:
            return jsonify({'reply': 'No response from AI. Try again.', 'is_bad': False})

        is_bad = contains_bad_words(user_message)
        return jsonify({'reply': full_text.strip(), 'is_bad': is_bad})

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout'}), 504
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


# ============================================================
# EMBBEDED HTML (Fully styled, all features)
# ============================================================
CHAT_HTML = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Arif AI - Attitude</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        body {
            background: #0B0F19;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }
        .chat-container {
            width: 460px;
            height: 760px;
            background: #141B2D;
            border-radius: 40px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,215,0,0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid #2A3A5C;
        }
        .header {
            background: linear-gradient(135deg, #1A2744, #0F1629);
            padding: 22px 20px 16px;
            border-bottom: 1px solid #2A3A5C;
            text-align: center;
            position: relative;
        }
        .header::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 20%;
            width: 60%;
            height: 2px;
            background: linear-gradient(90deg, transparent, #FFD700, transparent);
            border-radius: 10px;
        }
        .header h1 {
            color: #FFD700;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 3px;
            text-shadow: 0 0 20px rgba(255,215,0,0.3);
        }
        .header p {
            color: #8899BB;
            font-size: 13px;
            margin-top: 4px;
            letter-spacing: 1px;
        }
        .header .badge {
            display: inline-block;
            background: #FF4D4D;
            color: #fff;
            padding: 3px 14px;
            border-radius: 30px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            margin-right: 4px;
            vertical-align: middle;
        }
        .header .dev-name {
            color: #FFD700;
            font-weight: 700;
        }
        .messages {
            flex: 1;
            padding: 20px 18px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
            background: #0E1422;
        }
        .msg-wrapper {
            display: flex;
            flex-direction: column;
            max-width: 92%;
            animation: slideUp 0.3s ease;
        }
        .msg-wrapper.user {
            align-self: flex-end;
        }
        .msg-wrapper.bot {
            align-self: flex-start;
            width: 100%;
        }
        .msg {
            padding: 12px 18px;
            border-radius: 22px;
            font-size: 15px;
            line-height: 1.6;
            word-break: break-word;
            position: relative;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .user .msg {
            background: #2A4B7C;
            color: #FFFFFF;
            border-bottom-right-radius: 6px;
        }
        .bot .msg {
            background: #1E2940;
            color: #E0E6F0;
            border-bottom-left-radius: 6px;
            border-left: 4px solid #FFD700;
        }
        .bad-msg .msg {
            background: #4A1A1A !important;
            color: #FF6B6B !important;
            border-left: 4px solid #FF0000 !important;
            font-size: 22px !important;
            font-weight: 800 !important;
            text-shadow: 0 0 10px rgba(255,0,0,0.3);
        }
        .bad-msg .msg .big-emoji {
            font-size: 52px;
            display: block;
            text-align: center;
            margin-top: 8px;
            animation: shake 0.5s ease infinite;
        }
        @keyframes shake {
            0%,100% { transform: rotate(0deg); }
            25% { transform: rotate(15deg); }
            75% { transform: rotate(-15deg); }
        }
        .copy-btn {
            background: none;
            border: none;
            color: #5A6A8A;
            cursor: pointer;
            font-size: 11px;
            margin-top: 6px;
            align-self: flex-end;
            padding: 4px 12px;
            border-radius: 20px;
            transition: 0.3s;
            font-weight: 500;
        }
        .copy-btn:hover {
            background: #2A3A5C;
            color: #FFD700;
        }
        .typing {
            color: #8899BB;
            font-size: 13px;
            padding-left: 6px;
            font-style: italic;
        }
        .input-area {
            display: flex;
            padding: 14px 18px;
            background: #0F1629;
            border-top: 1px solid #2A3A5C;
            gap: 12px;
            align-items: center;
        }
        .input-area input {
            flex: 1;
            background: #1E2940;
            border: none;
            padding: 14px 20px;
            border-radius: 40px;
            color: #FFFFFF;
            font-size: 15px;
            outline: none;
            border: 1px solid #2A3A5C;
            transition: 0.3s;
        }
        .input-area input:focus {
            border-color: #FFD700;
            box-shadow: 0 0 15px rgba(255,215,0,0.1);
        }
        .input-area input::placeholder {
            color: #5A6A8A;
            font-weight: 300;
        }
        .input-area button {
            background: #FFD700;
            color: #0B0F19;
            border: none;
            width: 52px;
            height: 52px;
            border-radius: 50%;
            font-size: 24px;
            font-weight: 900;
            cursor: pointer;
            transition: 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 20px rgba(255,215,0,0.15);
        }
        .input-area button:hover {
            background: #FFED4A;
            transform: scale(1.06);
            box-shadow: 0 0 30px rgba(255,215,0,0.3);
        }
        .input-area .mic-btn {
            background: #2A3A5C;
            color: #FFD700;
            width: 52px;
            height: 52px;
            border-radius: 50%;
            border: none;
            font-size: 22px;
            cursor: pointer;
            transition: 0.3s;
        }
        .input-area .mic-btn:hover {
            background: #3A4A6C;
        }
        .input-area .mic-btn.recording {
            background: #FF4D4D;
            color: #FFFFFF;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        .footer-note {
            text-align: center;
            color: #3A4A6A;
            font-size: 10px;
            padding: 8px;
            border-top: 1px solid #1A2744;
            letter-spacing: 0.5px;
        }
        .footer-note span {
            color: #FFD700;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        ::-webkit-scrollbar {
            width: 5px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: #FFD700;
            border-radius: 20px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #FFED4A;
        }
        @media (max-width: 500px) {
            .chat-container {
                width: 100%;
                height: 95vh;
                border-radius: 24px;
            }
            .header h1 {
                font-size: 22px;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h1>🤖 ARIF</h1>
            <p><span class="badge">⚡ Attitude</span> Developer: <span class="dev-name">Arif</span></p>
        </div>
        <div class="messages" id="chatBox">
            <div class="msg-wrapper bot">
                <div class="msg">Yo! I'm Arif. Speak your mind – I'll match your energy. 💥</div>
            </div>
        </div>
        <div class="input-area">
            <button class="mic-btn" id="micBtn" onclick="startVoice()" title="Voice Input">🎤</button>
            <input type="text" id="userInput" placeholder="Ask anything... (any language)" />
            <button id="sendBtn" title="Send">➤</button>
        </div>
        <div class="footer-note">
            🔥 Bad words = bigger attitude + <span>🖕</span> &nbsp;·&nbsp; 🎤 Voice ready
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const micBtn = document.getElementById('micBtn');
        let chatHistory = [];

        function addMessage(text, type, isBad = false) {
            const wrapper = document.createElement('div');
            wrapper.className = `msg-wrapper ${type}`;
            if (isBad && type === 'bot') {
                wrapper.classList.add('bad-msg');
            }
            const msgDiv = document.createElement('div');
            msgDiv.className = 'msg';
            msgDiv.textContent = text;
            if (isBad && type === 'bot') {
                const emojiSpan = document.createElement('span');
                emojiSpan.className = 'big-emoji';
                emojiSpan.textContent = '🖕';
                msgDiv.appendChild(emojiSpan);
            }
            wrapper.appendChild(msgDiv);
            if (type === 'bot') {
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-btn';
                copyBtn.textContent = '📋 Copy';
                copyBtn.onclick = function() {
                    navigator.clipboard.writeText(text).then(() => {
                        copyBtn.textContent = '✅ Copied!';
                        setTimeout(() => copyBtn.textContent = '📋 Copy', 2000);
                    }).catch(() => {
                        copyBtn.textContent = '❌ Failed';
                    });
                };
                wrapper.appendChild(copyBtn);
            }
            chatBox.appendChild(wrapper);
            chatBox.scrollTop = chatBox.scrollHeight;
            chatHistory.push({ role: type === 'user' ? 'user' : 'assistant', content: text });
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            addMessage(text, 'user');
            userInput.value = '';
            const typingWrapper = document.createElement('div');
            typingWrapper.className = 'msg-wrapper bot';
            const typingDiv = document.createElement('div');
            typingDiv.className = 'msg typing';
            typingDiv.textContent = 'Arif is thinking... ⏳';
            typingWrapper.appendChild(typingDiv);
            chatBox.appendChild(typingWrapper);
            chatBox.scrollTop = chatBox.scrollHeight;
            try {
                const historyPayload = chatHistory.slice(-6).map(m => ({
                    role: m.role,
                    content: m.content
                }));
                const response = await fetch('/ai/chat_api', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: text,
                        history: historyPayload
                    })
                });
                if (!response.ok) throw new Error('Network error');
                const data = await response.json();
                chatBox.removeChild(typingWrapper);
                if (data.error) {
                    addMessage('❌ ' + data.error, 'bot');
                    return;
                }
                const reply = data.reply || 'No response from AI.';
                const isBad = data.is_bad || false;
                addMessage(reply, 'bot', isBad);
            } catch (error) {
                chatBox.removeChild(typingWrapper);
                addMessage('❌ Server offline or API busy. Try again later.', 'bot');
            }
        }

        function startVoice() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('Voice input not supported in this browser. Use Chrome/Edge.');
                return;
            }
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            recognition.lang = 'auto';
            recognition.continuous = false;
            recognition.interimResults = true;
            micBtn.classList.add('recording');
            micBtn.textContent = '⏹️';
            recognition.onresult = function(event) {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                userInput.value = transcript;
                if (event.results[0].isFinal) {
                    micBtn.classList.remove('recording');
                    micBtn.textContent = '🎤';
                    sendMessage();
                }
            };
            recognition.onerror = function() {
                micBtn.classList.remove('recording');
                micBtn.textContent = '🎤';
                alert('Voice recognition error. Try again.');
            };
            recognition.onend = function() {
                micBtn.classList.remove('recording');
                micBtn.textContent = '🎤';
            };
            recognition.start();
        }

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
'''
