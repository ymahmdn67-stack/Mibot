"""
حل reCAPTCHA v2 Invisible باستخدام Playwright
يقوم باعتراض طلبات الشبكة واستخراج التوكن تلقائياً
"""

import asyncio
import re
from playwright.async_api import async_playwright


class RecaptchaSolver:
    def __init__(self):
        self.token = None
        self.captured_responses = []

    async def intercept_response(self, response):
        """اعتراض الاستجابات والبحث عن توكن reCAPTCHA"""
        try:
            # البحث عن طلبات reCAPTCHA
            if "recaptcha" in response.url and "reload" in response.url:
                print(f"[*] تم اعتراض طلب: {response.url}")
                
                # محاولة الحصول على نص الاستجابة
                try:
                    body = await response.text()
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

    async def solve(self, url: str, timeout: int = 30):
        """
        حل reCAPTCHA على الموقع المحدد
        
        Args:
            url: رابط الموقع الذي يحتوي على reCAPTCHA
            timeout: مدة الانتظار بالثواني
        
        Returns:
            التوكن المستخرج أو None
        """
        async with async_playwright() as p:
            # تشغيل المتصفح
            browser = await p.chromium.launch(headless=False)
            
            # إنشاء صفحة جديدة
            page = await browser.new_page()
            
            # اعتراض جميع الاستجابات
            page.on("response", self.intercept_response)
            
            print(f"[*] جاري فتح الموقع: {url}")
            
            try:
                # الذهاب للموقع
                await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
                
                print("[*] جاري الانتظار لالتقاط التوكن...")
                
                # الانتظار لاستخراج التوكن
                start_time = asyncio.get_event_loop().time()
                while self.token is None:
                    await asyncio.sleep(0.5)
                    
                    # التحقق من انقضاء المهلة الزمنية
                    elapsed = asyncio.get_event_loop().time() - start_time
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
                await browser.close()


async def main():
    """الدالة الرئيسية"""
    solver = RecaptchaSolver()
    
    # الموقع المستهدف
    target_url = "https://greenmethods.com/my-account/"
    
    print("=" * 60)
    print("حل reCAPTCHA v2 Invisible باستخدام Playwright")
    print("=" * 60)
    print()
    
    # حل الكابتشا
    token = await solver.solve(target_url, timeout=30)
    
    if token:
        print("\n" + "=" * 60)
        print("النتيجة النهائية:")
        print("=" * 60)
        print(f"TOKEN = {token}")
        print("=" * 60)
    else:
        print("\n[✗] فشل الحل")


if __name__ == "__main__":
    asyncio.run(main())
