import os
import glob
from pathlib import Path

# 修正md檔未能排版的問題
FINAL_OUTPUT_DIR = "./final_output"

def parse_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = content.strip().split('\n\n')
    segments = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            idx = lines[0]
            time_range = lines[1]
            text = '\n'.join(lines[2:])
            segments.append({"idx": idx, "time": time_range, "text": text})
    return segments

def main():
    srt_files = glob.glob(os.path.join(FINAL_OUTPUT_DIR, "*.srt"))
    if not srt_files:
        print("🤔 找不到可以轉檔的 SRT。")
        return
        
    print(f"找到 {len(srt_files)} 個 SRT 檔案準備重組為 MD...")

    for file_path in srt_files:
        filename = Path(file_path).stem.replace("-ok", "")
        md_out = os.path.join(FINAL_OUTPUT_DIR, f"{filename}-ok.md")
        
        segments = parse_srt(file_path)
        
        with open(md_out, 'w', encoding='utf-8') as f:
            f.write(f"# {filename} (AI 專業校正版)\n\n")
            
            paragraph_text = []
            start_time = None
            
            for i, s in enumerate(segments):
                if start_time is None:
                    start_time = s['time'].split(' --> ')[0].split(',')[0]
                    
                text = s['text']
                
                # 過濾掉可能由於模型殘留前言導致的單獨 "OK"、"好的" 等雜訊
                if text in ["OK", "好的", "OK。", "好的。"] and len(paragraph_text) > 0:
                    continue
                    
                paragraph_text.append(text)
                
                clean_end = text.strip()
                # ★ 在這裡調整段落長度：預設是 15 句且遇到標點才換段
                if (len(paragraph_text) >= 15 and clean_end.endswith(('。', '？', '！', '.', '?', '!'))) or len(paragraph_text) >= 20:
                    combined_text = "".join(paragraph_text)
                    f.write(f"### [{start_time}]\n{combined_text}\n\n")
                    
                    paragraph_text = []
                    start_time = None
                    
            # 處理結尾剩餘的句子
            if paragraph_text:
                combined_text = "".join(paragraph_text)
                f.write(f"### [{start_time}]\n{combined_text}\n\n")
        
        print(f"✅ 成功為 {filename}.srt 重新生成優美的短文 {filename}-ok.md ！")

if __name__ == "__main__":
    main()
