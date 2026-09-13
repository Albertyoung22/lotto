# 台灣彩券 · 威力彩大數據視覺化儀表板與 Google OR-Tools AI 運籌預測系統

本專案提供**完整、視覺化且全自動**的方案，用於查詢、下載與統計台灣彩券「威力彩」（Super Lotto 6/38）歷史各期開獎獎號與派彩數據，並深度整合 **Google OR-Tools (運籌學 CP-SAT 求解器)** 提供具備嚴謹數學模型與多注多樣性包牌的智慧推薦。

支援 **Flask Web 雲端部署 (Render / Railway / GitHub)** 以及 **Windows 原生一體化桌面 GUI**。

---

## ☁️ 雲端平台部署指南 (GitHub + Render)

本系統已針對 **Render.com** 與 **GitHub** 完成生產級適配，支援 **1-Click 零配置部屬**！

### 步驟 1：建立並推送到您的 GitHub 儲存庫

在本地終端機（PowerShell 或 Bash）依序執行下列指令：

```bash
# 1. 切換至專案目錄
cd D:\PythonTest\Lotto

# 2. 初始化 Git 儲存庫 (若尚未初始化)
git init

# 3. 將所有檔案加入暫存區
git add .

# 4. 提交版本
git commit -m "feat: Taiwan Lottery Flask Web App with Google OR-Tools AI Optimizer"

# 5. 連接至您的 GitHub 遠端儲存庫
git remote add origin https://github.com/Albertyoung22/lotto.git

# 6. 推送至 GitHub 主分支
git branch -M main
git push -u origin main
```

---

### 步驟 2：在 Render (Render.com) 建立 Web 服務

1. 登入 [Render 官方網站](https://render.com/)，點選右上角 **「New +」** -> **「Web Service」**。
2. 選擇 **「Build and deploy from a Git repository」**，並連接剛才推送的 GitHub 專案。
3. 填寫服務設定（系統內建的 `render.yaml` 與 `Procfile` 會自動套用大部分設定）：
   - **Name**: `taiwan-lottery-ai`（自訂）
   - **Region**: `Singapore` 或 `Oregon`（建議選亞洲或美國皆可）
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn app:app
     ```
   - **Instance Type**: 選擇 **Free**（完全免費）。
4. （選填）進階環境變數 (Environment Variables)：
   - `PYTHON_VERSION`: `3.12.0`
5. 點擊 **「Create Web Service」**！
   - Render 會自動拉取程式碼、安裝 `ortools`、`flask`、`gunicorn` 並自動配置 SSL 網址（例如 `https://taiwan-lottery-ai.onrender.com`）。
   - 部署完成後，即可在手機、平板或電腦瀏覽器隨時隨地開啟使用！

---

## 💻 本機執行方式 (Local Development)

### 1. 🌐 網頁版 (Flask + Waitress WSGI)
- **特色**：暗黑金屬玻璃擬態（Glassmorphism）極致視覺美學、3D 漸層炫彩球、Google OR-Tools AI 智慧包牌、單注/全選複製、即時官方同步。
- **本機啟動**：
  ```bash
  # 安裝相依套件 (首次)
  pip install -r requirements.txt

  # 啟動生產級 Waitress / Flask 伺服器
  python app.py
  # 或者雙擊: 啟動網頁版UI.bat
  ```
  啟動後瀏覽器訪問：`http://127.0.0.1:5000`

---

### 2. 🖥️ 一體化原生桌面視窗版 (Tkinter Desktop GUI)
- **特色**：
  - 單一視窗（All-in-One）無彈窗整合設計。
  - 頂部 Showcase 3D 彩球即時連動。
  - 頁籤 1：🤖 Google OR-Tools AI 智慧運籌預測（自訂膽碼、殺號、和值、多注互斥）。
  - 頁籤 2：📋 282+ 期完整歷史開獎清單與即時搜尋。
  - 頁籤 3：📊 號碼開出頻率與遺漏值排行榜。
- **本機啟動**：
  ```bash
  python lotto_gui.py
  # 或者雙擊: 啟動桌面版GUI.bat
  ```

---

## 🤖 Google OR-Tools 運籌學 AI 最佳化原理

有別於不可解釋的黑箱神經網路，本系統將彩券選號問題定義為**運籌學約束滿足與組合最佳化問題 (Combinatorial Optimization & 0-1 Mixed Integer Programming)**：

### 1. 歷史特徵工程 (Feature Engineering)
- **時序衰減加權頻率 (Decay-Weighted Frequency)**：近期開出期數賦予較高時序趨勢權重。
- **遺漏值回補潛力 (Omission / Due Index)**：統計各球號距離上次開出的未出期數，捕捉適度冷熱回補週期。
- **雙號共現親和度矩陣 (Co-occurrence Affinity)**：計算歷史 282+ 期中常結伴同時開出的黃金雙號組合。
- **和值黃金常態分佈 (Sum Distribution)**：統計威力彩歷史開獎平均和值為 **117**，設定常態區間 **85 ~ 155**。
- **奇偶與大小比例平衡 (Parity & High/Low)**：奇偶比與大小比嚴格限制於 $2:4 \sim 4:2$ 常態平衡範圍內。

### 2. Google OR-Tools CP-SAT 0-1 整數規劃建模
- **決策變數**：$x_i \in \{0, 1\}$，代表第 $i$ 號是否選中（$i = 1, \dots, 38$）。
- **號碼數量約束**：$\sum_{i=1}^{38} x_i = 6$（第一區精確選出 6 顆球）。
- **連號防禦約束**：$\forall i, x_i + x_{i+1} + x_{i+2} \le 2$（連續 3 顆球開出機率極低，強制防禦過度密集連號）。
- **和值約束**：$85 \le \sum_{i=1}^{38} i \cdot x_i \le 155$。
- **多注多樣性互斥約束 (Portfolio Diversity / 包牌最大覆蓋率)**：
  求解多注時，限制新注單與已選注單的**重疊球數 $\le 3$ 顆**，防止號碼重複浪費投注成本，達到最大化的號碼覆蓋率。
- **目標函數**：$\max \sum_{i=1}^{38} w_i \cdot x_i$（最大化綜合潛力分數）。

---

## 📂 專案檔案架構

| 檔案路徑 | 說明 |
| :--- | :--- |
| `app.py` | **Flask 主應用程式**，支援 Waitress、Gunicorn 與 Render 部署 |
| `Procfile` | Render / Heroku 雲端啟動行程定義 (`web: gunicorn app:app`) |
| `render.yaml` | Render 雲端平台基礎設施藍圖設定 (Blueprint) |
| `requirements.txt` | Python 相依函式庫清單 (Flask, waitress, gunicorn, ortools) |
| `.gitignore` | Git 版本控制忽略清單 |
| `web/index.html` | 現代化極致玻璃擬態前端網頁 (含 3D 彩球與 AI 運籌面板) |
| `lotto_ai_optimizer.py` | Google OR-Tools CP-SAT 運籌整數規劃與啟發式備援核心 |
| `lotto_gui.py` | 一體化原生桌面視窗 GUI 程式 |
| `taiwan_lottery.py` | 台彩官方資料爬蟲、JSON/CSV 存取模組與 CLI 工具 |
| `super_lotto_history.csv` | 2024~至今全期開獎紀錄 (CSV 格式) |
| `super_lotto_history.json` | 2024~至今全期開獎紀錄 (JSON 格式) |
| `啟動網頁版UI.bat` | Windows 雙擊啟動 Flask / Waitress 網頁伺服器 |
| `啟動桌面版GUI.bat` | Windows 雙擊啟動原生桌面視窗程式 |
