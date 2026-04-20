import pyrebase
from flask import Flask, render_template_string, request, Response, stream_with_context
import cloudscraper
import re
import time
import threading
import os

app = Flask(__name__)

# Cloudscraper to bypass protection
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

# --- 1. FIREBASE SETUP ---
# Render par serviceAccount ki jagah seedha databaseURL use karna easy hai
config = {
    "apiKey": "AIzaSyAe5XKQlowY_AroKkQ80SeAYPqLnF02KoE",
    "authDomain": "animeverse-9eada.firebaseapp.com",
    "databaseURL": "https://animeverse-9eada-default-rtdb.firebaseio.com/",
    "storageBucket": "animeverse-9eada.appspot.com"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()

# Global dictionary to keep track of logs
monitor_logs = {}

# --- 2. FIREBASE HELPER ---
def save_to_firebase(anime, s, e, link):
    try:
        # A. Permanent Link Storage 
        db.child("animeverse_links").child(anime).child(f"S{s}").child(f"E{e}").set({
            "url": link,
            "bot": "#",
            "time": time.time()
        })

        # B. Added Today Section 
        today = time.strftime('%Y-%m-%d')
        db.child("added_today").child(today).child(anime).set({
            "id": anime,
            "s": s,
            "e": e,
            "timestamp": time.time()
        })
        return True
    except Exception as err:
        print(f"Firebase Error: {err}")
        return False

# --- 3. BACKGROUND MONITOR TASK ---
def monitor_thread_task(anime, s, e):
    global monitor_logs
    url = f"https://archive.toonworld4all.me/episode/{anime}-{s}x{e}"
    task_id = f"{anime}-{s}-{e}"
    monitor_logs[task_id] = f"🚀 Started Monitoring: {anime} S{s}E{e}\n"
    
    while True:
        t = time.strftime('%H:%M:%S')
        try:
            res = scraper.get(url, timeout=25)
            if res.status_code == 200:
                match = re.search(r'https?://[a-zA-Z0-9-]+\.pages\.dev/play/[^\s"\']+', res.text)
                if match:
                    save_to_firebase(anime, s, e, match.group(0))
                    monitor_logs[task_id] += f"[{t}] ✅ SUCCESS: Found & Added!\n"
                    break 
            
            monitor_logs[task_id] += f"[{t}] Checking... Not found yet. (Waiting 5m)\n"
            time.sleep(300)
        except Exception as err:
            monitor_logs[task_id] += f"[{t}] Error: {str(err)}\n"
            time.sleep(60)

# --- 4. HTML TEMPLATE ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AnimeVerse Admin PRO</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --accent: #ff7b00; --bg: #0b1118; --card: #1a2430; --monitor: #ff4757; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; padding: 10px; margin: 0; }
        .container { max-width: 600px; margin: auto; }
        .tabs { display: flex; overflow-x: auto; gap: 5px; margin-bottom: 10px; border-bottom: 1px solid #2d3748; }
        .tab-btn { padding: 12px 18px; background: #1a2430; border: none; color: #94a3b8; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 13px; font-weight: bold; white-space: nowrap; }
        .tab-btn.active { background: var(--accent); color: #000; }
        .tab-btn.mon-tab.active { background: var(--monitor); color: #fff; }
        .section { display: none; }
        .section.active { display: block; }
        .card { background: var(--card); padding: 20px; border-radius: 0 0 12px 12px; margin-bottom: 15px; border-top: 2px solid var(--accent); }
        input { width: 100%; padding: 12px; border-radius: 8px; background: #0d1621; color: white; border: 1px solid #334155; box-sizing: border-box; margin-bottom: 10px; outline: none; }
        button { width: 100%; padding: 15px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; color: white; transition: 0.3s; }
        #status { background: #000; padding: 15px; border-radius: 10px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 11px; border: 1px solid #2d3748; color: #adbac7; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align:center; color: var(--accent);">ANIMEVERSE ADMIN</h2>
        <div class="tabs">
            <div class="tab-btn active" onclick="openTab(event, 'bulk')">All Seasons</div>
            <div class="tab-btn" onclick="openTab(event, 'season')">Season</div>
            <div class="tab-btn" onclick="openTab(event, 'episode')">Episode</div>
            <div class="tab-btn mon-tab" onclick="openTab(event, 'monitor_tab')">Monitor 📡</div>
        </div>

        <div id="bulk" class="section active">
            <div class="card">
                <input type="text" id="slug_bulk" placeholder="Anime Slug">
                <button style="background: var(--accent);" onclick="start('bulk')">FETCH ALL</button>
            </div>
        </div>

        <div id="monitor_tab" class="section">
            <div class="card">
                <input type="text" id="slug_m" placeholder="Anime Slug">
                <input type="number" id="s_m" placeholder="Season">
                <input type="number" id="e_m" placeholder="Episode">
                <button style="background: var(--monitor);" onclick="start('monitor')">WATCH EPISODE</button>
            </div>
        </div>
        <div id="status">System Online...</div>
    </div>
    <script>
        function openTab(evt, name) {
            let s = document.getElementsByClassName("section");
            for (let i = 0; i < s.length; i++) s[i].classList.remove("active");
            document.getElementById(name).classList.add("active");
        }
        async function start(mode) {
            const status = document.getElementById('status');
            let url = `/fetch?mode=${mode}`; # Simplified for example
            const response = await fetch(url);
            # ... Reader logic for streaming logs ...
        }
    </script>
</body>
</html>
'''

# --- 5. ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/monitor')
def monitor_ep():
    anime = request.args.get('anime')
    s = request.args.get('season')
    e = request.args.get('ep')
    task_id = f"{anime}-{s}-{e}"
    t = threading.Thread(target=monitor_thread_task, args=(anime, s, e))
    t.daemon = True
    t.start()
    
    @stream_with_context
    def generate():
        yield f"🚀 Monitoring Started: {anime} S{s}E{e}\n"
        last_log_len = 0
        while task_id in monitor_logs:
            current_logs = monitor_logs[task_id]
            if len(current_logs) > last_log_len:
                new_content = current_logs[last_log_len:]
                yield new_content
                last_log_len = len(current_logs)
                if "✅" in new_content: break
            time.sleep(2)
    return Response(generate(), mimetype='text/html')

@app.route('/fetch')
def fetch_anime():
    anime = request.args.get('anime')
    s_num = request.args.get('season')
    e_num = request.args.get('ep')
    
    @stream_with_context
    def generate():
        seasons = [int(s_num)] if s_num else range(1, 15)
        for s in seasons:
            yield f"<b>Season {s}</b>...\n"
            misses = 0
            ep_range = range(int(e_num), int(e_num)+1) if e_num else range(1, 101)
            for e in ep_range:
                url = f"https://archive.toonworld4all.me/episode/{anime}-{s}x{e}"
                try:
                    res = scraper.get(url, timeout=15)
                    if res.status_code == 200:
                        match = re.search(r'https?://[a-zA-Z0-9-]+\.pages\.dev/play/[^\s"\']+', res.text)
                        if match:
                            save_to_firebase(anime, s, e, match.group(0))
                            yield f"Ep {e}: ✅ Saved\n"
                            misses = 0
                        else:
                            yield f"Ep {e}: Link not found ❌\n"
                            misses += 1
                    else:
                        yield f"Ep {e}: Not available ❌\n"
                        misses += 1
                except Exception:
                    yield f"Ep {e}: Timeout ❌\n"
                    misses += 1
                if misses >= 3 and not e_num: break
        yield "<b>Process Completed!</b>"
    return Response(generate(), mimetype='text/html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
