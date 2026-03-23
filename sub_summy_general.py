import os
import glob
from pathlib import Path
import ollama
from tqdm import tqdm
from datetime import datetime

try:
    import opencc
    # s2twp: 簡體轉繁體台灣習慣用語
    converter = opencc.OpenCC('s2twp.json')
except ImportError:
    converter = None



FINAL_OUTPUT_DIR = "./final_output"
MODEL_NAME = "gemma3:12b-it-q4_K_M"

def generate_summary(md_file_path):
    """
    讀取校正後的 md 檔，拆分段落後請 Ollama 產生重點整理。
    """
    filename = Path(md_file_path).stem
    # 產生的檔案名稱：原名_重點整理.md
    summary_out = os.path.join(FINAL_OUTPUT_DIR, f"{filename}_重點整理.md")
    
    if os.path.exists(summary_out):
        print(f"⏭️  {filename} 已經有重點整理啦，先略過。")
        return summary_out
        
    print(f"\n📝 準備產生重點整理: {filename} ...")
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 讀取檔案失敗: {e}")
        return None

    
    # 每 2000 字切一段
    chunk_size = 2000
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    try:
        client = ollama.Client(host='http://localhost:11434', timeout=600)
    except Exception as e:
        print(f"❌ 初始化 Ollama Client 失敗: {e}")
        return None

    final_combined_summary = ""
    full_summary = ""
    
    for idx, chunk in enumerate(chunks):
        tqdm.write(f"⏳ [AI 思考中... 正在整理重點筆記，進度 {idx+1}/{len(chunks)}]")
        
        prompt = f"""你好！我是你的逐字稿整理助手。
我會把這段錄音轉錄稿整理成一份結構清晰、重點突出的學習筆記。

請針對以下【逐字稿內容】進行整理，並遵循以下規範：

### 📝 任務要求：
1. **繁體化校正**：請嚴格將所有內容轉換為「繁體中文」，並修正可能的音誤或錯字。
2. **語氣風格**：請維持溫和、清晰、條理分明的整理口吻，像是幫同學做好一份課堂筆記。
3. **系統化結構**：請嚴格套用以下 Markdown 格式排版，不要隨意更動標題名稱：

## 📑 學習筆記：[請根據這段內容起一個簡潔明確的副標題]

> [!TIP]
> **本段核心**：[用 1-2 句話精煉地總結這段最重要的核心訊息，要讓人一眼就看懂講者在說什麼。]

### 💡 核心知識點
* **[小標題 1]**：[內容詳述]
    * *補充*：[僅限總結文本中已有的細節或定義，避免憑空捏造內容]
* **[小標題 2]**：[內容詳述]

### 🔍 具體範例或案例
* **[範例場景]**：[詳述講者提到的具體情境、操作步驟或實際應用案例]

### 🛠️ 實作建議與行動方針
* **[建議內容]**：[錄音中提到的具體做法、工具使用技巧或給聽眾的行動方針]

---
**整理小結**：
[一段簡潔的結語，總結這段內容的重點與價值（約 50-100 字）。]

### ⚠️ 特別提醒：
* **保留細節**：不要只寫大綱，要把講者說的邏輯、步驟細節都精煉地保留下來。
* **嚴禁自創**：如果錄音裡沒提到的內容，請不要自己加進去，只整理講者實際說過的內容。

---
逐字稿內容：
{chunk}
"""
        try:
            response = client.chat(model=MODEL_NAME, messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ], options={
                "temperature": 0.4,
                "repeat_penalty": 1.10,
                "num_ctx": 4096, 
            }, stream=True)
            
            summary_text = ""
            for r_chunk in response:
                word = r_chunk['message']['content']
                summary_text += word
                print(word, end='', flush=True)
                
            print("\n")
            
            chunk_summary = summary_text.strip()
        
            # 如果有多個 Part，則增加分段標題
            if len(chunks) > 1:
                full_summary += f"\n\n---\n\n## 📒 第 {idx+1} 段整理\n\n"
            
            full_summary += chunk_summary

        except Exception as e:
            print(f"\n❌ 第 {idx+1} 段重點整理時發生錯誤: {e}")
            continue

    # 加入主標題與 YAML Header
    base_name = Path(md_file_path).stem
    now_str = datetime.now().strftime('%Y-%m-%dT%H:%M')
    
    main_header = f"---\ncreated: {now_str}\ntags: \n---\n\n"
    main_header += f"# 📝 逐字稿重點整理：{base_name}\n\n"
    main_header += f"> **整理時間**：{now_str}\n"
    main_header += f"> **筆記來源**：`{os.path.basename(md_file_path)}`\n\n"
    
    final_combined_summary = main_header + full_summary

    if converter:
        print("🔄 正在確保輸出完全為繁體中文...")
        final_combined_summary = converter.convert(final_combined_summary)
    
    with open(summary_out, 'w', encoding='utf-8') as f:
        f.write(final_combined_summary)
        
    print(f"✅ {filename} 重點整理已產生並儲存至 {summary_out}！")
    return summary_out

def main():
    print("✨ 啟動 AI 重點整理腳本 (由 Ollama 加持) ...")
    
    os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)
    md_files = glob.glob(os.path.join(FINAL_OUTPUT_DIR, "*.md"))
    # 過濾掉已經是整理過的檔案 (名稱中包含 _重點整理)
    source_files = [f for f in md_files if "_重點整理" not in f]
    
    if not source_files:
        print("🤔 final_output 資料夾裡面沒有找到可以整理的 .md 檔案。")
        return

    print(f"📂 共找到 {len(source_files)} 個待整理的 Markdown 檔！")
    
    for file_path in source_files:
        generate_summary(file_path)
        
    print("\n🎉 所有的重點整理作業都完成了！")

if __name__ == "__main__":
    main()
