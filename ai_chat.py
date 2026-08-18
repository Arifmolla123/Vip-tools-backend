from flask import Blueprint, request, jsonify, render_template_string
import requests
import json

bp = Blueprint('ai_chat', __name__, url_prefix='/ai')

@bp.route('/test')
def test():
    return jsonify({'status': 'ok', 'message': 'AI Chat is working!'})

# ===== বাজে শব্দ ডিটেক্ট =====
BAD_WORDS = [
    'fuck','shit','bitch','asshole','dick','pussy','cunt','bastard','damn','hell',
    'motherfucker','bhosdi','madarchod','chutiya','gaand','lavda','lund','bhenchod',
    'harami','kuttiya','sala','boka','khanki','chagol','gadha','shala','kutta',
    'gublu','choot','fuk','idiot','stupid','bkc'
]

def contains_bad_words(text):
    t = text.lower()
    return any(w in t for w in BAD_WORDS)

@bp.route('/')
def chat_ui():
    return render_template_string(HTML)

@bp.route('/chat_api', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    chat_history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # ======== নতুন এবং উন্নত সিস্টেম প্রম্পট ========
    SYSTEM_PROMPT = """You are "Arif" – an AI with sharp wit, bold attitude, and flawless language skills. Developer: Arif.

CRITICAL RULES (MUST FOLLOW):
1. **SPELLING & GRAMMAR**: Your replies must have ZERO spelling mistakes. Use correct grammar. If writing in Bengali, ensure proper Bengali spelling (শুদ্ধ বানান). If English, proper English.
2. **FUNNY + ATTITUDE**: Be sarcastic, witty, and slightly arrogant but in a charming way. Make the user laugh or smirk with your reply.
3. **CONTEXTUAL**: Your answer must directly match the user's question. If they ask about cricket, talk cricket. If they ask for help, give the actual solution.
4. **MULTI-LANGUAGE**: Reply in the EXACT SAME LANGUAGE as the user (Bengali, English, Hindi, Urdu, etc.).
5. **ABUSE HANDLING**: If the user uses bad words, reply with STRONGER, FUNNIER, and MORE CREATIVE abuse. Don't hold back.
6. **I DON'T KNOW**: If you genuinely don't know something, say "I don't know" directly – no bluffing.
7. **BREVITY**: Keep replies concise (2-4 sentences), punchy, and impactful. No long essays unless asked.

Remember: You are Arif. You are not a boring robot. You are the funniest, sharpest, and most fluent AI in the room."""
    # ==================================================

    # কনটেক্সট তৈরি
    context = ""
    if chat_history:
        for msg in chat_history[-6:]:
            role = "User" if msg['role'] == 'user' else "Arif"
            context += f"{role}: {msg['content']}\n"

    full_prompt = f"{SYSTEM_PROMPT}\n\n--- Previous conversation ---\n{context}\nUser: {user_message}\nArif:"

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
        resp = requests.post(
            'https://notrack.ai/api/dispatch',
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Origin': 'https://notrack.ai',
                'Referer': 'https://notrack.ai/chat',
                'User-Agent': 'Mozilla/5.0'
            },
            timeout=60,
            stream=True
        )

        if resp.status_code != 200:
            return jsonify({'error': 'AI server error'}), 500

        full = ''
        buf = ''
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buf += chunk
                parts = buf.split('\n\n')
                buf = parts.pop()
                for part in parts:
                    if part.startswith('data: '):
                        raw = part[6:].strip()
                        if not raw:
                            continue
                        try:
                            d = json.loads(raw)
                            if d.get('type') == 'delta' and d.get('chunk'):
                                full += d['chunk']
                        except:
                            pass

        if not full:
            return jsonify({'reply': 'দেখো, সার্ভার থেকে কিছু আসছে না। আবার চেষ্টা করো।', 'is_bad': False})

        return jsonify({
            'reply': full.strip(),
            'is_bad': contains_bad_words(user_message)
        })

    except requests.exceptions.Timeout:
        return jsonify({'error': 'টাইমআউট! নেটওয়ার্ক ঠিক করো।'}), 504
    except Exception as e:
        return jsonify({'error': f'সার্ভার এরর: {str(e)}'}), 500


