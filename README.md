# 台灣彩券 · 雙旗艦彩種大數據視覺化儀表板與 AI 運籌預測系統
### 🎱 威力彩 (Super Lotto 6/38) ＆ 💎 大樂透 (Lotto 6/49)

本專案提供**完整、視覺化且全自動**的方案，用於查詢、即時下載與深度統計台灣彩券兩大旗艦彩種——「**威力彩 (6/38)**」與「**大樂透 (6/49)**」歷史各期開獎獎號與派彩數據，並深度整合 **運籌學 CP-SAT 求解器 (Operations Research)** 提供具備嚴謹數學模型與多注多樣性包牌的智慧推薦。

系統原生支援 **雙彩種一鍵無縫切換**、**Flask Web 雲端部署 (Render / Railway / GitHub)** 以及 **Windows 原生一體化桌面 GUI**。

---

## 🌟 雙旗艦彩種支援特色 (Dual-Game Architecture)

| 彩種名稱 | 規則架構 | 號碼池 | 特別號/第二區 | 和值常態區間 | 開獎日與時間 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **🎱 威力彩** | 6/38 + 1/8 | 1 ~ 38 (選 6 顆) | 1 ~ 8 (獨立第二區選 1 顆) | 85 ~ 155 (平均約 117) | 每週一、週四 20:30 |
| **💎 大樂透** | 6/49 + 1/49 | 1 ~ 49 (選 6 顆) | 1 ~ 49 (不重複特別號選 1 顆) | 115 ~ 185 (平均約 150) | 每週二、週五 20:30 |

- **自動化數據同步**：支援官方 API 即時抓取最新期別，並提供 CSV/JSON 自動落盤與 Excel 相容 (UTF-8-SIG) 匯出。
- **自適應 8 階派彩判定**：精確模擬大樂透官方八大獎項（頭獎 6+0、貳獎 5+1、參獎 5+0、肆獎 4+1、伍獎 4+0、陸獎 3+1、柒獎 2+1、普獎 3+0）與威力彩中獎門檻。
- **無縫 UI 切換**：無論在網頁端或桌面 GUI，皆可隨時於頂部切換彩種，歷史數據、特徵工程、求解約束、回測與存證即時同步變更。

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
git commit -m "feat: Taiwan Lottery Flask Web App with Dual-Game AI Optimizer"

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
- **特色**：
  - 雙彩種切換分頁（威力彩 6/38 / 大樂透 6/49）。
  - 暗黑金屬玻璃擬態（Glassmorphism）極致視覺美學、3D 漸層炫彩球。
  - AI 運籌智慧包牌、單注/全選複製、即時官方同步。
  - 權威神準驗證實驗室：開獎前 SHA-256 存證 + 無未來數據滾動回測。
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
  - 頂部精選 Showcase 3D 彩球即時連動，頂部快速切換彩種。
  - 頁籤 1：🤖 AI 智慧運籌預測（自訂膽碼、殺號、特別號、和值、多注互斥）。
  - 頁籤 2：📋 數百期完整歷史開獎清單與即時搜尋。
  - 頁籤 3：📊 號碼開出頻率與遺漏值排行榜（1~38 或 1~49 自由縮放切換）。
- **本機啟動**：
  ```bash
  python lotto_gui.py
  # 或者雙擊: 啟動桌面版GUI.bat
  ```

---

## 🤖 運籌學 AI 最佳化原理 (CP-SAT Mathematical Formulation)

有別於不可解釋的黑箱神經網路，本系統將彩券選號問題定義為**運籌學約束滿足與組合最佳化問題 (Combinatorial Optimization & 0-1 Mixed Integer Programming)**：

### 1. 歷史特徵工程 (Feature Engineering)
- **時序衰減加權頻率 (Decay-Weighted Frequency)**：近期開出期數賦予較高時序趨勢權重。
- **遺漏值回補潛力 (Omission / Due Index)**：統計各球號距離上次開出的未出期數，捕捉適度冷熱回補週期。
- **雙號共現親和度矩陣 (Co-occurrence Affinity)**：計算歷史各期中常結伴同時開出的黃金雙號組合。
- **和值黃金常態分佈 (Sum Distribution)**：
  - 威力彩：常態分佈約 **85 ~ 155**（平均 117）。
  - 大樂透：常態分佈約 **115 ~ 185**（平均 150）。
- **奇偶與大小比例平衡 (Parity & High/Low)**：奇偶比與大小比嚴格限制於 $2:4 \sim 4:2$ 常態平衡範圍內。

### 2. CP-SAT 0-1 整數規劃建模
- **決策變數**：$x_i \in \{0, 1\}$，代表第 $i$ 號是否選中（威力彩 $i = 1, \dots, 38$；大樂透 $i = 1, \dots, 49$）。
- **號碼數量約束**：$\sum_{i} x_i = 6$（精確選出 6 顆正碼球）。
- **特別號互斥約束 (大樂透)**：若特別號為 $S$，則 $x_S = 0$（正碼與特別號不重複）。
- **連號防禦約束**：$\forall i, x_i + x_{i+1} + x_{i+2} \le 2$（連續 3 顆球開出機率極低，強制防禦過度密集連號）。
- **和值約束**：$\text{SumMin} \le \sum_{i} i \cdot x_i \le \text{SumMax}$。
- **多注多樣性互斥約束 (Portfolio Diversity / 包牌最大覆蓋率)**：
  求解多注時，限制新注單與已選注單的**重疊球數 $\le 3$ 顆**，防止號碼重複浪費投注成本，達到最大化的號碼覆蓋率。
