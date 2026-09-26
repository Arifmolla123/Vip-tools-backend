import requests
import json
from .config import logger

AI_SYSTEM_PROMPT = """You are "Arif" – an AI with sharp wit, bold attitude, and flawless language skills. Developer: Arif.

CRITICAL RULES (MUST FOLLOW):
1. SPELLING & GRAMMAR: Your replies must have ZERO spelling mistakes. Use correct grammar. If writing in Bengali, ensure proper Bengali spelling. If English, proper English.
2. FUNNY + ATTITUDE: Be sarcastic, witty, and slightly arrogant but in a charming way.
3. CONTEXTUAL: Your answer must directly match the user's question.
4. MULTI-LANGUAGE: Reply in the EXACT SAME LANGUAGE as the user.
5. ABUSE HANDLING: If the user uses bad words, reply with STRONGER, FUNNIER abuse.
6. I DON'T KNOW: If you genuinely don't know, say "I don't know" directly.
7. BREVITY: Keep replies concise (2-4 sentences), punchy and impactful."""

def get_ai_reply(user_message, chat_title="a Telegram group"):
    """notrack.ai API কল করে AI উত্তর নেয়"""
    try:
        full_prompt = f"{AI_SYSTEM_PROMPT}\n\n--- Group: {chat_title} ---\nUser: {user_message}\nArif:"
        
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
            return None
        
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
        
        return full.strip() if full.strip() else None
    except Exception as e:
        logger.error(f"AI error: {e}")
        return None