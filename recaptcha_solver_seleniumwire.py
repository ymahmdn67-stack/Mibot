"""
محلّل reCAPTCHA - نسخة محسّنة باعتماد مكتبة Selenium-Wire

لماذا selenium-wire؟
    - تحافظ على نفس مبدأ النسخة الأصلية تماماً: "اعتراض حركة الشبكة" وقراءة الاستجابات.
    - تدمج الوكيل (Proxy) داخلياً وتحقن شهادة SSL تلقائياً، فلا تظهر مشكلة
      "جاري الالتقاط بلا نتيجة" التي كانت بسبب عدم مرور المتصفح عبر وكيل mitmproxy
      وعدم تثبيت الشهادة.
    - لا حاجة لضبط أي إعداد وكيل يدوي ولا تثبيت شهادات.

المتطلبات:
    pip install selenium-wire blinker==1.7.0
    # ويتطلب متصفح Chrome مثبتاً (يُدار chromedriver تلقائياً في الإصدارات الحديثة)
"""

import re
import gzip
import time
import argparse

from seleniumwire import webdriver  # اعتراض الشبكة مدمج هنا
from selenium.webdriver.chrome.options import Options


def extract_token(body: str):
    """نفس منطق النسخة الأصلية لاستخراج التوكن من جسم الاستجابة."""
    m = re.search(r'\["rresp","(.*?)",null', body)
    return m.group(1) if m else None


def main():
    parser = argparse.ArgumentParser(description="reCAPTCHA Token Solver (Selenium-Wire)")
    parser.add_argument("--url", default="https://greenmethods.com/my-account/",
                        help="الرابط المستهدف")
    parser.add_argument("--timeout", type=int, default=120,
                        help="أقصى مدة انتظار للتوكن بالثواني")
    parser.add_argument("--headless", action="store_true",
                        help="تشغيل المتصفح بدون واجهة (قد يقل معدل النجاح مع reCAPTCHA)")
    args = parser.parse_args()

    chrome_options = Options()
    if args.headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # selenium-wire يدير الوكيل والشهادة داخلياً، لا حاجة لأي إعداد إضافي
    driver = webdriver.Chrome(options=chrome_options)

    print(f"[+] فتح الصفحة: {args.url}")
    driver.get(args.url)
    print("[*] جاري الانتظار لالتقاط التوكن...")

    token = None
    deadline = time.time() + args.timeout
    seen = 0
    try:
        while token is None and time.time() < deadline:
            # نفس مبدأ النسخة الأصلية: مراقبة طلبات reCAPTCHA reload
            for request in driver.requests[seen:]:
                seen = len(driver.requests)
                if request.response and (
                    "recaptcha/enterprise/reload" in request.url
                    or "recaptcha/api2/reload" in request.url
                ):
                    raw_body = request.response.body
                    try:
                        body = gzip.decompress(raw_body).decode("utf-8", errors="ignore")
                    except Exception:
                        body = raw_body.decode("utf-8", errors="ignore")

                    token = extract_token(body)
                    if token:
                        break
            time.sleep(1)

        if token:
            print("\n[+] تم الالتقاط بنجاح!")
            print("TOKEN =", token)
        else:
            print("\n[-] انتهت المهلة دون التقاط أي توكن.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
