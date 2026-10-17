# 電路解題

適合手機與 iPad 的電路學、電子學練習。每一輪先看學習目標和公式，再一次答一題。送出之後才看得到正解、逐步解題、公式代入、單位檢查和常見錯誤；看完解析才能進入下一題。結束時會列出答對題數，也可以只重做錯題。

進度放在這次瀏覽的 Streamlit session state。重新整理頁面會清掉尚未結束的那一輪。

每一輪的題目是當場產生的。選 5 題就會得到 5 題。每個學習概念至少有五種思考方式：正向計算、反向求解、比較電路、找解題錯誤、預測條件改變。適合的概念另外有故障判斷。桌燈、熱水壺、手電筒、USB、玩具車等情境使用各自的電路模型；LED、馬達、充電器不會被直接當成一般電阻。同一題型仍可抽一組符合範圍的數字，答案與解析來自該題型自己的公式。

## 教材怎麼用

題目、電路圖和解析都是原創的，用來練習下面兩份教材裡的觀念，不複製教材段落、習題或圖片。

1. All About Circuits，《Lessons in Electric Circuits》  
   https://www.allaboutcircuits.com/textbook/
2. 陽明交通大學 OCW，「電路學概論」，112 學年度，電機工程學系陳永平  
   https://ocw.nycu.edu.tw/?course_page=all-course%2Fcollege-of-electrical-and-computer-engineering%2Fintroduction-to-electric-circuit-112

主題對到的範圍：

| 主題 | 對照 |
| --- | --- |
| 電荷、電壓與電流 | AAC 直流第 1 章；OCW 第 1 章 |
| 歐姆定律與電功率 | AAC 直流第 2 章；OCW 第 2 章 |
| 串聯與並聯 | AAC 直流第 5、7 章；OCW 第 2 章 |
| 克希荷夫定律與分壓分流 | AAC 直流第 6 章；OCW 第 2 章 |
| 戴維寧、諾頓與最大功率 | AAC 直流第 10 章；OCW 第 2 章 |
| 一階暫態與二階阻尼 | AAC 直流第 16 章；OCW 第 3、4 章 |
| 相量、阻抗與功率因數 | AAC 交流第 3、4、5、11 章；OCW 第 5 章 |
| 理想運算放大器 | AAC 半導體第 8 章；OCW 第 6 章 |
| 二極體與電晶體 | AAC 半導體第 2、3、4 章。迴路計算同時用到歐姆定律與 KVL |

每一題解析底部的連結，是該題觀念的出處，不是題目出處。

## 本機啟動

需要 Python 3.10 以上。在專案目錄執行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/check_bank.py
streamlit run app.py
```

macOS 或 Linux 把啟動虛擬環境的指令換成 `source .venv/bin/activate`。

瀏覽器會打開 http://localhost:8501 。手機和電腦在同一個 Wi-Fi 時，可以用終端機裡的 Network URL，用手機直接開。

## 部署到 Streamlit Community Cloud

這個專案沒有資料庫，也沒有密鑰。

1. 把整個資料夾推上 GitHub。倉庫可以是公開的；若是私人倉庫，要在 Streamlit 授權讀取。
2. 用 GitHub 帳號登入 https://share.streamlit.io 。
3. 選 **Create app**。
4. Repository 選這個專案，Branch 選你要部署的分支。
5. Main file path 填 `app.py`。
6. App URL 可以自取。Advanced settings 裡 Python 版本用 3.11 或 3.12 即可。
7. 不要填 Secrets。`requirements.txt` 會自動安裝 Streamlit。
8. 按 **Deploy**。完成後用手機或 iPad 的瀏覽器打開那個網址。

介面是直向、按鈕整列寬。iPad 直向會以中間欄閱讀，橫向也不會把字拉得太開。

## 題庫分檔

| 檔案 | 內容 |
| --- | --- |
| `bank/topics.json` | 主題、學習目標、公式、觀念、來源編號 |
| `bank/templates.json` | 題型。每個題型有接法、假設、數值範圍、情境、答案公式、步驟句型與來源 |
| `bank/sources.json` | 來源標題與連結 |
| `bank/questions.json` | 早期固定題幹，仍會被檢查，對局不再從這裡抽題 |
| `bank/answers.json` | 固定題的正解 |
| `bank/explanations.json` | 固定題的解析 |

應用程式啟動時會做和下面相同的檢查。不過關就不會出題。

```powershell
python scripts/check_bank.py
python -m unittest tests.test_bank
```

固定題的數值仍須和公式一致。題型則會用種子 1、2、3 各抽一題：正解必須等於答案公式，數值題的答案展示和代入式最後一個數字也要能用同一誤差計分，選擇題必須只有一個選項的公式對上正解。計算需要的每一個輸入數字都要出現在題幹或條件裡。

玩家的數值答案在絕對誤差或相對誤差任一成立時算對。

## 加一種題型

在 `bank/templates.json` 新增一個物件。`model` 是這個接法的名稱，每一個 `scenarios` 都要沿用同一個 `model`。`variables` 寫可抽的數值，`derived` 和 `answer_formula` 只用安全四則、次方以及 `sqrt`、`exp`、`log`、`abs`、`hypot`。步驟放在 `steps`，出題時才把數字填進去。若接法或物理條件變了，請新增題型，不要改用別的題型的答案公式。加完執行 `python scripts/check_bank.py`。
