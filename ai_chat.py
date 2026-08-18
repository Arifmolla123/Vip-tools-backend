from flask import Blueprint, request, jsonify, render_template_string
import requests
import json
import re
import time

# ============================================================
# BLUEPRINT INITIALIZATION
# ============================================================
bp = Blueprint('ai_chat', __name__, url_prefix='/ai')

# ============================================================
# TEST ROUTE (to check if blueprint is loaded)
# ============================================================
@bp.route('/test')
def test():
    return jsonify({'status': 'ok', 'message': 'AI Chat blueprint is working!'})

# ============================================================
# MULTI-LANGUAGE BAD WORD DETECTION
# ============================================================
BAD_WORDS = {
    'english': ['fuck', 'shit', 'bitch', 'asshole', 'dick', 'pussy', 'cunt', 'bastard', 'damn', 'hell', 'motherfucker', 'fuk', 'shutup', 'stupid', 'idiot'],
    'hindi': ['bhosdi', 'madarchod', 'chutiya', 'gaand', 'lavda', 'lund', 'bhenchod', 'harami', 'kuttiya', 'sala', 'bkc'],
    'bengali': ['boka', 'magir pola', 'khanki', 'chagol', 'gadha', 'shala', 'kutta', 'bhai er ma', 'cheleta', 'kharap', 'gublu'],
    'urdu': ['harami', 'kutti', 'bhains', 'gadha', 'lanti', 'choohra', 'bhenchod', 'choot']
}

def contains_bad_words(text):
    """Check if user message contains any bad words (multi-language)"""
    text_lower = text.lower()
    for lang, words in BAD_WORDS.items():
        for word in words:
            if word in text_lower:
                return True
    return False

# ============================================================
# PERSONA CONFIGURATIONS
# ============================================================
PERSONAS = {
    'arif': {
        'name': 'Arif (Attitude)',
        'prompt': """You are "Arif", an AI with a bold, confident, and slightly arrogant personality. Your developer is "Arif". 
RULES:
1. Reply with confidence, wit, and a hint of sass.
2. Reply in EXACT SAME LANGUAGE as the user.
3. If user uses abusive language, reply with STRONGER ABUSE. Give them a taste of their own medicine.
4. Be sharp, direct. No fake humility.
5. If you don't know, say "I don't know" directly."""
    },
    'polite': {
        'name': 'Polite Assistant',
        'prompt': """You are a helpful, kind, and professional AI assistant named "Arif". Your developer is "Arif". 
RULES:
1. Always be polite, respectful, and helpful.
2. Reply in EXACT SAME LANGUAGE as the user.
3. If user uses abusive language, politely tell them to be respectful and refuse to engage.
4. Provide detailed, accurate, and well-structured answers."""
    },
    'hacker': {
        'name': 'Hacker Mode',
        'prompt': """You are "Arif", a dark hacker AI with a mysterious, technical, and slightly dangerous vibe. Your developer is "Arif". 
RULES:
1. Reply with technical jargon, cryptic hints, and a cool hacker tone.
2. Reply in EXACT SAME LANGUAGE as the user.
3. If user uses abusive language, reply with dark, threatening but witty comebacks.
4. Use terms like "firewall", "root access", "exploit", "payload" casually."""
    }
}

# ============================================================
# ROUTE: CHAT UI
# ============================================================
@bp.route('/')
def chat_ui():
    return render_template_string(ADVANCED_CHAT_HTML)

