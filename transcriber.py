import os
import sys
import webbrowser
import threading
import uuid
import json
import logging
from flask import Flask, request, jsonify
from groq import Groq
import yt_dlp
from dotenv import load_dotenv  # <--- Добавили импорт

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
load_dotenv()  # <--- Загружаем данные из .env файла

# --- НАСТРОЙКИ ---
app = Flask(__name__)
UPLOAD_FOLDER = 'temp_downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ПОЛУЧАЕМ КЛЮЧ БЕЗОПАСНО
# Если ключа нет, скрипт выдаст ошибку, а не упадет молча
API_KEY = os.getenv("GROQ_API_KEY") 
if not API_KEY:
    raise ValueError("API Key not found! Check your .env file.")

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SKYFALL")

# --- HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FAN SONG // INTERCEPTOR</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #050505;
            --panel-bg: rgba(20, 20, 25, 0.95);
            --accent: #FFD800; /* Arknights Yellow */
            --cyan: #00F0FF;   /* Cyan */
            --text: #EAEAEA;
            --dim: #555;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text);
            font-family: 'Rajdhani', sans-serif;
            margin: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            background-image: radial-gradient(circle at center, #1a1a1a 0%, #000 100%);
        }

        /* ФОН (ПОЛНОСТЬЮ ОТКЛЮЧЕН ОТ КЛИКОВ) */
        #bg-canvas {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: 0;
            pointer-events: none;
        }

        /* ОСНОВНОЙ КОНТЕЙНЕР */
        .container {
            position: relative;
            z-index: 10;
            width: 550px;
            background: var(--panel-bg);
            padding: 40px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 0 60px rgba(0,0,0,0.8);
            /* Arknights Style Cut */
            clip-path: polygon(
                20px 0, 100% 0, 
                100% calc(100% - 20px), 
                calc(100% - 20px) 100%, 
                0 100%, 0 20px
            );
        }

        /* Желтая полоска сверху */
        .container::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px;
            background: var(--accent);
            box-shadow: 0 0 15px var(--accent);
        }

        h1 { margin: 0; font-size: 42px; text-transform: uppercase; color: #fff; letter-spacing: 2px; line-height: 1; }
        .sub { color: var(--accent); font-family: 'Share Tech Mono', monospace; font-size: 12px; margin-bottom: 30px; letter-spacing: 1px; }

        /* ЭЛЕМЕНТЫ УПРАВЛЕНИЯ */
        .tabs { display: flex; gap: 10px; margin-bottom: 25px; }
        .tab {
            flex: 1; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid #333;
            color: #777; cursor: pointer; text-align: center; font-family: 'Share Tech Mono', monospace;
            transition: 0.2s; font-size: 14px;
        }
        .tab:hover { border-color: #fff; color: #fff; }
        .tab.active { background: var(--accent); color: #000; font-weight: bold; border-color: var(--accent); box-shadow: 0 0 15px rgba(255, 216, 0, 0.2); }

        .input-wrapper { height: 60px; margin-bottom: 25px; }

        input[type="text"] {
            width: 100%; height: 100%; padding: 0 20px; background: rgba(0,0,0,0.5); border: 1px solid #444;
            color: var(--cyan); font-family: 'Share Tech Mono', monospace; font-size: 16px; outline: none; 
            transition: 0.3s;
        }
        input[type="text"]:focus { border-color: var(--cyan); box-shadow: 0 0 20px rgba(0, 240, 255, 0.15); }

        .file-zone {
            width: 100%; height: 100%; border: 1px dashed #555; display: flex; align-items: center; justify-content: center;
            color: #777; font-family: 'Share Tech Mono', monospace; cursor: pointer; transition: 0.3s;
            background: rgba(0,0,0,0.3);
        }
        .file-zone:hover { border-color: var(--cyan); color: var(--cyan); background: rgba(0, 240, 255, 0.05); }

        button {
            width: 100%; height: 70px; background: #EAEAEA; color: #000; border: none;
            font-family: 'Rajdhani', sans-serif; font-weight: 800; font-size: 24px;
            cursor: pointer; text-transform: uppercase; letter-spacing: 4px;
            transition: 0.2s;
            clip-path: polygon(0 0, 95% 0, 100% 25%, 100% 100%, 0 100%);
        }
        button:hover { background: var(--cyan); box-shadow: 0 0 30px rgba(0, 240, 255, 0.3); }
        button:disabled { background: #333; color: #555; cursor: not-allowed; box-shadow: none; }

        .footer {
            margin-top: 25px; text-align: center; font-family: 'Share Tech Mono', monospace; 
            font-size: 10px; color: #444; letter-spacing: 2px; text-transform: uppercase;
        }

        .status-msg {
            text-align: center; font-family: 'Share Tech Mono', monospace; font-size: 12px;
            color: var(--accent); margin-bottom: 10px; min-height: 15px; opacity: 0.8;
        }

        /* МОДАЛЬНОЕ ОКНО */
        #modal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); z-index: 100;
            justify-content: center; align-items: center;
            backdrop-filter: blur(5px);
        }
        .modal-content {
            width: 800px; max-width: 90%; height: 80%; background: #0a0a0a; border: 1px solid var(--cyan);
            display: flex; flex-direction: column; box-shadow: 0 0 50px rgba(0, 240, 255, 0.15);
        }
        .modal-header { 
            padding: 15px 25px; background: rgba(0, 240, 255, 0.05); border-bottom: 1px solid rgba(0, 240, 255, 0.2);
            display: flex; justify-content: space-between; align-items: center; color: var(--cyan); font-family: 'Share Tech Mono', monospace; 
        }
        .close-btn { cursor: pointer; color: #777; font-weight: bold; border: 1px solid transparent; padding: 2px 8px; transition: 0.2s; }
        .close-btn:hover { color: #fff; border-color: #fff; }
        
        #result-text {
            flex: 1; padding: 30px; overflow-y: auto; color: #ccc; font-family: 'Share Tech Mono', monospace; 
            white-space: pre-wrap; font-size: 14px; line-height: 1.6;
        }
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; background: #000; }
        ::-webkit-scrollbar-thumb { background: #333; }
        ::-webkit-scrollbar-thumb:hover { background: var(--cyan); }

    </style>
</head>
<body>
    <canvas id="bg-canvas"></canvas>

    <div class="container">
        <h1>Fan Song</h1>
        <div class="sub">AUDIO INTERCEPTOR // PROJECT: SKYFALL</div>

        <div class="tabs">
            <div id="tab-yt" class="tab active" onclick="switchMode('yt')">NETWORK (YT)</div>
            <div id="tab-file" class="tab" onclick="switchMode('file')">LOCAL DATA</div>
        </div>

        <div class="input-wrapper" id="input-yt">
            <input type="text" id="url" placeholder=">> INSERT TARGET URL HERE">
        </div>

        <div class="input-wrapper" id="input-file" style="display:none;">
            <div class="file-zone" onclick="document.getElementById('file').click()">
                <span id="filename">>> CLICK TO MOUNT DRIVE</span>
            </div>
            <input type="file" id="file" style="display:none" onchange="fileSelected()">
        </div>

        <div class="status-msg" id="status">[ SYSTEM ONLINE ]</div>

        <button id="btn" onclick="process()">INITIATE</button>
        
        <div class="footer">skyfall analytics // unauthorized access prohibited</div>
    </div>

    <div id="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span>>> DECRYPTION LOG</span>
                <span class="close-btn" onclick="closeModal()">[CLOSE TERMINAL]</span>
            </div>
            <div id="result-text">Initializing data stream...</div>
        </div>
    </div>

    <script>
        // --- PARTICLES ---
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');
        let width, height;
        let particles = [];

        function resize() { width = canvas.width = window.innerWidth; height = canvas.height = window.innerHeight; }
        window.addEventListener('resize', resize);
        resize();

        class Particle {
            constructor() { this.reset(); }
            reset() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.size = Math.random() * 2 + 1;
                this.speed = Math.random() * 0.5 + 0.1;
                this.opacity = Math.random() * 0.5;
            }
            update() {
                this.y -= this.speed;
                if(this.y < 0) this.reset();
            }
            draw() {
                ctx.fillStyle = `rgba(255, 255, 255, ${this.opacity})`;
                ctx.fillRect(this.x, this.y, this.size, this.size);
            }
        }
        for(let i=0; i<50; i++) particles.push(new Particle());
        function animate() {
            ctx.clearRect(0, 0, width, height);
            particles.forEach(p => { p.update(); p.draw(); });
            requestAnimationFrame(animate);
        }
        animate();

        // --- APP LOGIC ---
        let mode = 'yt';

        function switchMode(newMode) {
            mode = newMode;
            document.getElementById('tab-yt').className = mode === 'yt' ? 'tab active' : 'tab';
            document.getElementById('tab-file').className = mode === 'file' ? 'tab active' : 'tab';
            document.getElementById('input-yt').style.display = mode === 'yt' ? 'block' : 'none';
            document.getElementById('input-file').style.display = mode === 'file' ? 'block' : 'none';
        }

        function fileSelected() {
            const file = document.getElementById('file').files[0];
            if (file) {
                document.getElementById('filename').innerText = ">> MOUNTED: " + file.name;
                document.getElementById('filename').style.color = "var(--cyan)";
                document.getElementById('filename').style.fontWeight = "bold";
            }
        }

        function closeModal() {
            document.getElementById('modal').style.display = 'none';
            resetUI();
        }

        function resetUI() {
            const btn = document.getElementById('btn');
            btn.disabled = false;
            btn.innerText = "INITIATE";
            btn.style.background = "#EAEAEA";
            document.getElementById('status').innerText = "[ SYSTEM ONLINE ]";
            document.getElementById('status').style.color = "var(--accent)";
        }

        async function process() {
            const btn = document.getElementById('btn');
            const status = document.getElementById('status');
            
            // 1. Сбор данных
            const formData = new FormData();
            
            if (mode === 'yt') {
                const url = document.getElementById('url').value;
                if (!url) { status.innerText = ">> ERROR: URL REQUIRED"; status.style.color = "#ff4444"; return; }
                formData.append('yt_url', url);
            } else {
                const file = document.getElementById('file').files[0];
                if (!file) { status.innerText = ">> ERROR: FILE REQUIRED"; status.style.color = "#ff4444"; return; }
                formData.append('file', file);
            }

            // 2. Блокировка интерфейса
            btn.disabled = true;
            btn.innerText = "PROCESSING...";
            btn.style.background = "#333";
            status.innerText = "[ ESTABLISHING CONNECTION... ]";

            try {
                const response = await fetch('/api/transcribe', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();

                // 4. Результат
                document.getElementById('modal').style.display = 'flex';
                const output = document.getElementById('result-text');
                
                if (data.error) {
                    // Используем экранированный перенос строки, чтобы не сломать JS
                    output.innerText = "SYSTEM FAILURE:\\n" + data.error;
                    output.style.color = "#ff4444";
                } else {
                    output.innerText = data.text;
                    output.style.color = "#ccc";
                }

            } catch (e) {
                alert("CRITICAL ERROR: " + e);
                resetUI();
            }
        }
    </script>
</body>
</html>
"""

# --- БЭКЕНД ЛОГИКА ---
def get_transcription(client, filepath):
    filename = os.path.basename(filepath)
    try:
        logger.info(f"V3 Transcribe: {filename}")
        with open(filepath, "rb") as file:
            return client.audio.transcriptions.create(
                file=(filename, file.read()),
                model="whisper-large-v3",
                temperature=0,
                response_format="verbose_json",
            ).text
    except Exception as e:
        logger.warning(f"V3 Error: {e}. Switching to Turbo...")
        try:
            with open(filepath, "rb") as file:
                return client.audio.transcriptions.create(
                    file=(filename, file.read()),
                    model="whisper-large-v3-turbo",
                    temperature=0,
                    response_format="verbose_json",
                ).text
        except Exception as e2:
            raise Exception(f"All models failed. Last error: {e2}")

def download_yt(url):
    logger.info(f"Downloading: {url}")
    filename = str(uuid.uuid4())
    # Настройки для обхода блокировок
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(UPLOAD_FOLDER, f'{filename}.%(ext)s'),
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'm4a'}],
        'quiet': True,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return os.path.join(UPLOAD_FOLDER, f"{filename}.m4a")

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    client = Groq(api_key=API_KEY)
    target_path = None
    try:
        if 'yt_url' in request.form:
            target_path = download_yt(request.form['yt_url'])
        elif 'file' in request.files:
            f = request.files['file']
            target_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{f.filename}")
            f.save(target_path)
        else:
            return jsonify({'error': 'No input'}), 400

        text = get_transcription(client, target_path)
        
        if os.path.exists(target_path): os.remove(target_path)
        return jsonify({'text': text})

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    threading.Timer(1.5, open_browser).start()
    print("ЗАПУСК СЕРВЕРА...")
    app.run(port=5000, debug=False)