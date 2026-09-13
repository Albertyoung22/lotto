# -*- coding: utf-8 -*-
"""
台灣彩券 - 威力彩 Web 視覺化儀表板伺服器
========================================
支援以 Flask + Waitress / Gunicorn 高性能 WSGI 伺服器運行，
完美適配本機開發與雲端 Render / GitHub 部署。
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def run_server():
    port = int(os.environ.get("PORT", 5000))
    try:
        from app import app
        try:
            from waitress import serve
            print("=" * 65)
            print(f" 威力彩 Web 視覺化儀表板已啟動！(Waitress WSGI 生產級伺服器)")
            print(f" 本地訪問網址: http://127.0.0.1:{port}")
            print(f" (按 Ctrl + C 可停止伺服器)")
            print("=" * 65)
            serve(app, host="0.0.0.0", port=port, threads=6)
        except ImportError:
            print("=" * 65)
            print(f" 威力彩 Web 視覺化儀表板已啟動！(Flask 伺服器)")
            print(f" 本地訪問網址: http://127.0.0.1:{port}")
            print(f" (提示: 執行 pip install waitress 可啟用多線程生產級 WSGI)")
            print(f" (按 Ctrl + C 可停止伺服器)")
            print("=" * 65)
            app.run(host="0.0.0.0", port=port, debug=False)
    except ImportError:
        print("[警告] 尚未安裝 Flask，正在以 Python 內建 HTTP 伺服器啟動...")
        # 內建 http.server 備援
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        server_address = ("", port)
        httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
        print(f"本地訪問網址: http://127.0.0.1:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