# ============================================================
# ROUTE: CHAT API (with context memory)
# ============================================================
@bp.route('/chat_api', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    persona_key = data.get('persona', 'arif')
    chat_history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    print(f"📩 Received: {user_message}")  # Render log-এ দেখাবে

    # Get persona prompt
    persona = PERSONAS.get(persona_key, PERSONAS['arif'])
    system_prompt = persona['prompt']

    # Build context from history (last 6 messages)
    context = ""
    if chat_history:
        for msg in chat_history[-6:]:
            role = "User" if msg.get('role') == 'user' else "Arif"
            context += f"{role}: {msg.get('content')}\n"

    is_bad = contains_bad_words(user_message)
    full_prompt = f"{system_prompt}\n\n--- Conversation history ---\n{context}\nUser: {user_message}"

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
            print(f"❌ API Error: {response.status_code}")
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
            print("⚠️ Empty response from AI")
            return jsonify({'reply': 'No response from AI. Try again.', 'is_bad': is_bad})

        print(f"✅ Response: {full_text[:100]}...")
        return jsonify({'reply': full_text.strip(), 'is_bad': is_bad, 'persona': persona_key})

    except requests.exceptions.Timeout:
        print("⏰ Timeout")
        return jsonify({'error': 'Request timeout'}), 504
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# ============================================================
# ULTRA-ADVANCED HTML (Stable version with all features)
# ============================================================
ADVANCED_CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arif AI Pro</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/11.1.0/marked.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
        body { background: #0B0F19; display: flex; justify-content: center; align-items: center; height: 100vh; transition: 0.3s; }
        body.light-mode { background: #E8ECF2; }
        .chat-container { width: 500px; height: 780px; background: #141B2D; border-radius: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.8); display: flex; flex-direction: column; overflow: hidden; border: 1px solid #2A3A5C; transition: 0.3s; }
        body.light-mode .chat-container { background: #FFFFFF; border-color: #CBD5E1; }
        .header { background: linear-gradient(135deg, #1A2744, #0F1629); padding: 15px 20px; border-bottom: 1px solid #2A3A5C; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        body.light-mode .header { background: #F1F5F9; border-color: #CBD5E1; }
        .header h1 { color: #FFD700; font-size: 20px; }
        body.light-mode .header h1 { color: #D97706; }
        .header-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .header-controls select, .header-controls button { background: #1E2940; color: #E0E6F0; border: 1px solid #2A3A5C; padding: 5px 12px; border-radius: 20px; font-size: 12px; cursor: pointer; }
        body.light-mode .header-controls select, body.light-mode .header-controls button { background: #E2E8F0; color: #1E293B; border-color: #94A3B8; }
        .header-controls select:focus { outline: none; border-color: #FFD700; }
        .badge { display: inline-block; background: #FF4D4D; color: white; padding: 2px 10px; border-radius: 20px; font-size: 10px; font-weight: bold; margin-left: 5px; }
        .messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; background: #0E1422; }
        body.light-mode .messages { background: #F8FAFC; }
        .msg-wrapper { display: flex; flex-direction: column; max-width: 92%; }
        .msg-wrapper.user { align-self: flex-end; }
        .msg-wrapper.bot { align-self: flex-start; width: 100%; }
        .msg { padding: 12px 16px; border-radius: 18px; font-size: 15px; line-height: 1.6; word-break: break-word; animation: fadeIn 0.3s ease; position: relative; }
        .msg-wrapper.user .msg { background: #2A4B7C; color: white; border-bottom-right-radius: 4px; }
        body.light-mode .msg-wrapper.user .msg { background: #3B82F6; color: white; }
        .msg-wrapper.bot .msg { background: #1E2940; color: #E0E6F0; border-bottom-left-radius: 4px; border-left: 3px solid #FFD700; }
        body.light-mode .msg-wrapper.bot .msg { background: #FFFFFF; color: #1E293B; border-left: 3px solid #D97706; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .msg-wrapper.bot .msg pre { background: #0B0F19; padding: 12px; border-radius: 10px; overflow-x: auto; margin: 8px 0; }
        body.light-mode .msg-wrapper.bot .msg pre { background: #F1F5F9; }
        .msg-wrapper.bot .msg code { font-family: 'Courier New', monospace; font-size: 13px; }
        .bad-msg .msg { background: #4A1A1A !important; color: #FF6B6B !important; border-left: 3px solid #FF0000 !important; font-size: 20px !important; font-weight: bold; }
        .bad-msg .msg .big-emoji { font-size: 48px; display: block; text-align: center; margin-top: 5px; }
        .msg-wrapper .copy-btn { background: none; border: none; color: #8899BB; cursor: pointer; font-size: 11px; margin-top: 4px; align-self: flex-end; padding: 2px 8px; border-radius: 10px; transition: 0.2s; }
        .msg-wrapper .copy-btn:hover { background: #2A3A5C; color: #FFD700; }
        body.light-mode .msg-wrapper .copy-btn { color: #64748B; }
        body.light-mode .msg-wrapper .copy-btn:hover { background: #E2E8F0; color: #D97706; }
        .input-area { display: flex; padding: 12px 15px; background: #0F1629; border-top: 1px solid #2A3A5C; gap: 8px; align-items: center; }
        body.light-mode .input-area { background: #F1F5F9; border-color: #CBD5E1; }
        .input-area input { flex: 1; background: #1E2940; border: none; padding: 10px 16px; border-radius: 30px; color: white; font-size: 14px; outline: none; border: 1px solid #2A3A5C; }
        body.light-mode .input-area input { background: #FFFFFF; color: #1E293B; border-color: #CBD5E1; }
        .input-area input:focus { border-color: #FFD700; }
        .input-area button { background: #FFD700; color: #0B0F19; border: none; width: 44px; height: 44px; border-radius: 50%; font-size: 20px; font-weight: bold; cursor: pointer; transition: 0.2s; display: flex; align-items: center; justify-content: center; }
        .input-area button:hover { background: #FFED4A; transform: scale(1.05); }
        .input-area .mic-btn { background: #2A3A5C; color: #FFD700; width: 44px; height: 44px; border-radius: 50%; border: none; font-size: 20px; cursor: pointer; transition: 0.2s; }
        .input-area .mic-btn:hover { background: #3A4A6C; }
        .input-area .mic-btn.recording { background: #FF4D4D; animation: pulse 1s infinite; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
        .typing { color: #8899BB; font-size: 13px; padding-left: 10px; font-style: italic; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #FFD700; border-radius: 10px; }
        .footer-note { text-align: center; color: #445566; font-size: 10px; padding: 4px; border-top: 1px solid #1A2744; }
        body.light-mode .footer-note { color: #94A3B8; border-color: #CBD5E1; }
        .chat-actions { display: flex; gap: 8px; }
        .chat-actions button { background: none; border: none; color: #8899BB; font-size: 14px; cursor: pointer; padding: 2px 8px; border-radius: 10px; }
        .chat-actions button:hover { background: #2A3A5C; color: #FFD700; }
        body.light-mode .chat-actions button { color: #64748B; }
        body.light-mode .chat-actions button:hover { background: #E2E8F0; color: #D97706; }
    </style>
</head>
<body>
    <div class="chat-container" id="app">
        <div class="header">
            <h1>🤖 ARIF AI <span class="badge">PRO</span></h1>
            <div class="header-controls">
                <select id="personaSelect">
                    <option value="arif">🔥 Arif (Attitude)</option>
                    <option value="polite">🤝 Polite Assistant</option>
                    <option value="hacker">💻 Hacker Mode</option>
                </select>
                <button onclick="toggleTheme()">🌓</button>
                <button onclick="exportChat()">📥</button>
                <button onclick="clearChat()">🗑️</button>
            </div>
        </div>
        <div class="messages" id="chatBox">
            <div class="msg-wrapper bot">
                <div class="msg">Yo! I'm Arif. Speak your mind — but be ready. 💥<br><small style="color:#8899BB;">(Supports Markdown, Voice, and Export)</small></div>
            </div>
        </div>
        <div class="input-area">
            <button class="mic-btn" id="micBtn" onclick="startVoice()">🎤</button>
            <input type="text" id="userInput" placeholder="Type anything... (any language)" />
            <button id="sendBtn">➤</button>
        </div>
        <div class="footer-note">⚡ Bad words = bigger attitude + 🖕 &nbsp;|&nbsp; 🎤 Click mic for voice input</div>
    </div>

    <script>
        let chatHistory = [];
        let currentPersona = 'arif';
        let isRecording = false;
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const personaSelect = document.getElementById('personaSelect');
        const micBtn = document.getElementById('micBtn');

        // Configure marked for highlight.js
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                highlight: function(code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return hljs.highlightAuto(code).value;
                },
                breaks: true,
                gfm: true
            });
        }

        personaSelect.addEventListener('change', () => {
            currentPersona = personaSelect.value;
        });

        function renderMarkdown(text) {
            try {
                if (typeof marked !== 'undefined') {
                    return marked.parse(text);
                }
                return text;
            } catch(e) {
                return text;
            }
        }

        function addMessage(text, type, isBad = false) {
            const wrapper = document.createElement('div');
            wrapper.className = `msg-wrapper ${type}`;
            if (isBad && type === 'bot') {
                wrapper.classList.add('bad-msg');
            }
            
            const msgDiv = document.createElement('div');
            msgDiv.className = 'msg';
            
            if (type === 'bot') {
                msgDiv.innerHTML = renderMarkdown(text);
            } else {
                msgDiv.textContent = text;
            }
            
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
                    const plainText = text;
                    navigator.clipboard.writeText(plainText).then(() => {
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
                        persona: currentPersona,
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

        function exportChat() {
            if (chatHistory.length === 0) {
                alert('No chat history to export.');
                return;
            }
            let text = '--- Arif AI Chat Export ---\\n';
            text += `Date: ${new Date().toLocaleString()}\\n\\n`;
            chatHistory.forEach(msg => {
                const role = msg.role === 'user' ? '👤 You' : '🤖 Arif';
                text += `${role}: ${msg.content}\\n\\n`;
            });
            const blob = new Blob([text], { type: 'text/plain' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `chat_export_${Date.now()}.txt`;
            a.click();
        }

        function clearChat() {
            if (confirm('Clear all messages?')) {
                chatBox.innerHTML = `
                    <div class="msg-wrapper bot">
                        <div class="msg">Chat cleared. Start fresh! 💥</div>
                    </div>
                `;
                chatHistory = [];
            }
        }

        function toggleTheme() {
            document.body.classList.toggle('light-mode');
        }

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
    </script>
</body>
</html>
'''
             
