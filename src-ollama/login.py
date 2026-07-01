import time
from playwright.sync_api import sync_playwright

def renew_auth_state():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        page.goto("https://gemini.google.com/")
        
        print("\n" + "="*50)
        print("1. In the opened browser window, log in to your account.")
        print("2. After successfully logging in and seeing the Gemini dashboard, return to this terminal.")
        print("3. Press Enter to save the new session.")
        print("="*50 + "\n")
        
        input("After logging in, press Enter here to save the session file...")
        
        context.storage_state(path="auth_state.json")
        print("✅ Your new session has been successfully updated.")
        
        browser.close()

if __name__ == "__main__":
    renew_auth_state()
