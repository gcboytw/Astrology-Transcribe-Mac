"""
transcribe.py — 一鍵完成逐字稿全流程整合腳本

執行順序：
  Step 1: transcribe_engine.py  → 語音 → SRT
  Step 2: sub_edit-14b.py       → SRT → AI 校正 + Markdown
  Step 3: sub_summy_general.py  → Markdown → 重點筆記

用法：
  python transcribe.py
  python transcribe.py --skip-summy   (只跑轉錄與校正，跳過重點整理)
  python transcribe.py --only-edit    (只跑校正，跳過轉錄與重點整理)
"""

import subprocess
import sys
import os
from datetime import datetime

# ─── 設定 ────────────────────────────────────────────────
PYTHON = sys.executable               # 使用與目前相同的 venv Python
SCRIPTS = {
    "transcribe": "transcribe_engine.py",
    "edit":       "sub_edit-14b.py",
    "summy":      "sub_summy.py",
}

# ─── 工具函式 ─────────────────────────────────────────────
def banner(step: int, title: str):
    width = 52
    print("\n" + "=" * width)
    print(f"  Step {step}: {title}")
    print("=" * width + "\n")

def run_script(name: str, script: str) -> bool:
    """呼叫子腳本，return True 代表成功"""
    script_path = os.path.join(os.path.dirname(__file__), script)
    if not os.path.exists(script_path):
        print(f"❌ 找不到 {script}，請確認檔案存在。")
        return False

    start = datetime.now()
    result = subprocess.run([PYTHON, script_path])
    elapsed = (datetime.now() - start).seconds

    if result.returncode != 0:
        print(f"\n❌ {script} 執行失敗 (returncode={result.returncode})")
        return False

    print(f"\n✅ {name} 完成，耗時 {elapsed} 秒。")
    return True

# ─── 主流程 ──────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    skip_transcribe = "--only-edit" in args or "--skip-transcribe" in args
    skip_edit       = False
    skip_summy      = "--skip-summy" in args

    print("""
╔══════════════════════════════════════════════╗
║   🎙️  逐字稿全流程整合轉錄工具               ║
║   transcribe.py                              ║
╚══════════════════════════════════════════════╝
    """)

    # ── Step 1: 語音轉錄 ──────────────────────────────────
    if not skip_transcribe:
        banner(1, "語音轉錄 (Whisper → SRT)")
        ok = run_script("轉錄", SCRIPTS["transcribe"])
        if not ok:
            print("⛔ 轉錄失敗，流程中止。")
            sys.exit(1)
    else:
        print("⏭️  [Step 1] 已略過語音轉錄。")

    # ── Step 2: AI 校正 ───────────────────────────────────
    if not skip_edit:
        banner(2, "AI 智能校正 (SRT → Markdown)")
        ok = run_script("AI 校正", SCRIPTS["edit"])
        if not ok:
            print("⛔ AI 校正失敗，流程中止。")
            sys.exit(1)
    else:
        print("⏭️  [Step 2] 已略過 AI 校正。")

    # ── Step 3: 重點整理 ──────────────────────────────────
    if not skip_summy:
        banner(3, "重點筆記整理 (Markdown → 重點整理)")
        ok = run_script("重點整理", SCRIPTS["summy"])
        if not ok:
            # 重點整理失敗不強制中止，前兩步的成果已在 final_output
            print("⚠️  重點整理失敗，但前兩步的成果已儲存在 final_output/。")
    else:
        print("⏭️  [Step 3] 已略過重點整理。")

    print("\n🎉 全部流程完成！請至 final_output/ 查看成果。\n")

if __name__ == "__main__":
    main()
