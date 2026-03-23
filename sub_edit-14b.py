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

try:
    from astrology_data import astrology_terms, common_corrections
except ImportError:
    astrology_terms = ["相位", "合相", "三分相", "六分相", "四分相", "對相", "宮位"]
    common_corrections = {}

INPUT_DIR = "./output"
FINAL_OUTPUT_DIR = "./final_output"
MODEL_NAME = "qwen2.5:14b"

os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

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

def correct_text_batch(texts):
    """
    請 Ollama 幫我們批量校正文字。
    維持 SRT 一行對一行的結構，避免時間軸大亂。
    """
    # 準備名詞清單與同音字清單
    glossary_str = "、".join(astrology_terms)
    
    corrections_rules = ""
    if common_corrections:
        corrections_rules = "3. 【同音異義優先修復】：請優先將以下常見語音辨識錯誤修正回來：\n"
        for wrong, correct in common_corrections.items():
            corrections_rules += f"   - 看見「{wrong}」請修正為「{correct}」\n"
    else:
        corrections_rules = "3. 【同音異義修復】：請根據語境與常理，將明顯不通順的發音錯誤修正在字面上（例如把「殺野」改為「撒野」）。\n"
    
    # 為了制裁 Qwen 太愛整併文章的毛病，我們把輸入加上嚴格的 [編號] 錨點
    numbered_texts = [f"[{i+1}] {t}" for i, t in enumerate(texts)]
    
    prompt = f"""你是一個精通占星學的專業文字編輯，正在執行「嚴格的一對一字幕校正」任務。
參考專有名詞庫：{glossary_str}。

📝【遵守規則】📝
1. 你的任務只有：修飾錯別字與同音異字，並【加上適當的標點符號】。
2. 【極度重要：嚴禁過度校正與詞彙替換】：名詞庫僅供「有發音相似的錯字」時參考。如果講者原本發音正確且語意通順（例如講「角度」，就維持「角度」），請「絕對不要」擅自將其替換、升級或翻譯成名詞庫裡的專業術語（如「相位」）。保持講者原汁原味的口語表達！
{corrections_rules.strip()}
4. 絕對不可合併或刪除句子！我給你 {len(texts)} 行，你必須精準地回覆我 {len(texts)} 行。
5. 請維持我給你的「[編號]」格式。
6. 只輸出結果，不要說「好的」或給予任何解釋。

<待校正文本開始>
{chr(10).join(numbered_texts)}
<待校正文本結束>
"""
    try:
        # 加上 stream=True，讓我們肉眼可見它的思考過程
        client = ollama.Client(host='http://localhost:11434', timeout=600)
        
        tqdm.write("\n⏳ [AI 思考中...]")
        # Qwen 2.5 14b 處理錯字校正，temperature 調回 0.1 確保穩定發揮
        response = client.chat(model=MODEL_NAME, messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ], options={
            "temperature": 0.1,
            "num_ctx": 2048, # 限制上下文長度，減少記憶體佔用與運算時間
        }, stream=True)
        
        corrected_text = ""
        for chunk in response:
            word = chunk['message']['content']
            corrected_text += word
            print(word, end='', flush=True)
            
        print("\n") # 結束這批次換行
        
        corrected_text = corrected_text.strip()
        
        corrected_text = corrected_text.strip()
        
        # 把 AI 有時候愛講話的程式碼區塊標籤給脫掉
        if corrected_text.startswith("```"):
            corrected_text = "\n".join(corrected_text.split("\n")[1:])
        if corrected_text.endswith("```"):
            corrected_text = "\n".join(corrected_text.split("\n")[:-1])
            
        # 自動過濾掉可能的空行，避免因為多餘的換行而導致行數對不上
        corrected_lines = [line.strip() for line in corrected_text.strip().split('\n') if line.strip()]
        
        # 簡單驗證行數是否正確
        if len(corrected_lines) == len(texts):
            # 成功了！要把我們剛剛硬塞給它的 [編號] 拔掉，還給系統乾淨的字串
            clean_lines = []
            for line in corrected_lines:
                # 剔除開頭的 "[1] " 這類字串
                import re
                clean_line = re.sub(r'^\[\d+\]\s*', '', line)
                clean_lines.append(clean_line)
            return clean_lines
        else:
            return None # 觸發備用方案
    except Exception as e:
        print(f"\n❌ 呼叫 Ollama 時發生錯誤: {e}")
        return None

def correct_single_text(text):
    """如果批次處理失敗（行數對不上），就用這個單句一對一套餐"""
    glossary_str = "、".join(astrology_terms)
    
    corrections_rules = ""
    if common_corrections:
        corrections_rules = "【同音異義修復】：遇下列錯字請立刻修正\n"
        for wrong, correct in common_corrections.items():
            corrections_rules += f"   - 「{wrong}」➔「{correct}」\n"

    prompt = f"""你是一個專業的占星學文字編輯。請校正這一句話的錯別字與同音異字。
請參考專有名詞庫：{glossary_str}。
【極度重要：嚴禁過度校正與詞彙替換】：名詞庫僅供「錯字」參考。如果講者原本發音正確且語意通順（例如講「角度」，就維持「角度」），請絕對不要擅自將其替換或升級成名詞庫裡的專業術語（如「相位」）。保持講者原汁原味的口語表達！
{corrections_rules.strip()}
【極度重要】請務必在句意停頓處加上適當且豐富的標點符號（如逗號、句號、問號、驚嘆號等）。
只修正錯字與標點，直接給出單純的結果，不可加上任何前言或後語、編號、或是「請參考...」這類的解釋。

原始文字: {text}"""
    try:
        # 單句處理也比照辦理建立 client 加上 timeout，並防呆加上 num_ctx
        client = ollama.Client(host='http://localhost:11434', timeout=600)
        response = client.chat(model=MODEL_NAME, messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ], options={
            "temperature": 0.1,
            "num_ctx": 1024, # 單句需要的上下文更少
        })
        content = response['message']['content'].strip()
        
        # 暴力洗掉 Qwen 單句模式下愛講的廢話
        lines = content.split('\n')
        clean_lines = []
        for line in lines:
            if "```" in line or "請參考" in line or "結果為" in line or "保持原樣" in line or "沒有錯別字" in line:
                continue
            clean_lines.append(line)
            
        final_text = "\n".join(clean_lines).strip()
        return final_text if final_text else text
    except Exception:
        return text

