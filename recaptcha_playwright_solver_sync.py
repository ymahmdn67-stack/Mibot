import threading
import time
import re
from playwright.sync_api import sync_playwright

TOKEN = None

def watch():
    global TOKEN

    def on_response(response):
        global TOKEN
        if "recaptcha" in response.url and "reload" in response.url:
            try:
                body = response.text()
                m = re.search(r'\["rresp","(.*?)",null', body)
                if m:
                    TOKEN = m.group(1)
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = browser.new_page()
        page.on("response", on_response)
        page.goto("https://greenmethods.com/my-account/", wait_until="networkidle")

        while TOKEN is None:
            time.sleep(0.5)

        browser.close()


threading.Thread(target=watch, daemon=True).start()
print("جاري الانتظار لالتقاط التوكن...")
while TOKEN is None:
    time.sleep(1)

print("\nتم الالتقاط بنجاح!")
print("TOKEN =", TOKEN)
