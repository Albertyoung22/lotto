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
    fetch_lotto649_by_year,
    download_lotto649_range,
    save_to_csv,
    save_to_json
)
from lotto_ai_optimizer import (
    generate_predictions,
    check_ortools_status,
    run_historical_backtest,
    LottoCommitmentVerifier
)

SUPER_LOTTO_JSON = os.path.join(current_dir, "super_lotto_history.json")
SUPER_LOTTO_CSV = os.path.join(current_dir, "super_lotto_history.csv")
LOTTO649_JSON = os.path.join(current_dir, "lotto649_history.json")
LOTTO649_CSV = os.path.join(current_dir, "lotto649_history.csv")

# 相容別名
JSON_FILE = SUPER_LOTTO_JSON
CSV_FILE = SUPER_LOTTO_CSV

WEB_DIR = os.path.join(current_dir, "web")

GAME_FILE_MAP = {
    "super_lotto": ("super_lotto", os.path.join(current_dir, "super_lotto_history.json"), os.path.join(current_dir, "super_lotto_history.csv")),
    "lotto649":    ("lotto649",    os.path.join(current_dir, "lotto649_history.json"),    os.path.join(current_dir, "lotto649_history.csv")),
    "daily539":    ("daily539",    os.path.join(current_dir, "daily539_history.json"),    os.path.join(current_dir, "daily539_history.csv")),
    "lotto39m":    ("lotto39m",    os.path.join(current_dir, "lotto39m_history.json"),    os.path.join(current_dir, "lotto39m_history.csv")),
    "lotto49m":    ("lotto49m",    os.path.join(current_dir, "lotto49m_history.json"),    os.path.join(current_dir, "lotto49m_history.csv")),
    "3star":       ("3star",       os.path.join(current_dir, "3star_history.json"),       os.path.join(current_dir, "3star_history.csv")),
    "4star":       ("4star",       os.path.join(current_dir, "4star_history.json"),       os.path.join(current_dir, "4star_history.csv")),
    "bingo":       ("bingo",       os.path.join(current_dir, "bingo_history.json"),       os.path.join(current_dir, "bingo_history.csv")),
}

def get_game_files(game: str = "super_lotto"):
    """依遊戲類型取得正規化名稱、JSON 與 CSV 路徑"""
    g = (game or "super_lotto").lower()
    if g in ["lotto649", "649", "大樂透"]:
        return GAME_FILE_MAP["lotto649"]
    elif g in ["daily539", "539", "今彩539"]:
        return GAME_FILE_MAP["daily539"]
    elif g in ["lotto39m", "39m", "39樂合彩"]:
        return GAME_FILE_MAP["lotto39m"]
    elif g in ["lotto49m", "49m", "49樂合彩"]:
        return GAME_FILE_MAP["lotto49m"]
    elif g in ["3star", "3星彩"]:
        return GAME_FILE_MAP["3star"]
    elif g in ["4star", "4星彩"]:
        return GAME_FILE_MAP["4star"]
    elif g in ["bingo", "賓果賓果"]:
        return GAME_FILE_MAP["bingo"]
    return GAME_FILE_MAP["super_lotto"]

