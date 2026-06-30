"""
حل reCAPTCHA v2 Invisible باستخدام Playwright (نسخة متزامنة)
يقوم باعتراض طلبات الشبكة واستخراج التوكن تلقائياً
يعمل في بيئة Codespaces وLinux بوضع headless
"""

import re
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright


def install_browser():
    """تثبيت متصفح Chromium تلقائياً إذا لم يكن موجوداً"""
    print("[*] جاري التحقق من وجود المتصفح وتثبيته إن لزم...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[✓] المتصفح جاهز للاستخدام")
        else:
            print(f"[!] تحذير أثناء التثبيت: {result.stderr[:200]}")
    except Exception as e:
        print(f"[!] خطأ في تثبيت المتصفح: {e}")


class RecaptchaSolver:
    def __init__(self):
        self.token = None
        self.captured_responses = []

    def intercept_response(self, response):
        """اعتراض الاستجابات والبحث عن توكن reCAPTCHA"""
        try:
            # البحث عن طلبات reCAPTCHA
            if "recaptcha" in response.url and "reload" in response.url:
                print(f"[*] تم اعتراض طلب: {response.url}")
                
                # محاولة الحصول على نص الاستجابة
                try:
                    body = response.text()
                    self.captured_responses.append({
                        'url': response.url,
                        'body': body[:500]  # أول 500 حرف
                    })
                    
                    # البحث عن التوكن باستخدام regex
                    # للبحث عن: ["rresp","TOKEN_HERE",null
                    match = re.search(r'\["rresp","([^"]+)"', body)
                    
                    if match:
                        self.token = match.group(1)
                        print(f"[✓] تم استخراج التوكن: {self.token[:50]}...")
                        return True
                    
                    # محاولة بحث بديلة
                    if '"rresp"' in body:
                        print(f"[!] وجدت 'rresp' في الاستجابة لكن لم أتمكن من استخراج التوكن")
                        print(f"[!] محتوى الاستجابة: {body[:300]}")
                        
                except Exception as e:
                    print(f"[!] خطأ في قراءة الاستجابة: {e}")
                    
        except Exception as e:
            print(f"[!] خطأ في اعتراض الاستجابة: {e}")

    def solve(self, url: str, timeout: int = 30):
        """
        حل reCAPTCHA على الموقع المحدد
        
        Args:
            url: رابط الموقع الذي يحتوي على reCAPTCHA
            timeout: مدة الانتظار بالثواني
        
        Returns:
            التوكن المستخرج أو None
        """
        with sync_playwright() as p:
            # تشغيل المتصفح بوضع headless للعمل في Codespaces/Linux
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            
            # إنشاء صفحة جديدة
            page = browser.new_page()
            
            # اعتراض جميع الاستجابات
            page.on("response", self.intercept_response)
            
            print(f"[*] جاري فتح الموقع: {url}")
            
            try:
                # الذهاب للموقع
                page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
                
                print("[*] جاري الانتظار لالتقاط التوكن...")
                
                # الانتظار لاستخراج التوكن
                start_time = time.time()
                while self.token is None:
                    time.sleep(0.5)
                    
                    # التحقق من انقضاء المهلة الزمنية
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        print(f"[✗] انقضت مهلة الانتظار ({timeout}s) ولم يتم استخراج التوكن")
                        break
                
                if self.token:
                    print(f"\n[✓] تم الالتقاط بنجاح!")
                    print(f"[✓] TOKEN = {self.token}")
                    
                    # طباعة الاستجابات المعترضة للمرجعية
                    if self.captured_responses:
                        print(f"\n[*] عدد الطلبات المعترضة: {len(self.captured_responses)}")
                        for i, resp in enumerate(self.captured_responses, 1):
                            print(f"\n[{i}] URL: {resp['url']}")
                            print(f"    Body: {resp['body'][:200]}...")
                    
                    return self.token
                else:
                    print("[✗] فشل استخراج التوكن")
                    if self.captured_responses:
                        print(f"[!] تم اعتراض {len(self.captured_responses)} طلب(ات) لكن لم يتم العثور على التوكن")
                    return None
                    
            except Exception as e:
                print(f"[✗] خطأ: {e}")
                return None
            finally:
                browser.close()


def main():
    """الدالة الرئيسية"""
    # تثبيت المتصفح تلقائياً عند الحاجة
    install_browser()

    solver = RecaptchaSolver()
    
    # الموقع المستهدف
    target_url = "https://greenmethods.com/my-account/"
    
    print("=" * 60)
    print("حل reCAPTCHA v2 Invisible باستخدام Playwright")
    print("=" * 60)
    print()
    
    # حل الكابتشا
    token = solver.solve(target_url, timeout=30)
    
    if token:
        print("\n" + "=" * 60)
        print("النتيجة النهائية:")
        print("=" * 60)
        print(f"TOKEN = {token}")
        print("=" * 60)
    else:
        print("\n[✗] فشل الحل")


if __name__ == "__main__":
    main()
