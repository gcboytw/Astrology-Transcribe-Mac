# 占星語音轉錄與校正系統技術規格書 (Mac 平台專用版)

## 1. 專案概述
本專案旨在 macOS (Apple Silicon) 平台上建立一套自動化工作流，利用專為 Mac 優化的 `mlx-whisper` (或 Core ML 加速架構) 進行高效、低功耗的語音轉錄，並結合本地端 `Ollama` 進行占星專業術語校正，最終產出符合筆記需求的 Markdown 與 SRT 字幕檔案。

## 2. 環境需求
- **作業系統**: macOS 13.0 (Ventura) 或以上
- **硬體需求**: Apple Silicon 系列晶片 (M1 / M2 / M3 / M4)
- **Python 版本**: 3.9 或以上
- **核心依賴**:
    - `mlx-whisper`: Apple 官方推出的語音轉文字引擎 (完整發揮 M 系列晶片 GPU 與統一記憶體效能)
    - `ollama`: 呼叫本地 LLM 進行文字校正 (原生支援 Mac Metal 架構加速)
    - `pysrt`: (選配) 若需精細處理 SRT 格式

## 3. 資料夾結構預設
```text
Astrology-Transcribe-Mac/
├── models/
│   └── mlx-whisper-large-v3/  # mlx 格式模型快取路徑
├── output/
│   ├── [filename].srt         # 轉錄後字幕檔
│   └── [filename].md          # 轉錄後筆記檔
├── final_output/
│   ├── [filename]-ok.srt      # 校正後字幕檔
│   └── [filename]-ok.md       # 校正後筆記檔
├── audio/                     # 存放 待處理音檔
├── transcribe_engine.py       # 主程式腳本
├── sub_edit.py                # 字幕校正腳本
└── astrology_data.py          # 存放 Glossary 名詞庫
```

## 4. 技術流程規格

### Step 1: 模型初始化與硬體加速

* **模型選擇**: 使用基於 MLX 架構的 Whisper `large-v3` 或 `large-v3-turbo` 版本。
* **儲存設定**: 程式啟動時，若無本機快取將無縫從 Hugging Face 下載 MLX 格式模型。
* **運算設定 (Core ML / MLX)**: 
    * **預設配置**: 透過 Apple MLX 框架自動調度 GPU，利用統一記憶體大頻寬進行高速推理。
    * **極致低功耗配置 (Core ML)**: 若導入 `whisper.cpp` 的 Core ML 轉譯版 (.mlpackage)，可將全數語音矩陣運算轉交由 Neural Engine (NPU) 處理，達到機身全冷、零風扇噪音的背景處理體驗。

### Step 2: 轉錄階段 (語音引擎)

* **語音引導 (Prompting)**:
    * 注入 `initial_prompt`: "相位、合相、三分相、六分相、四分相、對相、宮位"。
* **效能優勢**: 依靠 Mac 的高記憶體頻寬 (如 M2 Pro/M4 規格)，能有效減少大模型 (large-v3) 搬運資料的瓶頸。

### Step 3: 校正階段 (Ollama)

* **外部資料庫**: 讀取 `astrology_data.py` 中的 `glossary` 列表。
* **校正邏輯**:
    * 針對轉錄出的 Segment 進行逐段或批量校正。
    * 修正同音異音字（例如：「合相」誤植為「河相」）。
* **硬體加速**: Mac 平台下的 Ollama 預設調用 MPS (Metal Performance Shaders)，校正過程能保持極高的生成速度。

### Step 4: 輸出規格

* **SRT 格式**: 保留標準時間標籤與校正後的文本。
* **Markdown 格式**:
    * 取代原有的純文字檔。
    * 使用 `### [時間戳]` 作為標題層級。
    * 內容呈現排版過、易讀的占星筆記。

## 5. 快速安裝指令

```bash
# 針對 Mac Apple Silicon 安裝專用的 MLX 轉錄套件
pip install mlx-whisper ollama
```

## 6. 後續擴展建議

* **自動化捷徑整合**: 配合 Mac 內建的 `Automator` 或是「捷徑 (Shortcuts)」App，實作「右鍵點擊音檔 -> 直接執行轉錄與校正」的無縫工作流。
* **全面接入 Core ML**: 若有需要長時間錄音監聽的應用，可考慮將工具進一步編譯為純 Core ML 版本，將續航影響降到最低。