# 初始化 Flask 應用程式 (設定模板路徑指向 web 資料夾)
app = Flask(
    __name__,
    template_folder=WEB_DIR,
    static_folder=WEB_DIR,
    static_url_path=""
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

def ensure_data_exists(game: str = "super_lotto"):
    """若資料庫檔案尚不存在，則自動從台彩官方 API 抓取歷史獎號 (2024~至今)"""
    game_type, json_file, csv_file = get_game_files(game)
    if not os.path.exists(json_file) or os.path.getsize(json_file) == 0:
        cur_year = datetime.now().year
        print(f"[資訊] 本地無 {game_type} 歷史資料快取，開始從台彩官方抓取 2024 ~ 至今全期獎號...")
        from taiwan_lottery import download_game_range
        download_game_range(game_type, 2024, cur_year, csv_file)

# -------------------------------------------------------------
# 頁面路由 (Page Routes)
# -------------------------------------------------------------
@app.route("/")
@app.route("/index.html")
def index():
    """首頁：渲染極致玻璃擬態 (Glassmorphism) 現代視覺化儀表板"""
    ensure_data_exists("super_lotto")
    return render_template("index.html")

# -------------------------------------------------------------
# API 路由 (RESTful API Endpoints)
# -------------------------------------------------------------
@app.route("/api/lottery", methods=["GET"])
def get_lottery_records():
    """取得歷史全期開獎資料 JSON (支援 game=super_lotto 或 game=lotto649)"""
    game = request.args.get("game", "super_lotto")
    ensure_data_exists(game)
    game_type, json_file, _ = get_game_files(game)
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            return jsonify(records)
        except Exception as e:
            return jsonify({"error": f"讀取 {game_type} 歷史資料失敗: {str(e)}"}), 500
    return jsonify([])

@app.route("/api/sync", methods=["POST"])
def sync_latest_data():
    """即時連線台灣彩券官方伺服器，同步更新指定彩券之最新獎號"""
    try:
        body = request.get_json(silent=True) or {}
        game = request.args.get("game") or body.get("game", "super_lotto")
        game_type, json_file, csv_file = get_game_files(game)

        cur_year = datetime.now().year
        print(f"[同步] 正在連線台彩官方更新 {game_type} 至 {cur_year} 年...")
        from taiwan_lottery import download_game_range
        download_game_range(game_type, 2024, cur_year, csv_file)

        total_count = 0
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)
                total_count = len(records)

        GAME_NAME_MAP = {
            "super_lotto": "威力彩", "lotto649": "大樂透", "daily539": "今彩539",
            "lotto39m": "39樂合彩", "lotto49m": "49樂合彩", "3star": "3星彩",
            "4star": "4星彩", "bingo": "賓果賓果"
        }
        g_name = GAME_NAME_MAP.get(game_type, game_type)

        return jsonify({
            "status": "ok",
            "game": game_type,
            "message": f"{g_name} 同步完成",
            "count": total_count,
            "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/export/csv", methods=["GET"])
def export_csv_file():
    """匯出全期開獎紀錄 CSV 檔案 (UTF-8-SIG 編碼，繁中 Excel 不亂碼)"""
    game = request.args.get("game", "super_lotto")
    ensure_data_exists(game)
    game_type, _, csv_file = get_game_files(game)
    if not os.path.exists(csv_file):
        return jsonify({"error": "CSV 檔案尚未生成"}), 404
    
    file_prefix = game_type
    return send_file(
        csv_file,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{file_prefix}_{datetime.now().strftime('%Y%m%d')}.csv"
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
    支援自訂約束：注數 (count)、膽碼 (locked_z1)、殺號 (excluded_z1)、特別號 (locked_z2)、和值範圍 (sum_min, sum_max)、遊戲 (game)
    """
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        count = int(body.get("count", 5))
        constraints = body.get("constraints", {})
        game = body.get("game") or request.args.get("game", "super_lotto")
    else:
        count = request.args.get("count", 5, type=int)
        constraints = {}
        game = request.args.get("game", "super_lotto")

    ensure_data_exists(game)
    game_type, json_file, _ = get_game_files(game)

    result = generate_predictions(json_file, num_tickets=count, constraints=constraints, game_type=game_type)
    return jsonify(result)

@app.route("/api/ziwei_recommend", methods=["GET", "POST"])
def ziwei_recommend_api():
    """
    紫微斗數與八字五行 + CP-SAT 雙引擎彩券預測 API
    - 參數: birth_year, birth_month, birth_day, birth_hour, count, game
    - 回傳: 紫微命理氣場速報、五行喜用神、偏財吉數與 CP-SAT 融合包牌結果
    """
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        b_year = body.get("birth_year")
        b_month = body.get("birth_month")
        b_day = body.get("birth_day")
        b_hour = body.get("birth_hour", 12)
        count = int(body.get("count", 5))
        game = body.get("game") or request.args.get("game", "super_lotto")
    else:
        b_year = request.args.get("birth_year", type=int)
        b_month = request.args.get("birth_month", type=int)
        b_day = request.args.get("birth_day", type=int)
        b_hour = request.args.get("birth_hour", 12, type=int)
        count = request.args.get("count", 5, type=int)
        game = request.args.get("game", "super_lotto")

    ensure_data_exists(game)
    game_type, json_file, _ = get_game_files(game)

    import lotto_ziwei_engine
    fortune = lotto_ziwei_engine.calculate_ziwei_lotto_fortune(
        birth_year=b_year,
        birth_month=b_month,
        birth_day=b_day,
        birth_hour=b_hour,
        game_type=game_type
    )

    constraints = {
        "ziwei_boost_map": fortune["boost_weights_z1"],
        "ziwei_lucky_z1": fortune["lucky_numbers_z1"]
    }

    pred_res = generate_predictions(json_file, num_tickets=count, constraints=constraints, game_type=game_type)

    return jsonify({
        "status": "ok",
        "game": game_type,
        "fortune": fortune,
        "tickets": pred_res.get("recommendations", []),
        "engine": pred_res.get("engine", "CP-SAT + Ziwei Hybrid")
    })

@app.route("/api/ai/backtest", methods=["GET", "POST"])
def run_backtest_api():
    """
    執行無未來數據的嚴格歷史時序步進回測 (Walk-Forward Rolling Backtest)
    - 參數: draws (回測期數), tickets (每期注數), game (支援全彩種: super_lotto / lotto649 / daily539 / lotto39m / lotto49m / 3star / 4star / bingo)
    - 回傳: AI vs 隨機快選 (Random Baseline) 勝率倍數、命中球數、獎項分佈與詳細對照清單
    """
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        draws = int(body.get("draws", 20))
        tickets = int(body.get("tickets", 5))
        game = body.get("game") or request.args.get("game", "super_lotto")
    else:
        draws = request.args.get("draws", 20, type=int)
        tickets = request.args.get("tickets", 5, type=int)
        game = request.args.get("game", "super_lotto")

    ensure_data_exists(game)
    game_type, json_file, _ = get_game_files(game)

    draws = max(5, min(draws, 50))
    tickets = max(1, min(tickets, 10))

    result = run_historical_backtest(json_file, test_draws=draws, tickets_per_draw=tickets, game_type=game_type)
    return jsonify(result)

@app.route("/api/ai/verify_commitment", methods=["POST"])
def verify_commitment_api():
    """
    開獎後 SHA-256 密碼學存證驗證：
    接收使用者輸入的明文字串與開獎前發布的 SHA-256 雜湊，驗證是否一致絕無竄改。
    """
    body = request.get_json(silent=True) or {}
    canonical_payload = body.get("canonical_payload", "")
    expected_hash = body.get("expected_hash", "")

    if not canonical_payload or not expected_hash:
        return jsonify({"status": "error", "message": "缺少 canonical_payload 或 expected_hash 參數"}), 400

    res = LottoCommitmentVerifier.verify_commitment(canonical_payload, expected_hash)
    return jsonify({"status": "ok", "result": res})


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
