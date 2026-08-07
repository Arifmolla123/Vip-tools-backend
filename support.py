# -*- coding: utf-8 -*-
from flask import Blueprint, render_template_string, request, jsonify
import requests
import json
import time
import logging

bp = Blueprint('support', __name__, url_prefix='/support')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORT_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Cyber Tools Support</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #070d17;
            color: #e0f0ec;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            padding: 12px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .app {
            max-width: 860px;
            width: 100%;
            background: linear-gradient(160deg, #0f1a26 0%, #091018 100%);
            border-radius: 40px;
            padding: 24px 20px 16px;
            border: 1px solid #1e3347;
            box-shadow: 0 30px 70px rgba(0,0,0,0.9), inset 0 1px 0 #2a4a5a;
            display: flex;
            flex-direction: column;
            height: 95vh;
            max-height: 820px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #1fc7b0;
            padding-bottom: 14px;
            margin-bottom: 14px;
            flex-wrap: wrap;
            gap: 10px;
            flex-shrink: 0;
        }
        .header-left {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .header-left .brand {
            display: flex;
            flex-direction: column;
        }
        .header-left .brand h1 {
            font-size: 1.6rem;
            font-weight: 700;
            background: linear-gradient(135deg, #1fc7b0, #b0fff0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
        }
        .header-left .brand span {
            font-size: 0.75rem;
            color: #6a8a8a;
            letter-spacing: 0.3px;
        }
        .header-left .icon {
            font-size: 2.2rem;
            color: #1fc7b0;
        }
        .header-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .lang-indicator {
            background: #0d1a26;
            padding: 4px 16px;
            border-radius: 40px;
            border: 1px solid #1e3347;
            font-size: 0.7rem;
            color: #88b8b0;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .lang-indicator i { color: #1fc7b0; }
        .chat-window {
            background: #0a121e;
            border-radius: 24px;
            padding: 16px;
            flex: 1;
            min-height: 300px;
            max-height: 100%;
            overflow-y: auto;
            border: 1px solid #1a2e3e;
            margin-bottom: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            scroll-behavior: smooth;
        }
        .chat-window::-webkit-scrollbar { width: 4px; }
        .chat-window::-webkit-scrollbar-track { background: #0a121e; }
        .chat-window::-webkit-scrollbar-thumb { background: #1fc7b0; border-radius: 10px; }
        .msg {
            max-width: 88%;
            padding: 14px 18px;
            border-radius: 18px;
            font-size: 0.95rem;
            line-height: 1.7;
            word-wrap: break-word;
            animation: fadeUp 0.3s ease;
            position: relative;
        }
        .msg.user {
            align-self: flex-end;
            background: linear-gradient(135deg, #1a2e3e, #0f1f2e);
            border-bottom-right-radius: 4px;
            border: 1px solid #2a4a5a;
            color: #d0f0ea;
        }
        .msg.bot {
            align-self: flex-start;
            background: #0d1a26;
            border-left: 4px solid #1fc7b0;
            border-bottom-left-radius: 4px;
            color: #e0f0ec;
            white-space: pre-wrap;
        }
        .msg.bot strong { color: #b0fff0; }
        .msg.bot ul { margin: 6px 0 6px 18px; padding-left: 6px; list-style-type: none; }
        .msg.bot ul li { position: relative; padding-left: 20px; margin-bottom: 4px; }
        .msg.bot ul li::before { content: "▸"; position: absolute; left: 0; color: #1fc7b0; font-weight: bold; }
        .msg .time {
            font-size: 0.6rem;
            color: #5f8a88;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .typing-indicator {
            align-self: flex-start;
            background: #0d1a26;
            padding: 10px 18px;
            border-radius: 30px;
            border-left: 4px solid #1fc7b0;
            display: flex;
            align-items: center;
            gap: 6px;
            color: #88b8b0;
            font-size: 0.8rem;
        }
        .typing-indicator .dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #1fc7b0;
            border-radius: 50%;
            animation: bounce 1.2s infinite;
        }
        .typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .input-area {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            background: #0a121e;
            border-radius: 60px;
            padding: 6px 6px 6px 20px;
            border: 1px solid #1a2e3e;
            transition: 0.2s;
            flex-shrink: 0;
        }
        .input-area:focus-within {
            border-color: #1fc7b0;
            box-shadow: 0 0 0 3px #1fc7b022;
        }
        .input-area input {
            flex: 1;
            background: transparent;
            border: none;
            color: #d0f0ea;
            font-size: 0.95rem;
            padding: 10px 0;
            outline: none;
            min-width: 140px;
            font-family: inherit;
        }
        .input-area input::placeholder { color: #3a5a5a; }
        .input-area .btn {
            background: #1fc7b0;
            border: none;
            color: #0b1119;
            padding: 10px 24px;
            border-radius: 60px;
            font-weight: 700;
            font-size: 0.9rem;
            cursor: pointer;
            transition: 0.15s;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }
        .input-area .btn:active { transform: scale(0.95); }
        .input-area .btn:disabled { opacity: 0.5; pointer-events: none; }
        .input-area .btn-outline {
            background: transparent;
            color: #88b8b0;
            border: 1px solid #1a2e3e;
            padding: 10px 16px;
        }
        .input-area .btn-outline:hover {
            border-color: #1fc7b0;
            color: #b0fff0;
        }
        .footer {
            text-align: center;
            margin-top: 12px;
            font-size: 0.7rem;
            color: #2a4a5a;
            display: flex;
            justify-content: center;
            gap: 24px;
            flex-wrap: wrap;
            flex-shrink: 0;
        }
        .footer a {
            color: #3a6a7a;
            text-decoration: none;
            transition: 0.2s;
        }
        .footer a:hover { color: #1fc7b0; }
        @media (max-width: 480px) {
            .app { padding: 12px; max-height: 98vh; height: 98vh; }
            .header-left .brand h1 { font-size: 1.2rem; }
            .chat-window { min-height: 220px; padding: 12px; }
            .msg { font-size: 0.85rem; padding: 10px 14px; }
            .input-area { padding: 4px 4px 4px 14px; }
            .input-area .btn { padding: 8px 16px; font-size: 0.8rem; }
        }
        .glow-border { position: relative; }
        .glow-border::before {
            content: '';
            position: absolute;
            top: -1px;
            left: -1px;
            right: -1px;
            bottom: -1px;
            border-radius: 40px;
            background: linear-gradient(135deg, #1fc7b033, #f5b34233);
            z-index: -1;
            opacity: 0.3;
        }
        .welcome-text {
            font-size: 0.9rem;
            color: #b0d0d0;
            margin-bottom: 4px;
        }
    </style>
</head>
<body>
<div class="app glow-border">
    <div class="header">
        <div class="header-left">
            <div class="icon"><i class="fas fa-headset"></i></div>
            <div class="brand">
                <h1>Cyber Tools</h1>
                <span>Support · 24/7</span>
            </div>
        </div>
        <div class="header-right">
            <span class="lang-indicator"><i class="fas fa-globe"></i> <span id="langLabel">English</span></span>
        </div>
    </div>

    <div class="chat-window" id="chatWindow">
        <div class="msg bot">
            <div class="welcome-text">👋 Welcome to <strong>Cyber Tools Support</strong></div>
            Ask me about app features, VIP unlock, tools, groups, channels, or the developer.<br>
            <span style="font-size:0.8rem;color:#5f8a88;">(Bengali, English, Hindi, Hinglish, Arabic, Urdu – all supported)</span>
            <div class="time"><i class="far fa-clock"></i> Now</div>
        </div>
    </div>

    <div class="input-area">
        <input type="text" id="userInput" placeholder="Type your question here...">
        <button class="btn" id="sendBtn"><i class="fas fa-paper-plane"></i> Send</button>
        <button class="btn btn-outline" id="clearBtn" title="Clear chat"><i class="fas fa-eraser"></i></button>
    </div>

    <div class="footer">
        <span><i class="fas fa-shield-alt"></i> Secure</span>
        <a href="#" id="whatsappLink"><i class="fab fa-whatsapp"></i> WhatsApp</a>
        <a href="#" id="telegramLink"><i class="fab fa-telegram-plane"></i> Telegram</a>
        <span><i class="fas fa-language"></i> Any language</span>
    </div>
</div>

<script>
    (function() {
        "use strict";

        var chatWindow = document.getElementById('chatWindow');
        var userInput = document.getElementById('userInput');
        var sendBtn = document.getElementById('sendBtn');
        var clearBtn = document.getElementById('clearBtn');
        var langLabel = document.getElementById('langLabel');

        var API_URL = '/support/chat';

        var DOCUMENTATION = `
=== CYBER TOOLS APP – COMPLETE GUIDE ===

🔹 HOME PAGE
• Tools: Device Info, News Generator, Age Calculator, Day Finder, URL Shortener, QR Code Scan/Gen, Style Name/Text Generator, Free Host file.
• Categories: Network, Security, Web, System.
• Drawer: My Profile, VIP Menu, About Us, Contact, Share App.
• Bottom Nav: Home, VIP Tools, Popular.

🔹 VIP UNLOCK
• Enter your registered Name and VIP Key.
• VIP Key is pre-generated and stored securely.
• Users CANNOT generate keys themselves – they must contact the developer.
• To get a VIP Key, contact developer Arif via WhatsApp or Telegram.
• On success → localStorage vip_status = 'active'
• VIP expiry: lifetime or specific date.

🔹 VIP TOOLS
• Premium Apps, IP Tracker, Cyber bomber, Cyber Phish, Telegram Tracker, Cyber SPY.
• If not VIP → shows "Access Denied" popup and redirects to vip.html.

🔹 SETTINGS
• View your VIP credentials.
• Delete account → only admin (Arif) can reactivate.

🔹 SHARE APP
• This page is already inside the app. Users do NOT need an external download link.
• If user asks for download link, tell them they are already inside the app.

🔹 JOIN COMMUNITY
• WhatsApp Group: https://chat.whatsapp.com/Gu9rE3yaSDnCJutYOKPUME
• YouTube Channel: https://youtube.com/@hackingcyber-q4s
• These are official community channels for support, updates, and tutorials.

🔹 DEVELOPER INFO
• Name: Arif
• Title: System Creator & Admin
• Bio: Hello! I am Arif. A passionate technology enthusiast and full-stack developer. I specialize in cybersecurity, modern web architectures, and custom application development.
• Skills: Ethical Hacking, Web Designer, App Development, Video Editor
• Security Signature: ARIF

🔹 SUPPORT
• There is NO support team. Only the developer Arif handles everything.
        `;

        var isTyping = false;

        function detectLanguage(text) {
            if (/[\u0980-\u09FF]/.test(text)) return 'বাংলা';
            if (/[\u0900-\u097F]/.test(text)) return 'हिन्दी';
            if (/[\u0600-\u06FF]/.test(text)) return 'العربية/اردو';
            var hinglishWords = ['kya', 'hai', 'nahi', 'aap', 'hum', 'tum', 'main', 'kaise', 'kyon', 'ho', 'hain', 'tha', 'thi', 'the', 'raha', 'rahi', 'rahe', 'sakta', 'sakti', 'sakte', 'chahiye', 'mil', 'de', 'le', 'kar', 'ko', 'se', 'mein', 'pe', 'ki', 'ka', 'ke', 'ne', 'bhi', 'hi', 'to', 'nahi', 'haan', 'ji', 'sir', 'madam', 'apka', 'apko', 'mera', 'tera', 'uska', 'unki', 'inke', 'jiska', 'jiski'];
            var words = text.toLowerCase().split(/\\s+/);
            var hinglishScore = 0;
            for (var i = 0; i < words.length; i++) {
                var w = words[i].replace(/[^a-z]/g, '');
                if (hinglishWords.indexOf(w) !== -1) hinglishScore++;
            }
            if (hinglishScore >= 2) return 'Hinglish';
            return 'English';
        }

        function addMessage(text, sender, time) {
            if (!time) time = new Date();
            var div = document.createElement('div');
            div.className = 'msg ' + sender;
            var hours = time.getHours().toString().padStart(2, '0');
            var minutes = time.getMinutes().toString().padStart(2, '0');
            var timeStr = hours + ':' + minutes;
            div.innerHTML = text + '<div class="time"><i class="far fa-clock"></i> ' + timeStr + '</div>';
            chatWindow.appendChild(div);
            chatWindow.scrollTop = chatWindow.scrollHeight;
            return div;
        }

        function showTyping() {
            if (isTyping) return;
            isTyping = true;
            var div = document.createElement('div');
            div.className = 'typing-indicator';
            div.id = 'typingIndicator';
            div.innerHTML = '<span>Typing</span><span class="dot"></span><span class="dot"></span><span class="dot"></span>';
            chatWindow.appendChild(div);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
        function hideTyping() {
            var el = document.getElementById('typingIndicator');
            if (el) el.remove();
            isTyping = false;
        }

        function getStaticAnswer(question) {
            var q = question.toLowerCase();
            // ইলিগ্যাল বা সিক্রেট প্রশ্নের জন্য ডিফল্ট মেসেজ
            var illegalKeywords = ['hack', 'crack', 'exploit', 'malware', 'virus', 'ransom', 'ddos', 'phish', 'spam', 'illegal', 'পাসওয়ার্ড', 'হ্যাক', 'ক্র্যাক', 'ফিশিং', 'স্পাই', 'ম্যালওয়্যার', 'আক্রমণ', 'সিক্রেট', 'firebase', 'ডাটাবেস', 'key'];
            var isIllegal = false;
            for (var i = 0; i < illegalKeywords.length; i++) {
                if (q.indexOf(illegalKeywords[i]) !== -1) {
                    isIllegal = true;
                    break;
                }
            }
            if (isIllegal) {
                return "আমি সাইবার টুলস সাপোর্ট এজেন্ট। আমি শুধু অ্যাপের ফিচার, VIP আনলক, টুলস, গ্রুপ, চ্যানেল বা ডেভেলপার সম্পর্কে প্রশ্নের উত্তর দিতে পারি। দয়া করে অ্যাপ সম্পর্কিত প্রশ্ন করুন।";
            }

            // বাকি স্ট্যাটিক উত্তর
            if (q.indexOf('vip') !== -1 || q.indexOf('key') !== -1 || q.indexOf('unlock') !== -1) {
                return "🔑 VIP keys are provided by the developer Arif. Please contact him via WhatsApp or Telegram.";
            }
            if (q.indexOf('group') !== -1 || q.indexOf('channel') !== -1 || q.indexOf('community') !== -1) {
                return "📢 You can join our WhatsApp Group (https://chat.whatsapp.com/Gu9rE3yaSDnCJutYOKPUME) or YouTube Channel (https://youtube.com/@hackingcyber-q4s).";
            }
            if (q.indexOf('developer') !== -1 || q.indexOf('arif') !== -1 || q.indexOf('who made') !== -1) {
                return "👨‍💻 The app is developed by Arif. He is a full-stack developer specializing in cybersecurity and app development.";
            }
            if (q.indexOf('tool') !== -1 || q.indexOf('feature') !== -1) {
                return "🛠️ Cyber Tools offers many features: Device Info, News Generator, Age Calculator, URL Shortener, QR Scanner, VIP Tools like IP Tracker, Cyber Bomber, and more.";
            }
            if (q.indexOf('download') !== -1 || q.indexOf('apk') !== -1) {
                return "📱 You are already inside the Cyber Tools app. To share it with friends, use the 'Share App' option from the drawer menu.";
            }
            return "আমি সাইবার টুলস সাপোর্ট এজেন্ট। আমি শুধু অ্যাপের ফিচার, VIP আনলক, টুলস, গ্রুপ, চ্যানেল বা ডেভেলপার সম্পর্কে প্রশ্নের উত্তর দিতে পারি। দয়া করে অ্যাপ সম্পর্কিত প্রশ্ন করুন।";
        }

        async function getAIResponse(question, detectedLang) {
            var prompt = `
You are the "Cyber Tools" support agent. Follow these rules strictly:

1. **CRITICAL: Reply EXACTLY in the same language as the user's question.**
   Detected language: ${detectedLang}.

2. **DO NOT answer any illegal, hacking, or secret questions.**
   If user asks about hacking, cracking, exploits, malware, virus, DDoS, phishing, spying, passwords, database, Firebase, or any secret/internal info:
   Reply: "আমি সাইবার টুলস সাপোর্ট এজেন্ট। আমি শুধু অ্যাপের ফিচার, VIP আনলক, টুলস, গ্রুপ, চ্যানেল বা ডেভেলপার সম্পর্কে প্রশ্নের উত্তর দিতে পারি। দয়া করে অ্যাপ সম্পর্কিত প্রশ্ন করুন।" (in the same language)

3. **Format your response cleanly**:
   - Use plain text, avoid markdown like #, **, __.
   - Use bullet points with "• " for lists.
   - Use blank lines between paragraphs.
   - Use emojis moderately (📱, 🔑, 👨‍💻, etc.).

4. **Never** say "I am an AI", "as an AI", "I can't".

5. **Use this documentation** for app-related answers:
${DOCUMENTATION}

User question: ${question}
            `.trim();

            var res = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: prompt })
            });
            if (!res.ok) {
                var errText = await res.text();
                throw new Error('HTTP ' + res.status + ': ' + errText.slice(0, 50));
            }
            var data = await res.json();
            if (data.error) throw new Error(data.error);
            return data.reply;
        }

        async function handleSend() {
            var question = userInput.value.trim();
            if (!question) return;

            var lang = detectLanguage(question);
            langLabel.textContent = lang;

            addMessage(question, 'user');
            userInput.value = '';
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            showTyping();

            try {
                var reply = await getAIResponse(question, lang);
                hideTyping();
                var formatted = reply
                    .replace(/\\n/g, '<br>')
                    .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                    .replace(/^#+\\s*/gm, '')
                    .replace(/^• /gm, '• ')
                    .replace(/^- /gm, '• ')
                    .replace(/^\\d+\\. /gm, function(m) { return '<br>' + m; });
                addMessage(formatted, 'bot');
            } catch (err) {
                hideTyping();
                var staticReply = getStaticAnswer(question);
                var msg = '⚠️ AI service is currently offline. Showing offline reply.<br><br>' + staticReply;
                addMessage(msg, 'bot');
                console.error('API Error:', err);
            } finally {
                sendBtn.disabled = false;
                sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send';
            }
        }

        function clearChat() {
            chatWindow.innerHTML = '';
            var welcome = document.createElement('div');
            welcome.className = 'msg bot';
            welcome.innerHTML = '👋 Chat cleared. Ask a new question.<div class="time"><i class="far fa-clock"></i> Now</div>';
            chatWindow.appendChild(welcome);
            langLabel.textContent = 'English';
        }

        sendBtn.addEventListener('click', handleSend);
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });
        clearBtn.addEventListener('click', clearChat);

        document.getElementById('whatsappLink').addEventListener('click', function(e) {
            e.preventDefault();
            window.open('https://wa.me/917865875762?text=Support+needed', '_blank');
        });
        document.getElementById('telegramLink').addEventListener('click', function(e) {
            e.preventDefault();
            window.open('https://t.me/your_support', '_blank');
        });

        console.log('✅ Cyber Tools Support ready (Flask backend)');
    })();
</script>
</body>
</html>
'''

@bp.route('/')
def support_page():
    return render_template_string(SUPPORT_HTML)


@bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400

    question = data['question']
    reply = call_ai_api(question)
    return jsonify({'reply': reply})


def call_ai_api(prompt):
    endpoint = 'http://de3.bot-hosting.net:21007/kilwa-claude'

    try:
        logger.info(f"Calling KILWA API: {endpoint}")
        resp = requests.get(
            endpoint,
            params={'text': prompt},
            timeout=20,
            headers={'User-Agent': 'CyberTools-Support/1.0'}
        )
        logger.info(f"KILWA API status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                result = resp.json()
                reply = result.get('reply') or result.get('response')
                if reply:
                    logger.info("✅ KILWA API success")
                    return reply
                else:
                    logger.warning(f"KILWA returned no reply: {result}")
            except json.JSONDecodeError:
                text = resp.text.strip()
                if text:
                    logger.info("✅ KILWA returned text")
                    return text
    except Exception as e:
        logger.error(f"KILWA API error: {str(e)[:100]}")

    logger.error("KILWA API failed. Falling back to static.")
    return get_static_answer(prompt)


def get_static_answer(question):
    q = question.lower()
    # ইলিগ্যাল বা সিক্রেট কীওয়ার্ড
    illegal_keywords = ['hack', 'crack', 'exploit', 'malware', 'virus', 'ransom', 'ddos', 'phish', 'spam', 'illegal', 'পাসওয়ার্ড', 'হ্যাক', 'ক্র্যাক', 'ফিশিং', 'স্পাই', 'ম্যালওয়্যার', 'আক্রমণ', 'সিক্রেট', 'firebase', 'ডাটাবেস', 'key']
    for word in illegal_keywords:
        if word in q:
            return "আমি সাইবার টুলস সাপোর্ট এজেন্ট। আমি শুধু অ্যাপের ফিচার, VIP আনলক, টুলস, গ্রুপ, চ্যানেল বা ডেভেলপার সম্পর্কে প্রশ্নের উত্তর দিতে পারি। দয়া করে অ্যাপ সম্পর্কিত প্রশ্ন করুন।"

    if 'vip' in q or 'key' in q or 'unlock' in q:
        return "🔑 VIP keys are provided by the developer Arif. Please contact him via WhatsApp or Telegram."
    if 'group' in q or 'channel' in q or 'community' in q:
        return "📢 You can join our WhatsApp Group (https://chat.whatsapp.com/Gu9rE3yaSDnCJutYOKPUME) or YouTube Channel (https://youtube.com/@hackingcyber-q4s)."
    if 'developer' in q or 'arif' in q or 'who made' in q:
        return "👨‍💻 The app is developed by Arif. He is a full-stack developer specializing in cybersecurity and app development."
    if 'tool' in q or 'feature' in q:
        return "🛠️ Cyber Tools offers many features: Device Info, News Generator, Age Calculator, URL Shortener, QR Scanner, VIP Tools like IP Tracker, Cyber Bomber, and more."
    if 'download' in q or 'apk' in q:
        return "📱 You are already inside the Cyber Tools app. To share it with friends, use the 'Share App' option from the drawer menu."
    return "আমি সাইবার টুলস সাপোর্ট এজেন্ট। আমি শুধু অ্যাপের ফিচার, VIP আনলক, টুলস, গ্রুপ, চ্যানেল বা ডেভেলপার সম্পর্কে প্রশ্নের উত্তর দিতে পারি। দয়া করে অ্যাপ সম্পর্কিত প্রশ্ন করুন।"