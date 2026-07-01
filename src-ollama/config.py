# ==========================================
# Local Ollama Configuration
# ==========================================
# Ollama runs offline on your own machine, so no API key or proxy is needed.
# Make sure Ollama is running before executing code.py:
#   ollama serve
# and that the model is pulled:
#   ollama pull qwen2.5:7b

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"

# Context window size (in tokens) given to the model.
# IMPORTANT: Ollama defaults to only 2048 tokens if this isn't set explicitly,
# which silently truncates long conversations. 8192 is a safe default for
# qwen2.5:7b on most machines with 16GB+ RAM. Lower it (e.g. 4096) if you
# hit out-of-memory errors, or raise it if you have plenty of RAM/VRAM.
OLLAMA_NUM_CTX = 8192
