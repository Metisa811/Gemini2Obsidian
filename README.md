# 🧠 NeuralMind Scraper 🕸️

**An advanced automation, extraction, and hierarchical knowledge graph construction pipeline for AI chat conversations (Google Gemini) — purpose-built for Obsidian.**

**NeuralMind Scraper** is far more than a simple web scraper. It's a complete data pipeline that takes raw, unstructured web conversations and transforms them — using the power of natural language processing — into structured, interconnected, and scientifically formatted notes ready for research, development, and knowledge management.

---

## ✨ Key Features & Achievements

The project tackles complex data engineering and web extraction challenges with robust, production-grade solutions:

- **Surgical LaTeX Extraction (Deep LaTeX Restoration):** Bypasses the layered visual structure of the web (DOM) by injecting custom JavaScript to extract pure KaTeX source code. Ensures even the most complex physics and mathematics equations are rendered flawlessly in Obsidian with standardized `$$LaTeX$$` formatting.
- **Hierarchical Knowledge Graph Architecture:** Leverages the `gemini-2.5-flash` model as a "Knowledge Architect." Each chat is intelligently parsed and mapped to a **parent node (Domain)** (e.g., Physics, Programming) and multiple **child nodes (Concepts)**, creating a well-organized, clustered knowledge network.
- **Automatic Code Block Isolation:** Automatically identifies programming code blocks, separates them from chat text, and saves them as standalone physical files (`.py`, `.tex`, `.m`) with internal Obsidian links (`[[Link]]`) embedded in the main Markdown note.
- **Intelligent Session Management & Anti-Ban Protection:** Stores user sessions in `auth_state.json` for seamless automatic login. Utilizes Playwright's anti-bot headers and proxy tunneling to prevent `403 Forbidden` errors.
- **Exponential Backoff Retry System:** Intelligently handles Google API traffic issues (`429` and `503` errors) with an exponential backoff mechanism, ensuring stability and resilience during heavy processing loads.

---

## 🏗️ System Architecture (How It Works)

The project operates in three distinct but interconnected pipeline phases:

### 🌐 Phase 1: Raw Extraction Engine (Web Scraper)
Using `Playwright`, the bot launches a browser, logs in with the stored session, and extracts chat links. An injected JavaScript script traverses the nested HTML tags to extract messages, stripping away UI clutter, and outputs raw JSON files.

### 🧹 Phase 2: Primary Text Sanitization (Text Sanitizer)
A Python script processes the JSON files, removing hidden web characters (zero-width spaces), redundant words (e.g., "Gemini said"), and irregular line breaks using advanced Regex patterns.

### 🧠 Phase 3: AI-Powered Processing (AI Formatter & Graph Engine)
The cleaned text is sent to the Gemini API. Using an engineered prompt, the AI restructures the content, corrects LaTeX formulas, preserves code blocks, and injects YAML frontmatter metadata — including Domain and Concepts — to establish the knowledge graph structure.

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

### 3. Configure API Key
Edit `src/config.py` and add your API key from Google AI Studio:
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

### 5. Run the Core Pipeline
```bash
python code.py
```

---

## 📺 Tutorial & Documentation

For a complete step-by-step guide on how to set up and use **NeuralMind Scraper**, watch our comprehensive tutorial:

**🎥 [NeuralMind Scraper - Complete Setup & Usage Guide](soon)**

> *Replace `YOUR_TUTORIAL_LINK` with the actual YouTube video URL*

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