def process_file(file_path):
    filename = Path(file_path).stem
    srt_out = os.path.join(FINAL_OUTPUT_DIR, f"{filename}.srt")
    txt_out = os.path.join(FINAL_OUTPUT_DIR, f"{filename}.txt")
    md_out = os.path.join(FINAL_OUTPUT_DIR, f"{filename}.md")

    if os.path.exists(srt_out) and os.path.exists(md_out):
        print(f"⏭️  {filename} 已經被校正過啦，先略過。")
        return

    print(f"\n✍️ 準備校正: {filename} ...")
    segments = parse_srt(file_path)
    
    # 調整為一次 10 句，配合 qwen2.5:7b 的效能
    batch_size = 5
    corrected_segments = []
    
    print("🤖 已經請 Ollama 喝杯咖啡，開始校正 (因為是在本地跑，這會花點時間，別擔心)...")
    
    for i in tqdm(range(0, len(segments), batch_size), desc="字幕段落處理進度"):
        batch = segments[i:i+batch_size]
        texts = [s['text'] for s in batch]
        
        corrected_lines = correct_text_batch(texts)
        if corrected_lines is None:
            # AI 剛剛亂改了行數，我們啟動備案一句一句處理
            tqdm.write("⚠️ AI 好像有點激動打亂了行數，啟動單句精確安全校正模式...")
            corrected_lines = []
            for t_idx, text in enumerate(texts):
                tqdm.write(f"   ➔ 正在搶救第 {t_idx+1}/{len(texts)} 句... (這需要一點耐心)")
                corrected_lines.append(correct_single_text(text))
            
        for s, c_text in zip(batch, corrected_lines):
            # 去除可能的空行與空白
            clean_text = c_text.strip() if c_text.strip() else s['text']
            
            # 確保完全繁體 (加上台灣語境習慣轉換)
            if converter:
                clean_text = converter.convert(clean_text)
                
            s['text'] = clean_text
            corrected_segments.append(s)
            
            # 即時印出給你看，證明沒偷懶
            tqdm.write(f"📝 {s['time'].split(' --> ')[0].split(',')[0]} | {clean_text}")

    # 產出漂亮的三種格式
    with open(srt_out, 'w', encoding='utf-8') as f:
        for s in corrected_segments:
            f.write(f"{s['idx']}\n{s['time']}\n{s['text']}\n\n")

    # 暫時取消輸出 txt
    # with open(txt_out, 'w', encoding='utf-8') as f:
    #     for s in corrected_segments:
    #         f.write(f"{s['text']}\n")

    #取消yaml屬性 tags: [astrology]\n
    with open(md_out, 'w', encoding='utf-8') as f:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M")
        yaml_header = f"---\ncreated: {now}\n---\n\n"
        f.write(yaml_header)
        f.write(f"# {filename} (AI 專業校正版)\n\n")
        
        # 將字幕分段合併成短文，每 15 句 (約1.5~2分鐘) 或根據標點符號結尾自動換段
        paragraph_text = []
        start_time = None
        
        for i, s in enumerate(corrected_segments):
            if start_time is None:
                start_time = s['time'].split(' --> ')[0].split(',')[0]
                
            text = s['text']
            # 過濾掉可能因為 Qwen 殘留前言導致的單獨 "OK"、"好的" 等雜訊
            if text in ["OK", "好的", "OK。", "好的。"] and len(paragraph_text) > 0:
                continue
                
            paragraph_text.append(text)
            
            # 必須累積滿 15 句「且」剛好遇到標點符號結尾，才算是一個完整的語意段落。
            # 如果超過 20 句都等不到標點符號，則強制換段避免段落過長。
            clean_end = text.strip()
            if (len(paragraph_text) >= 15 and clean_end.endswith(('。', '？', '！', '.', '?', '!'))) or len(paragraph_text) >= 20:
                combined_text = "".join(paragraph_text)  # 中文合併不加空格
                f.write(f"### [{start_time}]\n{combined_text}\n\n")
                
                # 重置段落收集器
                paragraph_text = []
                start_time = None
                
        # 處理迴圈結束後剩餘的尾巴句子
        if paragraph_text:
            combined_text = "".join(paragraph_text)
            f.write(f"### [{start_time}]\n{combined_text}\n\n")

    print(f"✅ {filename} 已經校正並轉出 md 與 srt 囉！")

def main():
    print("✨ 啟動 AI 智能本地校正腳本 (由 Ollama 的 qwen2.5:14b 大神加持) ...")
    
    srt_files = glob.glob(os.path.join(INPUT_DIR, "*.srt"))
    if not srt_files:
        print("🤔 output 資料夾裡面空空的，沒有找到可以校正的 .srt 檔案。要不要先執行一次 transcribe_engine.py 轉錄一下？")
        return

    print(f"📂 共找到 {len(srt_files)} 個待校正的字幕檔！")
    
    for file_path in srt_files:
        process_file(file_path)
        
    print("\n🎉 太棒了，所有的校正作業都完成了！這陣子辛苦你的電腦大腦了。")

if __name__ == "__main__":
    main()
