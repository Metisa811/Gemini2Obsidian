import os
import time
import json
import re
from playwright.sync_api import sync_playwright
from google import genai

# ==========================================
# 1. LOAD CONFIGURATION FROM CONFIG FILE
# ==========================================
try:
    import config
    API_KEY = config.API_KEY
    USE_PROXY = getattr(config, 'USE_PROXY', False)
    HTTP_PROXY = getattr(config, 'HTTP_PROXY', "")
    HTTPS_PROXY = getattr(config, 'HTTPS_PROXY', "")
except ImportError:
    print("⚠️ Error: config.py file not found!")
    print("Please create a config.py file alongside this script.")
    exit()

if USE_PROXY and HTTP_PROXY and HTTPS_PROXY:
    os.environ["HTTP_PROXY"] = HTTP_PROXY
    os.environ["HTTPS_PROXY"] = HTTPS_PROXY
    os.environ["http_proxy"] = HTTP_PROXY
    os.environ["https_proxy"] = HTTPS_PROXY
    print("🛡️ Network: Proxy successfully applied.")
else:
    print("🌐 Network: Direct connection (no proxy).")

# ==========================================
# 2. PHASE 1: CHAT EXTRACTION ENGINE
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
        
        print("🔍 Scanning chat list... (Open sidebar if closed)")
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
            
            # Check previous message count for smart update (Delta Sync)
            old_msg_count = 0
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_msg_count = len(json.load(f).get("messages", []))
                except:
                    pass
            
            print(f"\n⬇️ [{index+1}/{len(chat_links)}] Extracting chat: {url}")
            try:
                page.goto(url)
                time.sleep(4)
                
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
                        let blocks = document.querySelectorAll('user-query, model-response, [class*="message-content"]');
                        blocks.forEach(el => {
                            let role = (el.tagName.toLowerCase().includes('user') || el.className.includes('user')) ? 'user' : 'model';
                            let text = el.innerText || el.textContent;
                            if(text.trim()) data.push({ role: role, text: text.trim() });
                        });
                        return data.filter((v,i,a)=>a.findIndex(v2=>(v2.text===v.text))===i);
                    }
                """)
                
                new_msg_count = len(chat_data["messages"])
                
                if new_msg_count == old_msg_count and old_msg_count > 0:
                    print(f"   ⏭️ No new messages added (count: {new_msg_count}). Skipping...")
                    continue
                elif new_msg_count > 0:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(chat_data, f, ensure_ascii=False, indent=4)
                    
                    if old_msg_count > 0:
                        print(f"   🔄 Updated! (Old messages: {old_msg_count} -> New: {new_msg_count})")
                    else:
                        print(f"   💾 New chat saved successfully.")
                else:
                    print(f"   ❌ No messages found!")

            except Exception as e:
                print(f"   ⚠️ Extraction error: {e}")
                continue

        browser.close()
        return True

# ==========================================
# 3. PHASE 2 & 3: CASCADING GRAPH (Auto-generate parent and child nodes)
# ==========================================
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
        replacement = f"```{match[0]}\n{match[1]}\n```\n{link}"
        clean_text = clean_text.replace(f"```{match[0]}\n{match[1]}```", replacement, 1)
        
    return clean_text

def build_smart_graph_and_format():
    input_dir = "gemini_chats_json"
    output_graph = "NeuralMind_Graph"
    output_codes = os.path.join(output_graph, "Extracted_Codes")
    
    os.makedirs(output_graph, exist_ok=True)
    os.makedirs(output_codes, exist_ok=True)
    
    if not os.path.exists(input_dir): return
    
    files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    print(f"\n🧠 [Phase 2 & 3] Building cascading graph (Chat -> Sub-Domain -> Domain)...")
    
    client = genai.Client(api_key=API_KEY)
    
    all_titles = []
    for f in files:
        with open(os.path.join(input_dir, f), 'r', encoding='utf-8') as jf:
            t = json.load(jf).get("title", "Untitled").replace("/", "-").replace(":", "-").replace("|", "-")
            all_titles.append(t)
    
    for index, filename in enumerate(files):
        filepath = os.path.join(input_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        title = data.get("title", "Untitled").replace("/", "-").replace(":", "-").replace("|", "-")
        url = data.get('url', '')
        md_filepath = os.path.join(output_graph, f"{title}.md")
        
        # Check to save time
        if os.path.exists(md_filepath):
            if os.path.getmtime(filepath) <= os.path.getmtime(md_filepath):
                print(f"   ⏭️ Node '{title}' is up to date. Skipping...")
                continue
        
        other_titles = [t for t in all_titles if t != title]
        other_titles_str = "\n".join([f"- {t}" for t in other_titles]) if other_titles else "No other chats available."

        raw_chat_string = ""
        for msg in data.get("messages", []):
            role_name = "User" if msg.get("role") == "user" else "AI"
            raw_chat_string += f"[{role_name}]:\n{msg.get('text', '')}\n\n"

        # Prompt with strict domain list control (History added)
        prompt = f"""
        You are an expert at formatting Markdown and LaTeX for Obsidian software.
        I will provide a raw scraped conversation between a User and an AI.

        YOUR TASK:
        1. Reconstruct the conversation perfectly. Use "🧑 **You:**" for the user and "🤖 **Model:**" for the AI.
        2. CONTEXTUAL MATH FIX: Convert ANY mathematical/physical formulas into PERFECT standard LaTeX (`$formula$` or `$$\nformula\n$$`).
        3. STRICT CODE BLOCK RECONSTRUCTION: You MUST wrap all programming scripts/code in standard Markdown fences (```python ... ```).
        4. Remove annoying web UI artifacts.
        
        5. HIERARCHICAL KNOWLEDGE GRAPH (STRICT RULES):
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
        
        > 📂 **Sub-domain (Specialized Topic):** [[Sub-Domain]]
        > 🔗 **Related Chats:** [[Selected Title 1]] [[Selected Title 2]]
        
        ---
        
        [Put The Formatted Conversation Here]
        
        RAW TEXT TO PROCESS:
        {raw_chat_string[:25000]}
        """
        
        for attempt in range(5):
            try:
                # Using the requested model
                response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=prompt,
                )
                
                ai_formatted_md = response.text.strip()
                if ai_formatted_md.startswith("```markdown"): 
                    ai_formatted_md = ai_formatted_md[11:]
                elif ai_formatted_md.startswith("```"): 
                    ai_formatted_md = ai_formatted_md[3:]
                
                if ai_formatted_md.endswith("```"): 
                    ai_formatted_md = ai_formatted_md[:-3]
                    
                ai_formatted_md = ai_formatted_md.strip()
                
                # --- Extract metadata and physically create parent and child nodes ---
                domain_match = re.search(r'domain:\s*([^\n\r]+)', ai_formatted_md)
                sub_domain_match = re.search(r'sub_domain:\s*([^\n\r]+)', ai_formatted_md)
                
                domain_name = domain_match.group(1).strip().replace('[', '').replace(']', '') if domain_match else "Uncategorized"
                sub_domain_name = sub_domain_match.group(1).strip().replace('[', '').replace(']', '') if sub_domain_match else "General"
                
                # Clean invalid characters for filenames
                domain_name = re.sub(r'[\\/*?:"<>|]', "", domain_name)
                sub_domain_name = re.sub(r'[\\/*?:"<>|]', "", sub_domain_name)
                
                # Fix: Create node files in NeuralMind_Graph folder physically
                domain_file_path = os.path.join(output_graph, f"{domain_name}.md")
                if not os.path.exists(domain_file_path):
                    with open(domain_file_path, 'w', encoding='utf-8') as df:
                        df.write(f"---\ntype: domain\n---\n# {domain_name}\n\n> 🌌 **Mother Node (Main Branch)**\n")
                        
                sub_domain_file_path = os.path.join(output_graph, f"{sub_domain_name}.md")
                if not os.path.exists(sub_domain_file_path):
                    with open(sub_domain_file_path, 'w', encoding='utf-8') as sdf:
                        sdf.write(f"---\ntype: sub_domain\n---\n# {sub_domain_name}\n\n> 🌌 **Parent (Reference):** [[{domain_name}]]\n")

                # Extract code blocks and save chat markdown file
                final_md_content = extract_code_blocks(ai_formatted_md, title, output_codes)
                
                with open(md_filepath, 'w', encoding='utf-8') as md_file:
                    md_file.write(final_md_content)
                    
                print(f"   ✅ Node '{title}' connected to [{sub_domain_name} -> {domain_name}] successfully created.")
                break 
                
            except Exception as e:
                if '503' in str(e) or '429' in str(e):
                    wait_time = 15 + (attempt * 5)
                    print(f"   ⏳ Server busy. Retrying ({attempt+1}/5) after {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"   ⚠️ Model communication error (model may be unavailable): {e}")
                    break
        
        if index < len(files) - 1:
            time.sleep(15)

# ==========================================
if __name__ == "__main__":
    print("🚀 Starting cascading graph construction (Hierarchy Rebuild)...")
    if extract_chats():
        build_smart_graph_and_format()
        print("\n🎉 Your Obsidian graph has been successfully rebuilt and networked.")
