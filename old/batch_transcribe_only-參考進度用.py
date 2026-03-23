import os
import sys
from faster_whisper import WhisperModel
from tqdm import tqdm

# 時間格式轉換工具 (SRT 需要 HH:MM:SS,ms)
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milis:03}"

# --- 設定區 ---
MODEL_PATH = "./models/whisper-large-v3"
AUDIO_DIR = "audio"  # 目標音檔資料夾
INITIAL_PROMPT = "這是一段關於占星學的內容，關鍵字包括：相位、合相、三分相、六分相、四分相、對相、宮位。"

# 確保資料夾存在
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)
    print(f"✅ 已建立 {AUDIO_DIR} 資料夾，請將 mp4 或是 mp3 放入後再執行一次本程式。")
    sys.exit()

# 取得資料夾內所有的音檔 (mp3, mp4)
audio_files = [f for f in os.listdir(AUDIO_DIR) if f.lower().endswith(('.mp4', '.mp3'))]

if not audio_files:
    print(f"❌ 在 {AUDIO_DIR} 資料夾中找不到任何 mp3 或 mp4 檔案！")
    sys.exit()

print(f"📂 找到 {len(audio_files)} 個待處理音檔，準備開始轉錄。")

# 1. 初始化 Whisper 模型 (針對 288V CPU 最佳化)
print("載入 Whisper large-v3 模型...")
model = WhisperModel(
    "large-v3", 
    device="cpu",               # 在 288V 上，CPU 配合 OpenVINO 指令集非常快
    compute_type="int8",        # int8_ssse3 在這個套件版本不支援，改回一般 int8
    download_root=MODEL_PATH,
    cpu_threads=6                # 善用你 288V 的 6 核心
)

# 處理每一個音檔
for filename in audio_files:
    audio_path = os.path.join(AUDIO_DIR, filename)
    base_name = os.path.splitext(filename)[0]
    
    # 輸出檔案放在同一個 audio 目錄下
    srt_path = os.path.join(AUDIO_DIR, f"{base_name}.srt")
    md_path = os.path.join(AUDIO_DIR, f"{base_name}.md")

    # 如果已經產生過了就跳過 (避免中斷後要全部重頭來)
    if os.path.exists(srt_path) and os.path.exists(md_path):
        print(f"⏭️ {filename} 已經處理過，跳過。")
        continue

    print(f"\n======================================")
    print(f"🎬 正在轉錄: {filename} ...")
    
    # 2. 進行轉錄
    segments, info = model.transcribe(
        audio_path, 
        beam_size=5, 
        initial_prompt=INITIAL_PROMPT,
        vad_filter=True # 自動過濾靜音段落
    )
    
    print(f"⏱️ 偵測到音檔長度: {info.duration:.2f} 秒，語言: {info.language}")
    
    # 4. 邊轉錄邊生成檔案 (不用等全部轉完才寫檔，可以省記憶體而且即時)
    with open(srt_path, "w", encoding="utf-8") as srt_file, \
         open(md_path, "w", encoding="utf-8") as md_file:
        
        md_file.write(f"# 占星轉錄筆記 - {filename}\n\n")

        # 使用 tqdm 顯示進度條，總時間為音檔長度
        with tqdm(total=info.duration, desc="轉錄進度", unit="秒") as pbar:
            for i, segment in enumerate(segments):
                start_str = format_time(segment.start)
                end_str = format_time(segment.end)
                
                # 寫入 SRT 格式
                srt_file.write(f"{i+1}\n{start_str} --> {end_str}\n{segment.text.strip()}\n\n")
                
                # 寫入 Markdown 格式
                md_file.write(f"### [{start_str}]\n{segment.text.strip()}\n\n")
                
                # 推進進度條
                pbar.n = min(segment.end, info.duration) 
                pbar.refresh()

    print(f"\n✅ 完成！已生成: \n  - {srt_path}\n  - {md_path}")

print("\n🎉 全部音檔處理完畢！")
