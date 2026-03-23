# Antigravity Assistant Instructions

## Behavioral Rules
- **Token Usage / Performance Models**: 
  - ALWAYS notify and ask for permission before performing a full codebase scan or extensive analysis using high-performance cloud models (e.g., `Gemini 3.1 Pro`, `Gemma 3.1 Pro`).
  - Prefer using local models via `Ollama` (like `gemma3:12b`) for routine tasks where token usage is not a concern.

## Project Overview
This project is for transcribing and summarizing astrology-related audio content on macOS.
- **Main Workflow**: Transcribe audio -> Generate Subtitles -> Summarize using local LLM.
- **Key Models**: `gemma3:12b` (via Ollama) for summaries and edits.
