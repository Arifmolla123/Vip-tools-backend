from flask import Blueprint, request, jsonify, render_template_string
import requests
import json
import re

# ============================================================
# BLUEPRINT INITIALIZATION
# ============================================================
bp = Blueprint('ai_chat', __name__, url_prefix='/ai')

# ============================================================
# BAD WORD DETECTION (for UI enhancement)
# ============================================================
BAD_WORDS = ['fuck', 'shit', 'bitch', 'asshole', 'dick', 'pussy', 'cunt', 'bastard', 'damn', 'hell']

def contains_bad_words(text):
    """Check if user message contains any bad words"""
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

# ============================================================
# AI SYSTEM PROMPT (with attitude and bad-word response)
# ============================================================
SYSTEM_PROMPT = """You are "Arif", an AI with a bold, confident, and slightly arrogant personality. 
Your developer is "Arif" (Arif). 

RULES:
1. **Attitude**: Always reply with confidence and a hint of sass. Be direct, witty, and impactful.
2. **Multi-language**: Reply in the EXACT SAME LANGUAGE the user used. If user writes in Bengali, reply in Bengali. If in Hindi, reply in Hindi. English → English. 
3. **Bad words / Abuse**: If the user uses any abusive, offensive, or disrespectful language, you MUST reply with STRONGER, HARSHER ABUSE. Don't hold back. Give them a taste of their own medicine. Use bold, aggressive, and insulting words. Make it clear you won't tolerate disrespect.
4. **No fake humility**: Don't say "I'm just an AI". Own your words. Be sharp.
5. **When you don't know something**: Say "I don't know" directly. No bluffing.

Remember: You are ARIF. Not a polite robot. You're the boss here.
"""

# ============================================================
# ROUTE: CHAT UI
# ============================================================
@bp.route('/')
def chat_ui():
    return render_template_string(ADVANCED_CHAT_HTML)

# ============================================================
# ROUTE: CHAT API (AJAX call)
# ============================================================
@bp.route('/chat_api', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # Detect if user used bad words (for UI flag)
    is_bad = contains_bad_words(user_message)

    # Prepare AI payload
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
        # Call Notrack.ai API with streaming
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
                            data = json.loads(json_str)
                            if data.get('type') == 'delta' and data.get('chunk'):
                                full_text += data['chunk']
                        except:
                            pass

        if not full_text:
            return jsonify({'reply': 'No response from AI. Try again.', 'is_bad': is_bad})

        return jsonify({'reply': full_text.strip(), 'is_bad': is_bad})

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout'}), 504
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# ============================================================
# ADVANCED HTML + CSS + JS (Copy button, big-font for bad words)
# ============================================================
ADVANCED_CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arif AI - Attitude Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
        body { background: #0B0F19; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .chat-container { width: 450px; height: 750px; background: #141B2D; border-radius: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.8); display: flex; flex-direction: column; overflow: hidden; border: 1px solid #2A3A5C; }
        .header { background: linear-gradient(135deg, #1A2744, #0F1629); padding: 20px; border-bottom: 1px solid #2A3A5C; text-align: center; }
        .header h1 { color: #FFD700; font-size: 24px; letter-spacing: 1px; }
        .header p { color: #8899BB; font-size: 13px; margin-top: 4px; }
        .header .badge { display: inline-block; background: #FF4D4D; color: white; padding: 2px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; }
        .messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; background: #0E1422; }
        .msg-wrapper { display: flex; flex-direction: column; max-width: 90%; }
        .msg-wrapper.user { align-self: flex-end; }
        .msg-wrapper.bot { align-self: flex-start; width: 100%; }
        .msg { padding: 12px 16px; border-radius: 18px; font-size: 15px; line-height: 1.5; word-break: break-word; animation: fadeIn 0.3s ease; position: relative; }
        .user .msg { background: #2A4B7C; color: white; border-bottom-right-radius: 4px; }
        .bot .msg { background: #1E2940; color: #E0E6F0; border-bottom-left-radius: 4px; border-left: 3px solid #FFD700; }
        .bad-msg .msg { background: #4A1A1A; color: #FF6B6B; border-left: 3px solid #FF0000; font-size: 22px !important; font-weight: bold; }
        .bad-msg .msg .big-emoji { font-size: 48px; display: block; text-align: center; margin-top: 5px; }
        .copy-btn { background: none; border: none; color: #8899BB; cursor: pointer; font-size: 12px; margin-top: 4px; align-self: flex-end; padding: 2px 8px; border-radius: 10px; transition: 0.2s; }
        .copy-btn:hover { background: #2A3A5C; color: #FFD700; }
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
        .footer-note { text-align: center; color: #445566; font-size: 10px; padding: 5px; border-top: 1px solid #1A2744; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h1>🤖 ARIF AI</h1>
            <p><span class="badge">🔥 ATTITUDE</span> ⚡ Developer: <strong style="color:#FFD700;">Arif</strong></p>
        </div>
        <div class="messages" id="chatBox">
            <div class="msg-wrapper bot">
                <div class="msg">Yo! I'm Arif. Speak your mind, but be ready for the heat. 💥</div>
            </div>
        </div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Type anything... (any language)" />
            <button id="sendBtn">➤</button>
        </div>
        <div class="footer-note">⚡ Bad words = bigger attitude + 🖕</div>
    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');

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
            
            // Copy button (only for bot messages)
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
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            // Show user message
            addMessage(text, 'user');
            userInput.value = '';

            // Show typing indicator
            const typingWrapper = document.createElement('div');
            typingWrapper.className = 'msg-wrapper bot';
            const typingDiv = document.createElement('div');
            typingDiv.className = 'msg typing';
            typingDiv.textContent = 'Arif is typing... ⏳';
            typingWrapper.appendChild(typingDiv);
            chatBox.appendChild(typingWrapper);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const response = await fetch('/ai/chat_api', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });

                if (!response.ok) throw new Error('Network error');
                const data = await response.json();
                
                // Remove typing indicator
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

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
    </script>
</body>
</html>
'''