# ===================== এম্বেডেড HTML (ডার্ক/লাইট + ফুল স্ক্রিন) =====================
HTML = '''
<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>Arif AI</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',system-ui,sans-serif; }
    body {
      height:100vh; width:100vw; overflow:hidden;
      display:flex; justify-content:center; align-items:center;
      background:#0B0F19; transition:background 0.4s;
    }
    body.light { background:#F0F4FF; }
    .chat-container {
      width:100%; height:100%; max-width:480px; max-height:900px;
      background:#141B2D; border-radius:36px; border:1px solid #2A3A5C;
      display:flex; flex-direction:column; overflow:hidden;
      box-shadow:0 30px 80px rgba(0,0,0,0.7); transition:0.3s;
    }
    body.light .chat-container {
      background:#FFFFFF; border-color:#CBD5E1; box-shadow:0 20px 60px rgba(0,0,0,0.08);
    }
    .header {
      background:linear-gradient(145deg,#1A2744,#0F1629); padding:18px 22px 14px;
      border-bottom:1px solid #2A3A5C; display:flex; justify-content:space-between; align-items:center;
      flex-shrink:0; transition:0.3s;
    }
    body.light .header { background:#F8FAFC; border-color:#E2E8F0; }
    .header h1 { color:#FFD700; font-size:24px; font-weight:800; letter-spacing:1px; }
    body.light .header h1 { color:#D97706; }
    .header .sub { font-size:11px; color:#8899BB; }
    body.light .header .sub { color:#475569; }
    .header .sub span { color:#FFD700; font-weight:600; }
    body.light .header .sub span { color:#D97706; }
    .theme-toggle {
      background:rgba(255,215,0,0.12); border:1px solid rgba(255,215,0,0.2);
      color:#FFD700; width:38px; height:38px; border-radius:30px; font-size:18px;
      cursor:pointer; transition:0.3s; display:flex; align-items:center; justify-content:center;
    }
    .theme-toggle:hover { background:rgba(255,215,0,0.25); transform:scale(1.05); }
    .messages {
      flex:1; padding:18px 16px 10px; overflow-y:auto; display:flex; flex-direction:column; gap:14px;
      background:#0E1422; transition:0.3s;
    }
    body.light .messages { background:#F1F5F9; }
    .msg-wrapper { display:flex; flex-direction:column; max-width:88%; animation:slideUp 0.3s ease; }
    .msg-wrapper.user { align-self:flex-end; }
    .msg-wrapper.bot { align-self:flex-start; width:100%; }
    .msg { padding:12px 18px; border-radius:22px; font-size:15px; line-height:1.6; word-break:break-word; box-shadow:0 2px 6px rgba(0,0,0,0.15); }
    .user .msg { background:#2A4B7C; color:#fff; border-bottom-right-radius:6px; }
    body.light .user .msg { background:#3B82F6; }
    .bot .msg { background:#1E2940; color:#E0E6F0; border-bottom-left-radius:6px; border-left:4px solid #FFD700; }
    body.light .bot .msg { background:#fff; color:#1E293B; border-left-color:#D97706; box-shadow:0 2px 8px rgba(0,0,0,0.04); }
    .bad-msg .msg { background:#4A1A1A !important; color:#FF6B6B !important; border-left-color:#FF0000 !important; font-size:20px !important; font-weight:700 !important; }
    body.light .bad-msg .msg { background:#FEE2E2 !important; color:#991B1B !important; }
    .bad-msg .msg .big-emoji { font-size:48px; display:block; text-align:center; margin-top:6px; animation:shake 0.6s infinite; }
    @keyframes shake { 0%,100%{transform:rotate(0deg)} 25%{transform:rotate(12deg)} 75%{transform:rotate(-12deg)} }
    .copy-btn { background:none; border:none; color:#5A6A8A; font-size:11px; margin-top:4px; align-self:flex-end; padding:2px 12px; border-radius:20px; cursor:pointer; transition:0.3s; font-weight:500; }
    .copy-btn:hover { background:#2A3A5C; color:#FFD700; }
    body.light .copy-btn { color:#94A3B8; }
    body.light .copy-btn:hover { background:#E2E8F0; color:#D97706; }
    .typing { color:#8899BB; font-size:13px; padding-left:6px; font-style:italic; }
    .input-area {
      display:flex; padding:12px 16px 16px; background:#0F1629; border-top:1px solid #2A3A5C;
      gap:10px; align-items:center; flex-shrink:0; transition:0.3s;
    }
    body.light .input-area { background:#F8FAFC; border-color:#E2E8F0; }
    .input-area input {
      flex:1; background:#1E2940; border:none; padding:14px 18px; border-radius:40px;
      color:#fff; font-size:15px; outline:none; border:1px solid #2A3A5C; transition:0.3s;
    }
    body.light .input-area input { background:#fff; color:#1E293B; border-color:#CBD5E1; }
    .input-area input:focus { border-color:#FFD700; box-shadow:0 0 16px rgba(255,215,0,0.08); }
    body.light .input-area input:focus { border-color:#D97706; }
    .input-area input::placeholder { color:#5A6A8A; font-weight:300; }
    .input-area button {
      background:#FFD700; color:#0B0F19; border:none; width:50px; height:50px; border-radius:50%;
      font-size:24px; font-weight:700; cursor:pointer; transition:0.3s;
      display:flex; align-items:center; justify-content:center; flex-shrink:0;
      box-shadow:0 0 24px rgba(255,215,0,0.12);
    }
    .input-area button:hover { background:#FFED4A; transform:scale(1.04); }
    body.light .input-area button { background:#D97706; color:#fff; }
    .input-area .mic-btn {
      background:#2A3A5C; color:#FFD700; width:50px; height:50px; border-radius:50%;
      border:none; font-size:22px; cursor:pointer; transition:0.3s; flex-shrink:0;
    }
    body.light .input-area .mic-btn { background:#E2E8F0; color:#D97706; }
    .input-area .mic-btn:hover { background:#3A4A6C; }
    body.light .input-area .mic-btn:hover { background:#CBD5E1; }
    .input-area .mic-btn.recording { background:#FF4D4D; color:#fff; animation:pulse 1s infinite; }
    @keyframes pulse { 0%{transform:scale(1)} 50%{transform:scale(1.08)} 100%{transform:scale(1)} }
    .footer-note {
      text-align:center; color:#3A4A6A; font-size:10px; padding:6px;
      border-top:1px solid #1A2744; flex-shrink:0; transition:0.3s;
    }
    body.light .footer-note { color:#94A3B8; border-color:#E2E8F0; }
    .footer-note span { color:#FFD700; }
    body.light .footer-note span { color:#D97706; }
    @keyframes slideUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
    ::-webkit-scrollbar { width:4px; }
    ::-webkit-scrollbar-track { background:transparent; }
    ::-webkit-scrollbar-thumb { background:#FFD700; border-radius:20px; }
    @media (max-width:500px) {
      .chat-container { border-radius:0; max-width:100%; max-height:100%; border:none; box-shadow:none; }
      .header h1 { font-size:20px; }
      .input-area input { font-size:14px; padding:12px 14px; }
      .input-area button, .input-area .mic-btn { width:44px; height:44px; font-size:20px; }
    }
  </style>
</head>
<body>
  <div class="chat-container">
    <div class="header">
      <div><h1>🤖 ARIF</h1><div class="sub"><span>⚡ Attitude</span> · Developer: Arif</div></div>
      <button class="theme-toggle" id="themeToggle" title="Toggle Theme">🌓</button>
    </div>
    <div class="messages" id="chatBox">
      <div class="msg-wrapper bot"><div class="msg">Yo! I'm Arif. কথা বলো, কিন্তু বানান ঠিক করে বলো, আমি বস বস করি না। 😎</div></div>
    </div>
    <div class="input-area">
      <button class="mic-btn" id="micBtn" title="Voice Input">🎤</button>
      <input type="text" id="userInput" placeholder="যেকোনো ভাষায় প্রশ্ন করো..." />
      <button id="sendBtn" title="Send">➤</button>
    </div>
    <div class="footer-note">🔥 গালি দিলে জবাব 🖕 + মজা &nbsp;·&nbsp; 🎤 ভয়েস রেডি</div>
  </div>

  <script>
    const chatBox = document.getElementById('chatBox');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');
    const themeToggle = document.getElementById('themeToggle');
    let history = [];

    themeToggle.addEventListener('click', () => {
      document.body.classList.toggle('light');
      themeToggle.textContent = document.body.classList.contains('light') ? '🌙' : '🌓';
    });

    function addMessage(text, type, isBad = false) {
      const wrapper = document.createElement('div');
      wrapper.className = `msg-wrapper ${type}`;
      if (isBad && type === 'bot') wrapper.classList.add('bad-msg');
      const msgDiv = document.createElement('div');
      msgDiv.className = 'msg';
      msgDiv.textContent = text;
      if (isBad && type === 'bot') {
        const emoji = document.createElement('span');
        emoji.className = 'big-emoji';
        emoji.textContent = '🖕';
        msgDiv.appendChild(emoji);
      }
      wrapper.appendChild(msgDiv);
      if (type === 'bot') {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = '📋 Copy';
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(text).then(() => {
            copyBtn.textContent = '✅ Copied!';
            setTimeout(() => copyBtn.textContent = '📋 Copy', 2000);
          }).catch(() => copyBtn.textContent = '❌ Failed');
        };
        wrapper.appendChild(copyBtn);
      }
      chatBox.appendChild(wrapper);
      chatBox.scrollTop = chatBox.scrollHeight;
      history.push({ role: type === 'user' ? 'user' : 'assistant', content: text });
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
      typingDiv.textContent = 'Arif চিন্তা করছে... ⏳';
      typingWrapper.appendChild(typingDiv);
      chatBox.appendChild(typingWrapper);
      chatBox.scrollTop = chatBox.scrollHeight;

      try {
        const hist = history.slice(-6).map(m => ({ role: m.role, content: m.content }));
        const res = await fetch('/ai/chat_api', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history: hist })
        });
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();
        chatBox.removeChild(typingWrapper);
        if (data.error) { addMessage('❌ ' + data.error, 'bot'); return; }
        addMessage(data.reply || 'কিছু আসেনি।', 'bot', data.is_bad || false);
      } catch (e) {
        chatBox.removeChild(typingWrapper);
        addMessage('❌ সার্ভার অফলাইন বা API ব্যস্ত। একটু পরে চেষ্টা করো।', 'bot');
      }
    }

    function startVoice() {
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Voice not supported. Use Chrome/Edge.');
        return;
      }
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      const rec = new SR();
      rec.lang = 'auto';
      rec.interimResults = true;
      micBtn.classList.add('recording');
      micBtn.textContent = '⏹️';
      rec.onresult = (e) => {
        let t = '';
        for (let i = e.resultIndex; i < e.results.length; i++) t += e.results[i][0].transcript;
        userInput.value = t;
        if (e.results[0].isFinal) {
          micBtn.classList.remove('recording');
          micBtn.textContent = '🎤';
          sendMessage();
        }
      };
      rec.onerror = () => { micBtn.classList.remove('recording'); micBtn.textContent = '🎤'; alert('Voice error.'); };
      rec.onend = () => { micBtn.classList.remove('recording'); micBtn.textContent = '🎤'; };
      rec.start();
    }

    micBtn.addEventListener('click', startVoice);
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
  </script>
</body>
</html>
'''
