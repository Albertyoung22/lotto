# -*- coding: utf-8 -*-
"""
台灣彩券 · 威力彩 Web 視覺化儀表板與 AI 運籌預測服務 (Flask + Waitress / Gunicorn)
========================================================================================
支援本機運行與雲端平台 (Render, Railway, Fly.io, Heroku) 部署：
- 雲端 (Render / Linux): 自動由 Gunicorn 啟動 (gunicorn app:app)
- 本機 (Windows / Mac): 支援 Waitress 生產級 WSGI 伺服器或 Flask 開發伺服器
- 自動監聽環境變數 PORT ($PORT)，完美相容 Render 容器化部署
"""

import sys
import os
import json
import csv
from datetime import datetime

# 將當前目錄加入模組搜尋路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask, render_template, request, jsonify, send_file
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

# 導入爬蟲與 AI 運籌核心模組
from taiwan_lottery import (
    fetch_super_lotto_by_year,
    download_super_lotto_range,
    save_to_csv,
    save_to_json
)
from lotto_ai_optimizer import (
    generate_predictions,
    check_ortools_status
)

JSON_FILE = os.path.join(current_dir, "super_lotto_history.json")
CSV_FILE = os.path.join(current_dir, "super_lotto_history.csv")
WEB_DIR = os.path.join(current_dir, "web")

# 初始化 Flask 應用程式 (設定模板路徑指向 web 資料夾)
app = Flask(
    __name__,
    template_folder=WEB_DIR,
    static_folder=os.path.join(WEB_DIR, "static")
)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

if HAS_CORS:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response



def ensure_data_exists():
    """若資料庫檔案尚不存在，則自動從台彩官方 API 抓取歷史獎號 (2024~至今)"""
    if not os.path.exists(JSON_FILE) or os.path.getsize(JSON_FILE) == 0:
        print("[資訊] 本地無歷史資料快取，開始從台彩官方抓取 2024 ~ 至今全期獎號...")
        cur_year = datetime.now().year
        download_super_lotto_range(2024, cur_year, CSV_FILE)

# -------------------------------------------------------------
# 頁面路由 (Page Routes)
# -------------------------------------------------------------
@app.route("/")
@app.route("/index.html")
def index():
    """首頁：渲染極致玻璃擬態 (Glassmorphism) 現代視覺化儀表板"""
    ensure_data_exists()
    return render_template("index.html")

# -------------------------------------------------------------
# API 路由 (RESTful API Endpoints)
# -------------------------------------------------------------
@app.route("/api/lottery", methods=["GET"])
def get_lottery_records():
    """取得歷史全期開獎資料 JSON"""
    ensure_data_exists()
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
            return jsonify(records)
        except Exception as e:
            return jsonify({"error": f"讀取歷史資料失敗: {str(e)}"}), 500
    return jsonify([])

@app.route("/api/sync", methods=["POST"])
def sync_latest_data():
    """即時連線台灣彩券官方伺服器，同步更新最新期別獎號"""
    try:
        cur_year = datetime.now().year
        print(f"[同步] 正在連線台彩官方更新至 {cur_year} 年...")
        download_super_lotto_range(2024, cur_year, CSV_FILE)

        total_count = 0
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
                total_count = len(records)

        return jsonify({
            "status": "ok",
            "message": "同步完成",
            "count": total_count,
            "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/export/csv", methods=["GET"])
def export_csv_file():
    """匯出全期威力彩開獎紀錄 CSV 檔案 (UTF-8-SIG 編碼，繁中 Excel 不亂碼)"""
    ensure_data_exists()
    if not os.path.exists(CSV_FILE):
        return jsonify({"error": "CSV 檔案尚未生成"}), 404
    return send_file(
        CSV_FILE,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"super_lotto_{datetime.now().strftime('%Y%m%d')}.csv"
    )

@app.route("/api/ai/status", methods=["GET"])
def get_ai_engine_status():
    """查詢當前環境 AI 運籌求解器安裝狀態"""
    status = check_ortools_status()
    return jsonify(status)

@app.route("/api/ai/predict", methods=["GET", "POST"])
def predict_tickets():
    """
    執行 AI 運籌學最佳化求解：
    支援自訂約束：注數 (count)、膽碼 (locked_z1)、殺號 (excluded_z1)、特別號 (locked_z2)、和值範圍 (sum_min, sum_max)、多樣性包牌
    """
    ensure_data_exists()
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        count = int(body.get("count", 5))
        constraints = body.get("constraints", {})
    else:
        count = request.args.get("count", 5, type=int)
        constraints = {}

    result = generate_predictions(JSON_FILE, num_tickets=count, constraints=constraints)
    return jsonify(result)

@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """供 Render 雲端平台 Health Check 使用的探針端點"""
    return jsonify({
        "status": "healthy",
        "service": "taiwan-lottery-super-ai",
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# -------------------------------------------------------------
# Render 自動保活 / 防休眠內部線程 (Self Keep-Alive Thread)
# -------------------------------------------------------------
import threading
import time

def start_keep_alive_thread():
    """在背景啟動防休眠 Ping 線程，維護 Render 雲端熱啟動 (每 10 分鐘自動打卡)"""
    def _ping_loop():
        time.sleep(20)  # 等待伺服器啟動完成
        render_url = os.environ.get("RENDER_EXTERNAL_URL") or "https://taiwan-lottery-api.onrender.com"
        target_url = f"{render_url.rstrip('/')}/health"
        print(f"[*] 防休眠打卡機制已啟動，每 10 分鐘自動存取: {target_url}")

        import urllib.request
        while True:
            try:
                req = urllib.request.Request(target_url, headers={"User-Agent": "RenderKeepAlive/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Render 防休眠打卡成功 (HTTP {resp.status})")
            except Exception as e:
                print(f"[保活機制] 定時 Ping 提示: {e}")
            
            # 每 10 分鐘 (600 秒) 自動 Ping 一次
            time.sleep(600)

    t = threading.Thread(target=_ping_loop, daemon=True)
    t.start()

# 啟動防休眠背景線程
start_keep_alive_thread()


# -------------------------------------------------------------
# 啟動伺服器 (本機 Waitress / 開發伺服器)
# -------------------------------------------------------------
if __name__ == "__main__":
    ensure_data_exists()

    port = int(os.environ.get("PORT", 5000))

    import socket
    def get_real_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    real_ip = get_real_local_ip()

    print("=" * 65)
    print(" 台灣彩券 · 威力彩 Flask Web 視覺化伺服器已就緒")
    print(f" 監聽位址: http://0.0.0.0:{port}")
    print(f" 本地存取: http://127.0.0.1:{port}")
    print(f" 區網真實 IP 存取: http://{real_ip}:{port}")
    print("=" * 65)


    # 優先嘗試以 Waitress 高性能 WSGI 伺服器啟動 (生產級標準)
    try:
        from waitress import serve
        print(f"[*] 啟用 Waitress 高效能 WSGI 伺服器 (Production Mode)...")
        serve(app, host="0.0.0.0", port=port, threads=6)
    except ImportError:
        print("[*] 提示: 安裝 waitress 可獲得更高併發效能 (pip install waitress)")
        print(f"[*] 以 Flask 內建伺服器啟動...")
        app.run(host="0.0.0.0", port=port, debug=False)