- **目標函數**：$\max \sum_{i} w_i \cdot x_i$（最大化綜合潛力分數）。

---

## 🛡️ 權威科學驗證與回測實驗室 (Scientific Verification & Backtesting)

為徹底摒棄「事後諸葛」與「倖存者偏差」的質疑，本系統獨家整合了**量化金融與密碼學界公認的雙重客觀檢驗機制**：

### 1. 📈 嚴格無未來數據的步進式回測 (Walk-Forward Rolling Backtesting)
- **零時序洩漏 (No Lookahead Bias)**：模擬回到過去各期開獎點，回測第 $K$ 期時**嚴格只使用第 $1 \sim K-1$ 期的數據**進行特徵計算與求解，完全杜絕「偷看答案」的作弊可能。
- **A/B 雙軌對照基準 (Random Baseline)**：每期同步生成純電腦隨機快選注單作為基準線，以客觀統計檢驗 AI 運籌組相對於隨機快選的**勝率倍率 (Alpha Multiplier)** 與期望命中球數。
- **透明檢驗對照表**：自動生成過去 15 ~ 50 期的逐期詳細戰報，包含真實落球、AI 命中球數、獎項判定與隨機對照，數據公開可信。

### 2. 🔐 開獎前 SHA-256 密碼學時間戳存證 (Cryptographic Proof of Commitment)
- **開獎前鎖定 (Pre-Commitment)**：在開獎前數小時（18:00 前），系統將推薦注單、隨機防爆破鹽值 (Salt) 與時間戳透過 SHA-256 密碼學單向雜湊函數計算出 64 位的數位指紋 (Hash Token)。
- **不可逆與防事後改號**：開獎前公開 Hash 碼，任何人皆無法事後修改哪怕任何一顆球的號碼；開獎後公佈明文，任何人皆可在第三方工具（如 Google SHA-256 計算器）即時驗證吻合度，**徹底粉碎「事後選號、吹噓」的疑慮**！

---

## 📡 RESTful API 端點規範

所有 API 端點皆統一支援 `game=super_lotto`（預設）或 `game=lotto649` 參數：

| 端點 (Method & Path) | 參數說明 | 功能說明 |
| :--- | :--- | :--- |
| `GET /api/lottery?game=...` | `game`: `super_lotto` \| `lotto649` | 取得指定彩種全期開獎與派彩歷史紀錄 JSON |
| `POST /api/sync` | Body 或 Query: `{ "game": "..." }` | 即時連線台彩官方伺服器抓取最新期別並更新本機檔案 |
| `GET /api/export/csv?game=...` | `game`: `super_lotto` \| `lotto649` | 匯出繁體中文 Excel 相容 (UTF-8-SIG) 之歷史紀錄 CSV |
| `GET /api/ai/status` | 無 | 查詢後端 Google OR-Tools CP-SAT 求解器之安裝就緒狀態 |
| `POST /api/ai/predict` | JSON: `{ count, game, constraints: { locked_z1, excluded_z1, locked_z2, sum_min, sum_max, diversity } }` | 執行 CP-SAT 運籌求解，回傳推薦注單、評分與當期 SHA-256 存證雜湊 |
| `GET/POST /api/ai/backtest` | `game`, `draws` (回測期數), `tickets` (每期注數) | 執行嚴格步進無未來數據滾動回測，回傳 AI vs 隨機倍率與逐期對照 |
| `POST /api/ai/verify_commitment` | JSON: `{ canonical_payload, expected_hash }` | 驗證開獎後公佈之預測明文與開獎前公開之雜湊碼是否吻合 |

---

## 📂 專案檔案架構

| 檔案路徑 | 說明 |
| :--- | :--- |
| `app.py` | **Flask 主應用程式**，支援雙彩種 API、Waitress、Gunicorn 與 Render 雲端部署 |
| `Procfile` | Render / Heroku 雲端啟動行程定義 (`web: gunicorn app:app`) |
| `render.yaml` | Render 雲端平台基礎設施藍圖設定 (Blueprint) |
| `requirements.txt` | Python 相依函式庫清單 (Flask, waitress, gunicorn, ortools) |
| `.gitignore` | Git 版本控制忽略清單 |
| `web/index.html` | 雙彩種玻璃擬態前端網頁 (含 3D 彩球、AI 運籌與密碼學驗證實驗室) |
| `lotto_ai_optimizer.py` | CP-SAT 運籌整數規劃、大樂透/威力彩雙模組、回測引擎與 SHA-256 存證模組 |
| `lotto_gui.py` | 雙彩種一體化原生桌面視窗 GUI 程式 |
| `taiwan_lottery.py` | 台彩官方資料爬蟲模組（支援威力彩與大樂透官方 API 下載） |
| `super_lotto_history.csv` | 威力彩 2024~至今全期開獎紀錄 (CSV 格式) |
| `super_lotto_history.json` | 威力彩 2024~至今全期開獎紀錄 (JSON 格式) |
| `lotto649_history.csv` | 大樂透 2024~至今全期開獎紀錄 (CSV 格式) |
| `lotto649_history.json` | 大樂透 2024~至今全期開獎紀錄 (JSON 格式) |
| `啟動網頁版UI.bat` | Windows 雙擊啟動 Flask / Waitress 網頁伺服器 |
| `啟動桌面版GUI.bat` | Windows 雙擊啟動原生桌面視窗程式 |
