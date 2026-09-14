# 如何使用免費伺服器架設威力彩系統 (Render + GitHub Pages)

本指南說明如何參考現代化雲端免費託管架構（**Render 後端 + GitHub Pages 前端**），將「台灣彩券 · 威力彩 AI 運籌系統」進行零成本部署。

---

## 🏗️ 架構總覽

* **後端 API (Python / Flask)**：部署至 **Render (Free Web Service)**
  * 提供歷史開獎查詢 (`/api/lottery`)
  * 提供即時台彩官網同步 (`/api/sync`)
  * 提供 CP-SAT 運籌學求解 (`/api/ai/predict`)
  * 提供健康檢查與打卡探針 (`/health`)
* **前端介面 (HTML / CSS / JS)**：部署至 **GitHub Pages (Free Static Host)**
  * 極速載入網頁介面，不消耗 Render 資源。
  * 支援跨網域 API 呼叫 (CORS)。

---

## 第一步：準備 GitHub 儲存庫 (Repository)

1. 在 GitHub 上建立一個新的專案庫（例如 `taiwan-lottery-ai`）。
2. 將此專案的所有檔案上傳或 Push 至 GitHub 儲存庫：
   - `app.py`
   - `taiwan_lottery.py`
   - `lotto_ai_optimizer.py`
   - `requirements.txt`
   - `Procfile`
   - `render.yaml`
   - `web/index.html`

---

## 第二步：部署 Python 後端至 Render (Free Web Service)

1. 註冊並登入 [Render.com](https://render.com)。
2. 點擊 **New +** -> **Web Service**。
3. 連接您的 GitHub 帳號，選擇剛剛建立的 `taiwan-lottery-ai` 專案庫。
4. 設定參數：
   * **Name**: `taiwan-lottery-api` (可自訂)
   * **Region**: `Singapore` (新加坡，連線台灣最快)
   * **Branch**: `main`
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app`
   * **Instance Type**: `Free`
5. 點擊 **Create Web Service**，等待 2~3 分鐘構建完成。
6. 部署成功後複製您的 Render 網址，例如：`https://taiwan-lottery-api.onrender.com`

---

## 第三步：設定防休眠 (Prevent Render Sleep)

Render 免費版在無人存取 15 分鐘後會自動進入休眠（Cold Start 需要 30 秒喚醒）。

**解決方案（自動保活）**：
1. 前往免費的 [UptimeRobot.com](https://uptimerobot.com) 註冊帳號。
2. 點擊 **Add New Monitor**：
   * **Monitor Type**: `HTTP(s)`
   * **Friendly Name**: `Lotto-Render-KeepAlive`
   * **URL**: `https://taiwan-lottery-api.onrender.com/health`
   * **Monitoring Interval**: 設為 **5 分鐘** 或 **10 分鐘**。
3. 保存後，UptimeRobot 會每 5 分鐘自動打卡 `/health` 端點，Render 就**永遠不會休眠**！

---

## 第四步：部署前端網頁至 GitHub Pages

1. 進入專案的 GitHub 儲存庫。
2. 進入 **Settings** -> **Pages**。
3. **Source** 選擇 `Deploy from a branch`。
4. **Branch** 選擇 `main` / `/web` 資料夾（或專案根目錄）。
5. 點擊 Save，約 1 分鐘後即可獲得前端靜態網站網址：
   * 例如 `https://your-github-username.github.io/taiwan-lottery-ai/`

---

## ⚡ 恭喜完成！

現在您的威力彩 AI 系統已經同時擁有：
1. **GitHub Pages** 提供秒開的視覺化網頁介面。
2. **Render** 提供穩定的 Python 後端 API 與 OR-Tools AI 求解運算。
3. **UptimeRobot** 保障 Render 後端 24 小時全天候熱啟動不休眠！
