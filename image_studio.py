# -*- coding: utf-8 -*-
from flask import Blueprint, render_template_string, request, jsonify, session
import requests
import json
import logging
import uuid

bp = Blueprint('image_studio', __name__, url_prefix='/image_studio')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# HTML টেমপ্লেট – DeepSeek চ্যাট ইন্টারফেস
# ============================================================
DEEPSEEK_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <title>Cyber Tools – DeepSeek Chat</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #070d17; color: #e0f0ec; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; padding: 16px; min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .app { max-width: 820px; width: 100%; background: linear-gradient(160deg, #0f1a26, #091018); border-radius: 40px; padding: 28px 24px 20px; border: 1px solid #1e3347; box-shadow: 0 30px 70px rgba(0,0,0,0.9), inset 0 1px 0 #2a4a5a; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1fc7b0; padding-bottom: 14px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        .header-left { display: flex; align-items: center; gap: 14px; }
        .header-left .brand h1 { font-size: 1.7rem; font-weight: 700; background: linear-gradient(135deg, #1fc7b0, #b0fff0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; line-height: 1.2; }
        .header-left .brand span { font-size: 0.75rem; color: #6a8a8a; letter-spacing: 0.3px; }
        .header-left .icon { font-size: 2.2rem; color: #1fc7b0; }
        .header-right .lang-badge { background: #0d1a26; padding: 4px 16px; border-radius: 40px; border: 1px solid #1e3347; font-size: 0.7rem; color: #88b8b0; display: flex; align-items: center; gap: 6px; }
        .header-right .lang-badge i { color: #1fc7b0; }
        .chat-window { background: #0a121e; border-radius: 24px; padding: 16px; flex: 1; min-height: 400px; max-height: 600px; overflow-y: auto; border: 1px solid #1a2e3e; margin-bottom: 16px; display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth; }
        .chat-window::-webkit-scrollbar { width: 4px; }
        .chat-window::-webkit-scrollbar-track { background: #0a121e; }
        .chat-window::-webkit-scrollbar-thumb { background: #1fc7b0; border-radius: 10px; }
        .msg { max-width: 88%; padding: 14px 18px; border-radius: 18px; font-size: 0.95rem; line-height: 1.7; word-wrap: break-word; animation: fadeUp 0.3s ease; }
        .msg.user { align-self: flex-end; background: linear-gradient(135deg, #1a2e3e, #0f1f2e); border-bottom-right-radius: 4px; border: 1px solid #2a4a5a; color: #d0f0ea; }
        .msg.bot { align-self: flex-start; background: #0d1a26; border-left: 4px solid #1fc7b0; border-bottom-left-radius: 4px; color: #e0f0ec; white-space: pre-wrap; }
        .msg.bot strong { color: #b0fff0; }
        .msg .time { font-size: 0.6rem; color: #5f8a88; margin-top: 6px; display: flex; align-items: center; gap: 6px; }
        .typing-indicator { align-self: flex-start; background: #0d1a26; padding: 10px 18px; border-radius: 30px; border-left: 4px solid #1fc7b0; display: flex; align-items: center; gap: 6px; color: #88b8b0; font-size: 0.8rem; }
        .typing-indicator .dot { display: inline-block; width: 8px; height: 8px; background: #1fc7b0; border-radius: 50%; animation: bounce 1.2s infinite; }
        .typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .input-area { display: flex; gap: 10px; flex-wrap: wrap; background: #0a121e; border-radius: 60px; padding: 6px 6px 6px 20px; border: 1px solid #1a2e3e; transition: 0.2s; }
        .input-area:focus-within { border-color: #1fc7b0; box-shadow: 0 0 0 3px #1fc7b022; }
        .input-area input { flex: 1; background: transparent; border: none; color: #d0f0ea; font-size: 0.95rem; padding: 10px 0; outline: none; min-width: 140px; font-family: inherit; }
        .input-area input::placeholder { color: #3a5a5a; }
        .input-area .btn { background: #1fc7b0; border: none; color: #0b1119; padding: 10px 24px; border-radius: 60px; font-weight: 700; font-size: 0.9rem; cursor: pointer; transition: 0.15s; display: flex; align-items: center; gap: 8px; white-space: nowrap; }
        .input-area .btn:active { transform: scale(0.95); }
        .input-area .btn:disabled { opacity: 0.5; pointer-events: none; }
        .input-area .btn-outline { background: transparent; color: #88b8b0; border: 1px solid #1a2e3e; padding: 10px 16px; }
        .input-area .btn-outline:hover { border-color: #1fc7b0; color: #b0fff0; }
        .footer { text-align: center; margin-top: 20px; font-size: 0.7rem; color: #2a4a5a; display: flex; justify-content: center; gap: 24px; flex-wrap: wrap; border-top: 1px solid #0f1a26; padding-top: 16px; }
        .footer a { color: #3a6a7a; text-decoration: none; transition: 0.2s; }
        .footer a:hover { color: #1fc7b0; }
        .attitude { background: #1fc7b008; border-left: 3px solid #1fc7b0; padding: 10px 16px; border-radius: 12px; font-size: 0.85rem; color: #b0d0d0; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .attitude i { color: #1fc7b0; font-size: 1.2rem; }
        .back-link { display: inline-flex; align-items: center; gap: 8px; color: #88b8b0; text-decoration: none; font-size: 0.85rem; margin-bottom: 12px; transition: 0.2s; }
        .back-link:hover { color: #1fc7b0; }
        .model-selector { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
        .model-selector select { background: #0a121e; border: 1px solid #1a2e3e; color: #e0f0ec; padding: 8px 16px; border-radius: 40px; font-size: 0.85rem; outline: none; }
        .model-selector select:focus { border-color: #1fc7b0; }
        .conv-id { font-size: 0.7rem; color: #5f8a88; text-align: center; margin-top: 8px; }
        @media (max-width: 480px) { .app { padding: 16px; } .header-left .brand h1 { font-size: 1.3rem; } }
    </style>
</head>
<body>
    <div class="app">
        <a href="/support" class="back-link"><i class="fas fa-arrow-left"></i> Back to Support</a>

        <div class="header">
            <div class="header-left">
                <div class="icon"><i class="fas fa-comments"></i></div>
                <div class="brand">
                    <h1>Cyber Tools</h1>
                    <span>DeepSeek Chat Pro · by Arif</span>
                </div>
            </div>
            <div class="header-right">
                <span class="lang-badge"><i class="fas fa-globe"></i> Multi‑Lingual</span>
            </div>
        </div>

        <div class="attitude">
            <i class="fas fa-robot"></i>
            <span>
                <strong>🛡️ Cyber Tools Attitude:</strong> 
                DeepSeek AI with Memory — Hinglish, বাংলা, हिन्दी, العربية সব ভাষায় কাজ করে। 
                <span style="color:#5f8a88;font-size:0.8rem;">(যেকোনো ভাষায় প্রশ্ন করুন)</span>
            </span>
        </div>

        <div class="model-selector">
            <select id="modelSelect">
                <option value="1">DeepSeek V3.2</option>
                <option value="2">DeepSeek R1</option>
                <option value="3">DeepSeek Coder</option>
            </select>
            <button class="btn btn-outline" id="newChatBtn" style="padding:8px 20px; width:auto;">
                <i class="fas fa-plus"></i> New Chat
            </button>
        </div>

        <div class="chat-window" id="chatWindow">
            <div class="msg bot">
                👋 Welcome to <strong>DeepSeek Chat Pro</strong><br>
                Ask me anything — I remember our conversation! 😊
                <div class="time"><i class="far fa-clock"></i> Now</div>
            </div>
        </div>

        <div class="input-area">
            <input type="text" id="userInput" placeholder="Type your message here..." />
            <button class="btn" id="sendBtn"><i class="fas fa-paper-plane"></i> Send</button>
            <button class="btn btn-outline" id="clearBtn" title="Clear chat"><i class="fas fa-eraser"></i></button>
        </div>

        <div class="conv-id" id="convIdDisplay">Conversation ID: <span id="convIdValue">None</span></div>

        <div class="footer">
            <span><i class="fas fa-shield-alt"></i> Cyber Tools · Arif</span>
            <a href="https://chat.whatsapp.com/Gu9rE3yaSDnCJutYOKPUME" target="_blank"><i class="fab fa-whatsapp"></i> WhatsApp Group</a>
            <a href="https://youtube.com/@hackingcyber-q4s" target="_blank"><i class="fab fa-youtube"></i> YouTube Channel</a>
            <span><i class="fas fa-language"></i> Any language</span>
        </div>
    </div>

    <script>
        (function() {
            "use strict";

            const API_URL = '/deepseek/chat';

            const chatWindow = document.getElementById('chatWindow');
            const userInput = document.getElementById('userInput');
            const sendBtn = document.getElementById('sendBtn');
            const clearBtn = document.getElementById('clearBtn');
            const newChatBtn = document.getElementById('newChatBtn');
            const modelSelect = document.getElementById('modelSelect');
            const convIdValue = document.getElementById('convIdValue');

            let conversationId = null;
            let isTyping = false;

            function addMessage(text, sender, time) {
                if (!time) time = new Date();
                const div = document.createElement('div');
                div.className = 'msg ' + sender;
                const timeStr = time.getHours().toString().padStart(2,'0') + ':' + time.getMinutes().toString().padStart(2,'0');
                div.innerHTML = text + `<div class="time"><i class="far fa-clock"></i> ${timeStr}</div>`;
                chatWindow.appendChild(div);
                chatWindow.scrollTop = chatWindow.scrollHeight;
                return div;
            }

            function showTyping() {
                if (isTyping) return;
                isTyping = true;
                const div = document.createElement('div');
                div.className = 'typing-indicator';
                div.id = 'typingIndicator';
                div.innerHTML = '<span>DeepSeek is thinking</span><span class="dot"></span><span class="dot"></span><span class="dot"></span>';
                chatWindow.appendChild(div);
                chatWindow.scrollTop = chatWindow.scrollHeight;
            }

            function hideTyping() {
                const el = document.getElementById('typingIndicator');
                if (el) el.remove();
                isTyping = false;
            }

            async function sendMessage() {
                const message = userInput.value.trim();
                if (!message) return;

                addMessage(message, 'user');
                userInput.value = '';
                sendBtn.disabled = true;
                sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

                showTyping();

                try {
                    const payload = {
                        model: modelSelect.value,
                        message: message
                    };
                    if (conversationId) {
                        payload.conversation_id = conversationId;
                    }

                    const res = await fetch(API_URL, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    const data = await res.json();

                    hideTyping();
                    sendBtn.disabled = false;
                    sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send';

                    if (data.success && data.response) {
                        if (data.conversation_id) {
                            conversationId = data.conversation_id;
                            convIdValue.textContent = conversationId;
                        }
                        let reply = data.response.replace(/\n/g, '<br>');
                        addMessage(reply, 'bot');
                    } else {
                        addMessage('⚠️ Error: ' + (data.error || 'Unknown error'), 'bot');
                    }
                } catch (err) {
                    hideTyping();
                    sendBtn.disabled = false;
                    sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send';
                    addMessage('⚠️ Network error: ' + err.message, 'bot');
                }
            }

            function clearChat() {
                chatWindow.innerHTML = '';
                const welcome = document.createElement('div');
                welcome.className = 'msg bot';
                welcome.innerHTML = '👋 Chat cleared. Ask a new question.<div class="time"><i class="far fa-clock"></i> Now</div>';
                chatWindow.appendChild(welcome);
                // conversationId রাখি – মেমোরি রিসেট করতে চাইলে নতুন চ্যাট বাটন ব্যবহার করবেন
            }

            function newChat() {
                conversationId = null;
                convIdValue.textContent = 'None';
                chatWindow.innerHTML = '';
                const welcome = document.createElement('div');
                welcome.className = 'msg bot';
                welcome.innerHTML = '🆕 New conversation started! Ask me anything.<div class="time"><i class="far fa-clock"></i> Now</div>';
                chatWindow.appendChild(welcome);
            }

            sendBtn.addEventListener('click', sendMessage);
            userInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
            clearBtn.addEventListener('click', clearChat);
            newChatBtn.addEventListener('click', newChat);

            console.log('✅ Cyber Tools DeepSeek Chat ready');
        })();
    </script>
</body>
</html>
'''

# ============================================================
# রুট – পেজ রেন্ডার
# ============================================================
@bp.route('/')
def deepseek_page():
    return render_template_string(DEEPSEEK_HTML)


# ============================================================
# চ্যাট API প্রোক্সি – DeepSeek API-তে কল করে CORS যোগ করে
# ============================================================
@bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat_proxy():
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    if request.method == 'OPTIONS':
        return ('', 200, headers)

    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': 'Message is required'}), 400, headers

        model = data.get('model', '1')
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', None)

        api_url = 'https://zecora0.serv00.net/deepseek.php'

        payload = {
            'model': model,
            'message': message
        }
        if conversation_id:
            payload['conversation_id'] = conversation_id

        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }

        logger.info(f"Calling DeepSeek API with payload: {payload}")
        resp = requests.post(
            api_url,
            json=payload,
            headers=req_headers,
            timeout=30
        )

        logger.info(f"DeepSeek response status: {resp.status_code}")
        logger.info(f"DeepSeek response body: {resp.text[:500]}")

        try:
            result = resp.json()
        except:
            result = {'success': False, 'error': 'Invalid JSON response from API'}
 # আপনার ব্র্যান্ডিং যোগ করুন
        if result.get('success'):
            result['dev'] = '🔥 Cyber Tools · Arif'

        return jsonify(result), resp.status_code, headers

    except Exception as e:
        logger.error(f"DeepSeek proxy error: {str(e)[:100]}")
        return jsonify({'success': False, 'error': str(e)}), 500, headers