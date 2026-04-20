import pyrebase
from flask import Flask, render_template_string, request, Response, stream_with_context
import cloudscraper
import re
import time
import threading
import os

app = Flask(__name__)

# Cloudscraper setup
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

# --- 1. FIREBASE SETUP ---
config = {
    "apiKey": "AIzaSyAe5XKQlowY_AroKkQ80SeAYPqLnF02KoE",
    "authDomain": "animeverse-9eada.firebaseapp.com",
    "databaseURL": "https://animeverse-9eada-default-rtdb.firebaseio.com/",
    "storageBucket": "animeverse-9eada.appspot.com"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()

monitor_logs = {}

# --- 2. FIREBASE HELPER ---
def save_to_firebase(anime, s, e, link):
    try:
        db.child("animeverse_links").child(anime).child(f"S{s}").child(f"E{e}").set({
            "url": link,
            "bot": "#",
            "time": time.time()
        })
        today = time.strftime('%Y-%m-%d')
        db.child("added_today").child(today).child(anime).set({
            "id": anime, "s": s, "e": e, "timestamp": time.time()
        })
        return True
    except Exception:
        return False

# --- 3. MONITOR TASK ---
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
                    monitor_logs[task_id] += f"[{t}] ✅ SUCCESS: Added to Firebase!\n"
                    break 
            monitor_logs[task_id] += f"[{t}] Checking... Not found. (Waiting 5m)\n"
            time.sleep(300)
        except Exception:
            time.sleep(60)

# --- 4. HTML TEMPLATE ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AnimeVerse Admin V15</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --accent: #ff7b00; --bg: #0b1118; --card: #1a2430; --monitor: #ff4757; }
        body { font-family: sans-serif; background: var(--bg); color: white; padding: 10px; }
        .container { max-width: 500px; margin: auto; }
        .tabs { display: flex; gap: 5px; margin-bottom: 10px; border-bottom: 1px solid #334155; }
        .tab-btn { padding: 10px; background: #1a2430; border: none; color: #94a3b8; cursor: pointer; border-radius: 5px 5px 0 0; flex: 1; font-size: 12px; }
        .tab-btn.active { background: var(--accent); color: black; font-weight: bold; }
        .section { display: none; background: var(--card); padding: 15px; border-radius: 0 0 10px 10px; }
        .section.active { display: block; }
        input { width: 100%; padding: 12px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #334155; background: #0d1621; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; border: none; border-radius: 5px; color: white; font-weight: bold; cursor: pointer; }
        #status { background: black; padding: 15px; border-radius: 10px; height: 250px; overflow-y: auto; margin-top: 15px; font-family: monospace; font-size: 11px; white-space: pre-wrap; border: 1px solid #334155; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align:center; color: var(--accent);">ANIMEVERSE ADMIN</h2>
        <div class="tabs">
            <button class="tab-btn active" onclick="openTab(event, 'bulk')">All Seasons</button>
            <button class="tab-btn" onclick="openTab(event, 'season')">Season</button>
            <button class="tab-btn" onclick="openTab(event, 'episode')">Episode</button>
            <button class="tab-btn" onclick="openTab(event, 'monitor_tab')">Monitor</button>
        </div>

        <div id="bulk" class="section active">
            <input type="text" id="slug_bulk" placeholder="Anime Slug (e.g. naruto)">
            <button style="background: var(--accent);" onclick="start('bulk')">FETCH ALL SEASONS</button>
        </div>

        <div id="season" class="section">
            <input type="text" id="slug_season" placeholder="Anime Slug">
            <input type="number" id="num_season" placeholder="Season Number">
            <button style="background: #ff9f43;" onclick="start('season')">FETCH SEASON</button>
        </div>

        <div id="episode" class="section">
            <input type="text" id="slug_ep" placeholder="Anime Slug">
            <input type="number" id="s_ep" placeholder="Season">
            <input type="number" id="e_ep" placeholder="Episode">
            <button style="background: #a29bfe;" onclick="start('ep')">FETCH EPISODE</button>
        </div>

        <div id="monitor_tab" class="section">
            <input type="text" id="slug_m" placeholder="Anime Slug">
            <input type="number" id="s_m" placeholder="Season">
            <input type="number" id="e_m" placeholder="Episode">
            <button style="background: var(--monitor);" onclick="start('monitor')">START MONITOR</button>
        </div>

        <div id="status">System Ready...</div>
    </div>

    <script>
        function openTab(evt, name) {
            let s = document.getElementsByClassName("section");
            for (let i = 0; i < s.length; i++) s[i].classList.remove("active");
            let t = document.getElementsByClassName("tab-btn");
            for (let i = 0; i < t.length; i++) t[i].classList.remove("active");
            document.getElementById(name).classList.add("active");
            evt.currentTarget.classList.add("active");
        }

        async function start(mode) {
            const status = document.getElementById('status');
            let url = "";
            if(mode === 'bulk') url = `/fetch?anime=${document.getElementById('slug_bulk').value}`;
            else if(mode === 'season') url = `/fetch?anime=${document.getElementById('slug_season').value}&season=${document.getElementById('num_season').value}`;
            else if(mode === 'ep') url = `/fetch?anime=${document.getElementById('slug_ep').value}&season=${document.getElementById('s_ep').value}&ep=${document.getElementById('e_ep').value}`;
            else if(mode === 'monitor') url = `/monitor?anime=${document.getElementById('slug_m').value}&season=${document.getElementById('s_m').value}&ep=${document.getElementById('e_m').value}`;

            status.innerHTML = ">>> Connecting...\\n";
            const response = await fetch(url);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                status.innerHTML += decoder.decode(value);
                status.scrollTop = status.scrollHeight;
            }
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
    s, e = request.args.get('season'), request.args.get('ep')
    task_id = f"{anime}-{s}-{e}"
    threading.Thread(target=monitor_thread_task, args=(anime, s, e), daemon=True).start()
    
    @stream_with_context
    def generate():
        yield f"🚀 Monitor Task Added: {anime} S{s}E{e}\n"
        last_log_len = 0
        while task_id in monitor_logs:
            current_logs = monitor_logs[task_id]
            if len(current_logs) > last_log_len:
                yield current_logs[last_log_len:]
                last_log_len = len(current_logs)
                if "✅" in current_logs: break
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
            yield f"--- Season {s} ---\n"
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
                            yield f"Ep {e}: Not Found ❌\n"
                            misses += 1
                    else:
                        yield f"Ep {e}: 404 ❌\n"
                        misses += 1
                except Exception:
                    yield f"Ep {e}: Timeout ❌\n"
                    misses += 1
                if misses >= 3 and not e_num: break
        yield "🏁 Done!"
    return Response(generate(), mimetype='text/html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port).0', port=port)
