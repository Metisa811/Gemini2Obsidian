# 🧠 NeuralMind Scraper 🕸️

**An advanced automation, extraction, and hierarchical knowledge graph construction pipeline for AI chat conversations (Google Gemini) — purpose-built for Obsidian.**

**NeuralMind Scraper** is far more than a simple web scraper. It's a complete data pipeline that takes raw, unstructured web conversations and transforms them — using the power of natural languag[...]

---

## ✨ Key Features & Achievements

The project tackles complex data engineering and web extraction challenges with robust, production-grade solutions:

- **Surgical LaTeX Extraction (Deep LaTeX Restoration):** Bypasses the layered visual structure of the web (DOM) by injecting custom JavaScript to extract pure KaTeX source code. Ensures even the [...]
- **Hierarchical Knowledge Graph Architecture:** Leverages an AI-based "Knowledge Architect." Each chat is intelligently parsed and mapped to a **parent node (Domain)** and a **sub-domain**, produ[...]
- **Automatic Code Block Isolation:** Automatically identifies programming code blocks, separates them from chat text, and saves them as standalone physical files (`.py`, `.tex`, `.m`) with intern[...]
- **Intelligent Session Management & Anti-Ban Protection:** Stores user sessions in `auth_state.json` for seamless automatic login. Utilizes Playwright's anti-bot headers and optional proxy tunnel[...]
- **Exponential Backoff Retry System:** Intelligently handles API traffic issues (`429` and `503` errors) with an exponential backoff mechanism, ensuring stability and resilience.

---

## 🏗️ System Architecture (How It Works)

The project operates in three distinct but interconnected pipeline phases:

### 🌐 Phase 1: Raw Extraction Engine (Web Scraper)
Using `Playwright`, the bot launches a browser, logs in with the stored session, and extracts chat links. An injected JavaScript script traverses the nested HTML tags to extract messages, strippin[...]

### 🧹 Phase 2: Primary Text Sanitization (Text Sanitizer)
A Python script processes the JSON files, removing hidden web characters (zero-width spaces), redundant noise (e.g., "Gemini said"), and irregular line breaks using advanced Regex patterns.

### 🧠 Phase 3: AI-Powered Processing (AI Formatter & Graph Engine)
The cleaned text is sent to an AI formatting engine which restructures the content, corrects LaTeX formulas, preserves code blocks, and injects YAML frontmatter metadata — including domain/sub-d[...]

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Metisa811/Gemini2Obsidian.git
cd Gemini2Obsidian
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure API Key (Cloud variant)
Edit `src/config.py` and add your API key from Google AI Studio (used by the cloud/Gemini API variant):
```python
API_KEY = "Your_API_Key_Here"
USE_PROXY = False  # Set to True if you need proxy support
```

### 4. Initialize Session (First-time Login)
Run `login.py` once to log into your account and save the session state to `auth_state.json`:
```bash
cd src
python login.py
```

### 5. Run the Core Pipeline (Cloud/Gemini API)
```bash
python code.py
```

---

## 🔁 Offline / Local Variant: src-ollama/

This repository now includes an alternative fully-local pipeline at `src-ollama/` that replicates the same extraction and Obsidian graph-building flow but uses a local Ollama server (model `qwen2.[...]

Key differences
- `src/` : Cloud (uses the Gemini API).
- `src-ollama/` : Offline / Local (uses Ollama + local model for formatting).

Prerequisites
- Playwright (for web scraping) and Python installed.
- Ollama installed and running locally:
  - Start Ollama: `ollama serve`
  - Pull the model: `ollama pull qwen2.5:7b`

Setup & Run (src-ollama)
1. Change to the offline variant directory:
   ```bash
   cd src-ollama
   ```
2. Install Python deps:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Optionally update `src-ollama/config.py`:
   - `OLLAMA_HOST` (default `http://localhost:11434`)
   - `OLLAMA_MODEL` (default `qwen2.5:7b`)
   - `OLLAMA_NUM_CTX` (context window; default `8192`)
   This variant does not use any API key or proxy settings — Ollama runs locally.
4. Initialize session (first-time login to Gemini web — unchanged from src):
   ```bash
   python login.py
   ```
   This creates `auth_state.json` used by the scraper.
5. Run the pipeline:
   ```bash
   python code.py
   ```

Notes
- The scraping portion is identical and still logs into Gemini web (Playwright + `auth_state.json`) to extract conversations.
- The formatting/graph-building step runs locally via Ollama's REST API (no remote API costs, and the formatting step works offline once the model is pulled).
- The offline variant is ideal if you want to avoid API keys or run the formatting privately, but expectations for output quality and speed should be set according to your local model (qwen2.5:7b[...]

---

## 📺 Tutorial & Documentation

For a complete step-by-step guide on how to set up and use **NeuralMind Scraper**, watch our comprehensive tutorial:

**🎥 [NeuralMind Scraper - Complete Setup & Usage Guide](https://youtu.be/kgay4cizOwI)** [![Watch on YouTube](images/thumbnail.png)](https://youtu.be/kgay4cizOwI "NeuralMind Scraper - Complete Setup & Usage Guide")



---

## 🚀 Roadmap & Future Updates

The project is continuously evolving. Planned features for upcoming releases include:

- [ ] **Direct Zotero Integration:** Develop a script to identify scientific papers discussed in chats and link them to a Zotero database.
- [ ] **Multi-Platform Support:** Extend the scraper to extract and unify chat data from ChatGPT and Claude.
- [ ] **Automated Headless Execution (Cronjob):** Enable Windows Task Scheduler integration for background, headless synchronization of the knowledge graph every few days.
- [ ] **Vector Embedding Generation:** Convert Markdown notes into mathematical vectors using embedding models to build a semantic search and chat system within Obsidian (RAG System).
- [ ] **Native Obsidian Plugin:** Transform the Python script into a native Obsidian plugin for seamless user accessibility.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!  
Feel free to check the [issues page](https://github.com/Metisa811/Gemini2Obsidian/issues) for open tasks or to propose new ideas.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

**Built for researchers, developers, and knowledge enthusiasts.**
