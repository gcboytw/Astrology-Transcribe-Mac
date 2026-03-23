import os
import glob
import subprocess
from pathlib import Path
from huggingface_hub import snapshot_download
from tqdm import tqdm
import mlx_whisper

# 根據規格書定義的路徑
MODEL_DIR = "./models/mlx-whisper-large-v3"
AUDIO_DIR = "./audio"
OUTPUT_DIR = "./output"

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED_FORMATS = ["*.aac", "*.AAC", "*.mp3", "*.MP3", "*.mp4", "*.MP4", "*.m4a", "*.M4A", "*.wav", "*.WAV"]

def format_timestamp(seconds: float) -> str:
    """將秒數轉為 SRT 的時間格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def download_model():
    print("⏳ 正在檢查模型狀態...")
    repo_id = "mlx-community/whisper-large-v3-mlx"
    try:
        print("📥 如果尚未下載，現在會從 Hugging Face 下載 (這可能需要一點時間，請確認網路暢通)...")
        # snapshot_download 內建會有 tqdm 的漂亮進度條
        snapshot_download(
            repo_id=repo_id,
            local_dir=MODEL_DIR,
            local_dir_use_symlinks=False
        )
        print("✅ 模型準備就緒！\n")
    except Exception as e:
        print(f"❌ 模型下載失敗: {e}")
        raise

def process_file(file_path):
    filename = Path(file_path).stem
    ext = Path(file_path).suffix.lower()
    srt_path = os.path.join(OUTPUT_DIR, f"{filename}.srt")

    if os.path.exists(srt_path):
        print(f"⏭️  {filename} 已經轉錄過，略過。")
        return

    print(f"\n🎙️ 開始轉錄: {filename} ...")

    temp_wav_path = None
    transcribe_target = file_path

    if ext in [".aac", ".mp3", ".m4a"]:
        print(f"🔄 正在將 {ext} 轉換為 16kHz 單聲道 wav 格式，讓辨識更精準...")
        temp_wav_path = os.path.join(AUDIO_DIR, f"temp_{filename}.wav")
        cmd = ["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", temp_wav_path]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            transcribe_target = temp_wav_path
        except Exception as e:
            print(f"❌ FFmpeg 轉換失敗: {e}")
            return

    # 從 astrology_data.py 或是給個預設引導詞
    try:
        from astrology_data import glossary
        glossary_prompt = "、".join(glossary)
    except ImportError:
        glossary_prompt = "相位、合相、三分相、六分相、四分相、對相、宮位"

    # 加入繁體中文與標點符號的強力引導
    initial_prompt = f"以下是一段繁體中文的語音記錄，請務必使用繁體中文輸出，並加上適當的標點符號，切勿使用簡體字。常見詞彙包含：{glossary_prompt}。"

    try:
        # 由於 mlx-whisper 目前的 API 在回傳 segments 時是一次性 return（不同於 faster-whisper 的 generator），
        # 如果我們要顯示進度條，可以關閉 verbose 等它跑完，或是保留 verbose 但不加 tqdm。
        # 不過考量到 mlx-whisper 跑整段檔案的速度極快，為了讓畫面乾淨且有「處理中」的進度感，
        # 我們先顯示檔案大小或其他提示，然後將結果轉為類似 batch_transcribe 的逐行寫檔。
        
        print("⏳ 正在由 Apple Silicon GPU 進行極速推論，請稍候...")
        result = mlx_whisper.transcribe(
            transcribe_target,
            path_or_hf_repo=MODEL_DIR,
            initial_prompt=initial_prompt,
            language="zh", 
            condition_on_previous_text=False, 
            no_speech_threshold=0.6, 
            fp16=True, 
            verbose=False  # 關閉原本會洗頻的內建輸出，改用我們自己乾淨的寫檔流程
        )

        segments = result.get('segments', [])
        
        # 定義常見的 Whisper 全靜音/噪聲幻覺詞庫
        hallucination_keywords = ["李宗盛", "点赞", "點讚", "订阅", "訂閱", "打赏", "打賞", "明镜与点点", "Amara.org", "字幕", "編導、", "编导、"]
        
        # 取得最後一個時間點當作總長度
        total_duration = segments[-1]['end'] if segments else 1.0
        
        print("\n======================================")
        print(f"✅ 語音辨識完成！開始清理並寫入字幕檔...")
        
        # 使用 tqdm 顯示寫檔的進度與過濾結果
        with open(srt_path, "w", encoding="utf-8") as f_srt:
            
            valid_idx = 1
            with tqdm(total=total_duration, desc="建立檔案進度", unit="秒") as pbar:
                for segment in segments:
                    text = segment['text'].strip()
                    text = text.replace(' ', '')
                    
                    # 過濾雜訊
                    if any(keyword in text for keyword in hallucination_keywords) or not text:
                        # 推進進度條但跳過寫檔
                        pbar.n = min(segment['end'], total_duration)
                        pbar.refresh()
                        continue
                        
                    start_str = format_timestamp(segment['start'])
                    end_str = format_timestamp(segment['end'])
                    
                    # 寫入 SRT
                    f_srt.write(f"{valid_idx}\n{start_str} --> {end_str}\n{text}\n\n")
                    
                    valid_idx += 1
                    
                    # 推進進度條
                    pbar.n = min(segment['end'], total_duration) 
                    pbar.refresh()

        print(f"\n✅ {filename} 轉錄與檔案生成完成！產出檔案於 output 資料夾。")
    except Exception as e:
        print(f"❌ 處理 {filename} 時發生錯誤: {e}")
    finally:
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            print("🧹 已清理暫存 WAV 檔。")

def main():
    print("🚀 啟動 Mac 專用 GPU 加速語音轉錄引擎...")
    download_model()

    audio_files = []
    for fmt in SUPPORTED_FORMATS:
        audio_files.extend(glob.glob(os.path.join(AUDIO_DIR, fmt)))

    if not audio_files:
        print("🤔 找不太到 audio 資料夾中的 aac, mp3, m4a, mp4 或是 wav 檔案喔，確認一下檔案副檔名！")
        return

    print(f"📂 總共找到 {len(audio_files)} 個待處理音檔/影音檔。")
    
    # 處理全域的進度條
    for file_path in tqdm(audio_files, desc="轉錄總進度"):
        process_file(file_path)
    
    print("\n🎉 全部處理完成！你可以用 sub_edit.py 來進行 AI 校正囉！")

if __name__ == "__main__":
    main()
