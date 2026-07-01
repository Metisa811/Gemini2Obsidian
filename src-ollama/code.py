import os
import time
import json
import re
import hashlib
import requests
from playwright.sync_api import sync_playwright

# ==========================================
# 1. Load Configuration
# ==========================================
try:
    import config
    OLLAMA_HOST = getattr(config, 'OLLAMA_HOST', "http://localhost:11434")
    OLLAMA_MODEL = getattr(config, 'OLLAMA_MODEL', "qwen2.5:7b")
    OLLAMA_NUM_CTX = getattr(config, 'OLLAMA_NUM_CTX', 8192)
except ImportError:
    print("⚠️ Error: config.py not found!")
    print("Please create config.py in the same directory.")
    exit()

print(f"🦙 Using local Ollama at {OLLAMA_HOST} with model '{OLLAMA_MODEL}'")

# ==========================================
# 2. Phase 1: Chat Extraction Engine (Deep Delta Sync)
# ==========================================
def extract_chats():
    output_dir = "gemini_chats_json"
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, 
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        try:
            context = browser.new_context(
                storage_state="auth_state.json",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
        except Exception:
            print("❌ Error reading auth_state.json! Please run the login script first.")
            return False
            
        page = context.new_page()
        print("   [Phase 1] Navigating to Gemini main panel...")
        page.goto("https://gemini.google.com/")
        page.wait_for_load_state("domcontentloaded")
        
        print("🔍 Scanning chat list... (Open sidebar if closed, waiting 10 seconds)")
        time.sleep(10)
        
        chat_links = page.evaluate("""
            () => {
                let links = [];
                document.querySelectorAll('a').forEach(a => {
                    let href = a.getAttribute('href');
                    if (href && href.includes('/app/') && href.split('/').length > 2) {
                        let fullUrl = href.startsWith('/') ? 'https://gemini.google.com' + href : href;
                        links.push(fullUrl);
                    }
                });
                return [...new Set(links)];
            }
        """)
                    
        print(f"✅ Found {len(chat_links)} chats!")
        
        for index, url in enumerate(chat_links):
            chat_id = url.split("/")[-1]
            file_path = os.path.join(output_dir, f"{chat_id}.json")
            path_only = url.replace("https://gemini.google.com", "")
            
            old_msg_count = 0
            old_hash = None
            old_title = None
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        _old_data = json.load(f)
                        old_msg_count = len(_old_data.get("messages", []))
                        old_hash = _old_data.get("_hash")
                        old_title = _old_data.get("title")
                except:
                    pass
            
            print(f"\n⬇️ [{index+1}/{len(chat_links)}] Extracting chat: {url}")
            try:
                # Human-like SPA Navigation: Click the sidebar link instead of hard reloading
                clicked = page.evaluate(f"""
                    () => {{
                        let el = document.querySelector('a[href="{path_only}"]');
                        if(el) {{ el.click(); return true; }}
                        return false;
                    }}
                """)
                
                if clicked:
                    print("   🖱️ Used SPA click for faster loading...")
                    try:
                        page.wait_for_function(f"window.location.href.includes('{chat_id}')", timeout=5000)
                    except:
                        pass
                else:
                    print("   🔄 Performing full page reload (Link not visible)...")
                    page.goto(url)
                
                time.sleep(4)
                
                # Wait for messages to load dynamically
                try:
                    page.wait_for_selector('user-query, model-response, [class*="message-content"], [data-test-id="chat-message"], message-content', timeout=8000)
                except:
                    print("   ⏳ Taking longer to load or might be an empty chat...")
                
                for _ in range(5):
                    page.keyboard.press("PageUp")
                    time.sleep(0.5)
                    
                chat_data = {
                    "url": url,
                    "title": page.title().replace(" - Google Gemini", ""),
                    "messages": []
                }
                
                chat_data["messages"] = page.evaluate("""
                    () => {
                        try {
                            document.querySelectorAll('.katex').forEach(el => {
                                let annotation = el.querySelector('annotation[encoding="application/x-tex"]');
                                if (annotation) {
                                    let tex = annotation.textContent;
                                    let isBlock = el.classList.contains('katex-display');
                                    let textNode = document.createTextNode(isBlock ? '\\n\\n$$' + tex + '$$\\n\\n' : ' $' + tex + '$ ');
                                    el.replaceWith(textNode);
                                }
                            });
                            
                            document.querySelectorAll('pre, [class*="code-block"], [class*="snippet"]').forEach(el => {
                                if(el.dataset.wrapped) return;
                                el.dataset.wrapped = "true";
                                let codeText = el.innerText || el.textContent;
                                let textNode = document.createTextNode('\\n\\n```\\n' + codeText.trim() + '\\n```\\n\\n');
                                el.replaceWith(textNode);
                            });
                        } catch (e) {}

                        let data = [];
                        let blocks = document.querySelectorAll('user-query, model-response, [class*="message-content"], [data-test-id="chat-message"], message-content');
                        blocks.forEach(el => {
                            let role = (el.tagName.toLowerCase().includes('user') || el.className.includes('user') || el.className.includes('query')) ? 'user' : 'model';
                            let text = el.innerText || el.textContent;
                            if(text.trim()) data.push({ role: role, text: text.trim() });
                        });
                        return data.filter((v,i,a)=>a.findIndex(v2=>(v2.text===v.text))===i);
                    }
                """)
                
                new_msg_count = len(chat_data["messages"])

                # Content hash - catches edits even when message count stays the same
                content_hash = hashlib.md5(
                    json.dumps(chat_data["messages"], ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()
                chat_data["_hash"] = content_hash

                content_changed = (old_hash != content_hash)
                title_changed = (old_title is not None and old_title != chat_data["title"])

                if new_msg_count == 0:
                    print(f"   ❌ No messages found! (Google might have blocked the layout)")
                elif not content_changed and not title_changed:
                    print(f"   ⏭️ No new content (hash unchanged). Skipping...")
                    continue
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(chat_data, f, ensure_ascii=False, indent=4)

                    if title_changed:
                        print(f"   ✏️ Title changed: '{old_title}' -> '{chat_data['title']}'")
                    if old_msg_count > 0 and content_changed:
                        print(f"   🔄 Updated! (Old count: {old_msg_count} -> New count: {new_msg_count})")
                    elif old_msg_count == 0:
                        print(f"   💾 New chat successfully saved.")

            except Exception as e:
                print(f"   ⚠️ Extraction Error: {e}")
                continue

        browser.close()
        return True

# ==========================================
# 3. Phase 2 & 3: Hierarchical Graph Builder
# ==========================================
def load_manifest(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_manifest(path, manifest):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

def add_backlink(output_graph, target_title, source_title):
    """Append a backlink to an existing (already-built) note without calling the AI again,
    so the graph stays bidirectional even when the older note isn't being regenerated."""
    target_path = os.path.join(output_graph, f"{target_title}.md")
    if not os.path.exists(target_path):
        return  # target note doesn't exist (yet) - nothing to link

    with open(target_path, 'r', encoding='utf-8') as f:
        content = f.read()

    link_line = f"- [[{source_title}]]"
    if link_line in content:
        return  # already linked, avoid duplicates

    marker = "## 🔗 Connections"
    if marker in content:
        content = content.rstrip() + f"\n{link_line}\n"
    else:
        content = content.rstrip() + f"\n\n---\n{marker}\n{link_line}\n"

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(content)

def call_ollama(prompt, host, model, num_ctx=8192, timeout=180):
    """Send a prompt to a local Ollama server and return the generated text.
    Raises an exception on connection failure or non-200 response so the
    existing retry loop in the caller can handle it.

    IMPORTANT: Ollama defaults to a 2048-token context window regardless of
    what the underlying model supports. Without setting num_ctx explicitly,
    long chats get silently truncated. We set it here so full conversations
    actually reach the model.
    """
    response = requests.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_ctx": num_ctx,
                "num_predict": 4096
            }
        },
        timeout=timeout
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")

def normalize_latex(text):
    """Obsidian only renders $...$ (inline) and $$...$$ (block) math.
    Local models like qwen2.5 are trained on OpenAI-style formatting and
    very often emit \\( ... \\) and \\[ ... \\] instead, which Obsidian
    shows as raw text. This is a safety net that runs regardless of
    whether the model followed the prompt's formatting instructions.
    """
    # Block math: \[ ... \]  ->  $$\n...\n$$  (must be on their own lines for Obsidian)
    def _block_repl(m):
        inner = m.group(1).strip()
        return f"\n$$\n{inner}\n$$\n"
    text = re.sub(r'\\\[(.*?)\\\]', _block_repl, text, flags=re.DOTALL)

    # Inline math: \( ... \)  ->  $...$
    text = re.sub(r'\\\((.*?)\\\)', lambda m: f"${m.group(1).strip()}$", text, flags=re.DOTALL)

    # Ensure existing $$ block formulas are on their own lines (Obsidian requirement) -
    # if a $$ isn't already followed/preceded by a newline, add one.
    text = re.sub(r'(?<!\n)\$\$', '\n$$', text)
    text = re.sub(r'\$\$(?!\n)', '$$\n', text)

    return text

def extract_code_blocks(text, base_filename, output_codes_dir):
    code_pattern = re.compile(r'```([a-zA-Z0-9_\+\-]*)\s*\n(.*?)```', re.DOTALL)
    matches = code_pattern.findall(text)
    clean_text = text
    
    for index, match in enumerate(matches):
        language = match[0].lower().strip() if match[0] else "txt"
        content = match[1].strip()
        
        ext = "txt"
        if language in ["python", "py"]: ext = "py"
        elif language in ["latex", "tex"]: ext = "tex"
        elif language in ["json"]: ext = "json"
        elif language in ["javascript", "js"]: ext = "js"
        elif language in ["html"]: ext = "html"
        elif language in ["cpp", "c++"]: ext = "cpp"
        
        filename = f"{base_filename}_snippet_{index+1}.{ext}"
        filepath = os.path.join(output_codes_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        link = f"\n\n📎 **Code File:** [[{filename}]]\n\n"
        
        # Safe replacement for code blocks
        original_block = f"```{match[0]}\n{match[1]}```"
        if original_block in clean_text:
            clean_text = clean_text.replace(original_block, f"```{match[0]}\n{match[1]}\n```\n{link}", 1)
        
    return clean_text

def check_ollama_ready(host, model):
    """Verify the local Ollama server is reachable and the requested model is pulled.
    Returns True/False and prints a helpful message either way."""
    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"❌ Can't reach Ollama at {host}.")
        print("   Make sure Ollama is running (e.g. run 'ollama serve' or open the Ollama app).")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama status: {e}")
        return False

    tags = resp.json().get("models", [])
    installed = [m.get("name", "") for m in tags]
    # Ollama model names sometimes include a ":latest" suffix; match loosely
    if not any(model == m or m.startswith(model + ":") or m == model for m in installed):
        print(f"❌ Model '{model}' not found in Ollama.")
        print(f"   Installed models: {installed if installed else 'none'}")
        print(f"   Run: ollama pull {model}")
        return False

    print(f"✅ Ollama is up and '{model}' is ready.")
    return True

def build_smart_graph_and_format():
    input_dir = "gemini_chats_json"
    output_graph = "NeuralMind_Graph"
    output_codes = os.path.join(output_graph, "Extracted_Codes")
    
    os.makedirs(output_graph, exist_ok=True)
    os.makedirs(output_codes, exist_ok=True)
    
    if not os.path.exists(input_dir): return

    if not check_ollama_ready(OLLAMA_HOST, OLLAMA_MODEL):
        return
    
    files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    print(f"\n🧠 [Phase 2 & 3] Building Cascading Graph (Chat -> Sub-Domain -> Domain)...")

    manifest_path = os.path.join(output_graph, "_manifest.json")
    manifest = load_manifest(manifest_path)
    
    all_titles = []
    for f in files:
        with open(os.path.join(input_dir, f), 'r', encoding='utf-8') as jf:
            t = json.load(jf).get("title", "Untitled").replace("/", "-").replace(":", "-").replace("|", "-")
            all_titles.append(t)
    
    for index, filename in enumerate(files):
        filepath = os.path.join(input_dir, filename)
        chat_id = filename[:-5]  # strip ".json"
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        title = data.get("title", "Untitled").replace("/", "-").replace(":", "-").replace("|", "-")
        url = data.get('url', '')
        md_filepath = os.path.join(output_graph, f"{title}.md")

        # Prefer the hash already computed during extraction; fall back for old json files
        chat_hash = data.get("_hash")
        if chat_hash is None:
            chat_hash = hashlib.md5(
                json.dumps(data.get("messages", []), ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()

        manifest_entry = manifest.get(chat_id)

        if (manifest_entry
                and manifest_entry.get("hash") == chat_hash
                and manifest_entry.get("title") == title
                and os.path.exists(md_filepath)):
            print(f"   ⏭️ Node '{title}' is up-to-date. Skipping...")
            continue

        # Title changed since last build -> remove the stale note so it doesn't linger as an orphan
        if manifest_entry and manifest_entry.get("title") and manifest_entry.get("title") != title:
            old_md_path = manifest_entry.get("md_file")
            if old_md_path and os.path.exists(old_md_path) and old_md_path != md_filepath:
                os.remove(old_md_path)
                print(f"   🧹 Renamed chat detected: removed stale note '{manifest_entry.get('title')}.md'")
        
        other_titles = [t for t in all_titles if t != title]
        # Cap the list so the prompt doesn't balloon as the vault grows -
        # a 7B local model has far less context budget than a hosted model.
        MAX_OTHER_TITLES = 40
        if len(other_titles) > MAX_OTHER_TITLES:
            other_titles = other_titles[:MAX_OTHER_TITLES]
        other_titles_str = "\n".join([f"- {t}" for t in other_titles]) if other_titles else "No other chats available."

        raw_chat_string = ""
        for msg in data.get("messages", []):
            role_name = "User" if msg.get("role") == "user" else "AI"
            raw_chat_string += f"[{role_name}]:\n{msg.get('text', '')}\n\n"

        # Rough budget: at 8192 ctx tokens (~4 chars/token for Latin script,
        # less for Persian/Arabic), reserve room for instructions + output.
        # Keep this conservative since qwen2.5:7b has less headroom than a hosted model.
        MAX_CHAT_CHARS = min(14000, OLLAMA_NUM_CTX * 3)
        truncated_notice = ""
        if len(raw_chat_string) > MAX_CHAT_CHARS:
            raw_chat_string = raw_chat_string[:MAX_CHAT_CHARS]
            truncated_notice = "\n\n[NOTE: Conversation was long and has been truncated to fit the model's context window.]"

        prompt = f"""
        You are an expert at formatting Markdown and LaTeX for Obsidian software.
        I will provide a raw scraped conversation between a User and an AI.

        YOUR TASK:
        1. Reconstruct the conversation perfectly. Use "🧑 **You:**" for the user and "🤖 **Model:**" for the AI.
        2. CONTEXTUAL MATH FIX: Convert ANY mathematical/physical formulas into PERFECT standard LaTeX using ONLY `$formula$` for inline and `$$\nformula\n$$` for block equations. Do NOT use `\\(...\\)` or `\\[...\\]` delimiters — Obsidian does not render those.
        3. STRICT CODE BLOCK RECONSTRUCTION: You MUST wrap all programming scripts/code in standard Markdown fences (```python ... ```).
        4. Remove annoying web UI artifacts.
        5. Do NOT add any preamble, explanation, or commentary before or after the output (e.g. do not say "Here is the formatted markdown"). Output ONLY the content in the exact format below, starting directly with "---".
        
        6. HIERARCHICAL KNOWLEDGE GRAPH (STRICT RULES):
           - [Mother Node / Domain]: Choose ONE broad domain from this EXACT list ONLY: Physics, Mathematics, Computer_Science, Chemistry, Biology, Engineering, Languages, History, Medicine, Philosophy, Arts, Uncategorized.
           - [Sub-Domain]: Generate ONE specific sub-topic (e.g., Quantum_Mechanics, Achaemenid_Empire, Linear_Algebra). Use underscores for spaces.
           - [Direct Links]: Select 1 to 3 OTHER existing chat titles that share a DEEP conceptual bond. If no strong bond exists, leave the related section EMPTY.
        
        AVAILABLE OTHER CHATS IN VAULT:
        {other_titles_str}

        OUTPUT STRICTLY IN THIS EXACT FORMAT (No markdown backticks around the output):
        ---
        type: ai_conversation
        source: {url}
        domain: [Mother Node]
        sub_domain: [Sub-Domain]
        ---
        
        # {title}
        
        > 📂 **Sub-Domain (Specific Topic):** [[Sub-Domain]]
        > 🔗 **Related Chats:** [[Selected Title 1]] [[Selected Title 2]]
        
        ---
        
        [Put The Formatted Conversation Here]
        
        RAW TEXT TO PROCESS:
        {raw_chat_string}{truncated_notice}
        """
        
        for attempt in range(5):
            try:
                ai_formatted_md = call_ollama(prompt, OLLAMA_HOST, OLLAMA_MODEL, num_ctx=OLLAMA_NUM_CTX).strip()
                if ai_formatted_md.startswith("```markdown"): 
                    ai_formatted_md = ai_formatted_md[11:]
                elif ai_formatted_md.startswith("```"): 
                    ai_formatted_md = ai_formatted_md[3:]
                
                if ai_formatted_md.endswith("```"): 
                    ai_formatted_md = ai_formatted_md[:-3]
                    
                ai_formatted_md = ai_formatted_md.strip()

                if not ai_formatted_md:
                    raise ValueError("Empty response from model")

                # Fix math delimiters qwen2.5 tends to emit (\( \), \[ \]) so Obsidian
                # actually renders them as LaTeX instead of showing raw text.
                ai_formatted_md = normalize_latex(ai_formatted_md)
                
                # Metadata extraction and creating mother/child nodes physically
                domain_match = re.search(r'domain:\s*([^\n\r]+)', ai_formatted_md)
                sub_domain_match = re.search(r'sub_domain:\s*([^\n\r]+)', ai_formatted_md)
                
                domain_name = domain_match.group(1).strip().replace('[', '').replace(']', '') if domain_match else "Uncategorized"
                sub_domain_name = sub_domain_match.group(1).strip().replace('[', '').replace(']', '') if sub_domain_match else "General"
                
                domain_name = re.sub(r'[\\/*?:"<>|]', "-", domain_name)
                sub_domain_name = re.sub(r'[\\/*?:"<>|]', "-", sub_domain_name)
                
                domain_file_path = os.path.join(output_graph, f"{domain_name}.md")
                if not os.path.exists(domain_file_path):
                    with open(domain_file_path, 'w', encoding='utf-8') as df:
                        df.write(f"---\ntype: domain\n---\n# {domain_name}\n\n> 🌌 **Domain (Mother Node)**\n")
                        
                sub_domain_file_path = os.path.join(output_graph, f"{sub_domain_name}.md")
                if not os.path.exists(sub_domain_file_path):
                    with open(sub_domain_file_path, 'w', encoding='utf-8') as sdf:
                        sdf.write(f"---\ntype: sub_domain\n---\n# {sub_domain_name}\n\n> 🌌 **Mother Node:** [[{domain_name}]]\n")

                final_md_content = extract_code_blocks(ai_formatted_md, title, output_codes)
                
                with open(md_filepath, 'w', encoding='utf-8') as md_file:
                    md_file.write(final_md_content)

                # --- Bidirectional linking ---
                # Add a backlink on each related chat's note so the graph isn't one-directional.
                # This is a direct file append (no extra API call), so it also works for older
                # notes that won't be regenerated by the AI this run.
                related_match = re.search(r'Related Chats:\*\*\s*(.*)', ai_formatted_md)
                if related_match:
                    related_titles = re.findall(r'\[\[([^\]]+)\]\]', related_match.group(1))
                    for related_title in related_titles:
                        related_title = related_title.strip()
                        if related_title and related_title != title:
                            add_backlink(output_graph, related_title, title)

                # Persist this chat's build state so future runs can skip it accurately
                manifest[chat_id] = {"title": title, "hash": chat_hash, "md_file": md_filepath}
                save_manifest(manifest_path, manifest)
                    
                print(f"   ✅ Node '{title}' connected to [{sub_domain_name} -> {domain_name}] created successfully.")
                break 
                
            except requests.exceptions.ConnectionError:
                print(f"   ⏳ Can't reach Ollama at {OLLAMA_HOST}. Is 'ollama serve' running? Retrying ({attempt+1}/5) in 10 seconds...")
                time.sleep(10)
            except requests.exceptions.Timeout:
                print(f"   ⏳ Ollama took too long to respond. Retrying ({attempt+1}/5)...")
                time.sleep(5)
            except Exception as e:
                print(f"   ⚠️ Model Communication Error: {e}")
                break
        
        if index < len(files) - 1:
            time.sleep(1)

# ==========================================
if __name__ == "__main__":
    print("🚀 Starting cascading graph construction (Hierarchy Rebuild)...")
    if extract_chats():
        build_smart_graph_and_format()
        print("\n🎉 Obsidian graph successfully rebuilt and networked.")
