import os
import glob
from pathlib import Path
import ollama
from tqdm import tqdm
import json

try:
    from astrology_data import common_corrections, astrology_terms
except ImportError:
    print("❌ 找不到 astrology_data.py 或者裡面缺少 common_corrections 字典！")
    exit(1)

FINAL_OUTPUT_DIR = "./final_output"
MODEL_NAME = "qwen2.5:14b"  # 沿用之前的強大模型

def correct_paragraph(text):
    """
    請 Ollama 進行二次語意與同音錯字校正。
    """
    # 將對照表轉為友善的字串提示
    corrections_str = "\n".join([f"  - `{wrong}` 修正為 `{correct}`" for wrong, correct in common_corrections.items()])
    
    prompt = f"""你現在是一位具備深厚占星背景與文學素養的專業編輯。你的任務是進行這段文本的「第二次語意抓漏與修正」。

📝【嚴格遵守規則】📝
1. **同音異義檢查**：請優先根據以下常見語音誤判對照表，將字面上怪異的語音辨識錯誤修正回來：
{corrections_str}
2. **極簡修正**：只處理那些「聽起來合理，但寫出來明顯是同音錯字」的情況（例如：把「撒野」聽成「殺野」）。如果沒有錯字，請維持原句。
3. **保持語境與語氣**：保持講者原汁原味的口語表達，絕對「不要」額外添加其他語句、解釋、開場白（例如「好的」或「請參考」）或刪除原本的句子。
4. **只輸出結果**：請直接給出純文字結果，不要加上 markdown 標籤（如 ```）。

待修正文本：
{text}
"""
    try:
        client = ollama.Client(host='http://localhost:11434', timeout=600)
        response = client.chat(model=MODEL_NAME, messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ], options={
            "temperature": 0.1,  # 保持極低的溫度，避免 AI 擅自發揮創意
            "num_ctx": 2048,
        })
        
        content = response['message']['content'].strip()
        
        # 暴力洗掉 Qwen 單句模式下愛講的廢話
        lines = content.split('\n')
        clean_lines = []
        for line in lines:
            if "```" in line or "請參考" in line or "結果為" in line or "保持原樣" in line or "沒有錯字" in line or "不需修正" in line:
                continue
            clean_lines.append(line)
            
        final_text = "\n".join(clean_lines).strip()
        return final_text if final_text else text
    except Exception as e:
        print(f"\n❌ 校正時發生錯誤: {e}")
        return text

def process_md_file(file_path):
    print(f"\n🔍 開始二次校正: {Path(file_path).name} ...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    
    # 計算需要校正的段落數量來顯示進度條
    paragraphs_to_correct = [line for line in lines if line.strip() and not line.startswith('#')]
    
    pbar = tqdm(total=len(paragraphs_to_correct), desc="二次校正進度")
    
    for line in lines:
        stripped = line.strip()
        
        # 空行或標題列 (例如 # 20250418 或 ### [00:01:00]) 直接保留不送去校正
        if not stripped or stripped.startswith('#'):
            new_lines.append(line)
            continue
            
        # 送入 AI 進行二次把關
        corrected_text = correct_paragraph(stripped)
        new_lines.append(corrected_text + "\n")
        pbar.update(1)
        
    pbar.close()
    
    # 直接覆寫原本的 MD 檔案
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print(f"✅ {Path(file_path).name} 二次校正完成！")

def main():
    print("✨ 啟動 AI 智能二次語意校正腳本 (專注修復同音異字) ...")
    
    md_files = glob.glob(os.path.join(FINAL_OUTPUT_DIR, "*.md"))
    if not md_files:
        print("🤔 final_output 資料夾裡面沒有找到可以校正的 .md 檔案。")
        return

    print(f"📂 共找到 {len(md_files)} 個待校正的 Markdown 檔！")
    print(f"📚 目前載入的同音字對照庫有 {len(common_corrections)} 筆設定。\n")
    
    for file_path in md_files:
        process_md_file(file_path)
        
    print("\n🎉 太棒了，所有檔案的二次校正作業皆已完成！")

if __name__ == "__main__":
    main()
