"""
محلّل reCAPTCHA - نسخة متوافقة مع Python 3.12 (بدون مشاكل pkg_resources)

الفكرة:
    تحافظ على مبدأ "اعتراض الشبكة" الأصلي، لكن بدل وكيل mitmproxy الخارجي،
    تستخدم بروتوكول Chrome DevTools (CDP) المدمج في المتصفح عبر Selenium الرسمي.
    المتصفح نفسه يبلّغنا بكل استجابات الشبكة، فلا حاجة لوكيل خارجي ولا شهادة SSL،
    وهذا يحل سبب "جاري الالتقاط بلا نتيجة".

لماذا هذه أفضل من selenium-wire؟
    selenium-wire لم يعد مُصاناً ويتعطّل على Python 3.12 بخطأ:
        ModuleNotFoundError: No module named 'pkg_resources'
    أما Selenium الرسمي فمدعوم رسمياً ويعمل على Python 3.12 دون مشاكل.

المتطلبات:
    pip install selenium
    # Selenium 4.6+ يدير تنزيل chromedriver تلقائياً، ويتطلب متصفح Chrome مثبتاً.
"""

import re
import json
import time
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def extract_token(text: str):
    """نفس منطق النسخة الأصلية لاستخراج التوكن."""
    m = re.search(r'\["rresp","(.*?)",null', text)
    return m.group(1) if m else None


def main():
    parser = argparse.ArgumentParser(description="reCAPTCHA Token Solver (CDP)")
    parser.add_argument("--url", default="https://greenmethods.com/my-account/",
                        help="الرابط المستهدف")
    parser.add_argument("--timeout", type=int, default=120,
                        help="أقصى مدة انتظار للتوكن بالثواني")
    parser.add_argument("--headless", action="store_true",
                        help="تشغيل بدون واجهة (قد يقل النجاح مع reCAPTCHA)")
    args = parser.parse_args()

    options = Options()
    if args.headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # تفعيل سجل الأداء لالتقاط أحداث الشبكة عبر CDP
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)

    # تفعيل اعتراض الشبكة عبر CDP
    driver.execute_cdp_cmd("Network.enable", {})

    print(f"[+] فتح الصفحة: {args.url}")
    driver.get(args.url)
    print("[*] جاري الانتظار لالتقاط التوكن...")

    token = None
    deadline = time.time() + args.timeout
    try:
        while token is None and time.time() < deadline:
            logs = driver.get_log("performance")
            for entry in logs:
                try:
                    msg = json.loads(entry["message"])["message"]
                except Exception:
                    continue

                if msg.get("method") != "Network.responseReceived":
                    continue

                params = msg.get("params", {})
                url = params.get("response", {}).get("url", "")
                if "recaptcha/enterprise/reload" in url or "recaptcha/api2/reload" in url:
                    request_id = params.get("requestId")
                    try:
                        # جلب جسم الاستجابة عبر CDP (لا حاجة لفك Gzip يدوياً، CDP يعيده نصاً)
                        body = driver.execute_cdp_cmd(
                            "Network.getResponseBody", {"requestId": request_id}
                        )
                        text = body.get("body", "")
                        token = extract_token(text)
                        if token:
                            break
                    except Exception:
                        # قد لا يكون الجسم جاهزاً بعد، نتجاهل ونعيد المحاولة
                        continue
            time.sleep(1)

        if token:
            print("\n[+] تم الالتقاط بنجاح!")
            print("TOKEN =", token)
        else:
            print("\n[-] انتهت المهلة دون التقاط أي توكن.")
            print("    تأكد من ظهور/تفعيل reCAPTCHA في الصفحة.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
