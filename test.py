import re
import asyncio
import json
from faker import Faker
from curl_cffi.requests import AsyncSession

fake = Faker("en_UK")

f = fake.first_name()
l = fake.last_name()
k = f"{f} {l}"
e = f"{f.lower()}.{l.lower()}@gmail.com"


async def main():
    """
    استخدام جلسة واحدة لجميع الطلبات
    الكوكيز تُدار تلقائياً بين الطلبات
    """
    
    # إنشاء جلسة واحدة تُستخدم لجميع الطلبات
    async with AsyncSession(
        impersonate="chrome139",
        timeout=30
    ) as session:
        
        try:
            # ===== الطلب الأول: الحصول على الصفحة الأولى والحصول على nonce =====
            url = "https://greenmethods.com/my-account/"
            
            headers = {
                "authority": "greenmethods.com",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-language": "ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7",
                "cache-control": "max-age=0",
                "referer": "https://greenmethods.com/my-account/edit-address/billing/",
                "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            }
            
            response = await session.request(
                method="GET",
                url=url,
                headers=headers,
                # لا حاجة لتمرير cookies - الجلسة تديرها تلقائياً
            )
            
            # استخراج nonce من الاستجابة
            nonce_match = re.search(
                r'name="woocommerce-register-nonce" value="([^"]+)"',
                response.text
            )
            
            if not nonce_match:
                print("خطأ: لم يتم العثور على nonce")
                return
            
            nonce = nonce_match.group(1)
            
            # ===== الطلب الثاني: الحصول على reCAPTCHA token =====
            headers_anchor = {
                'authority': 'www.google.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                'referer': 'https://greenmethods.com/',
                'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'iframe',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'cross-site',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                'x-client-data': 'CMDjygE=',
            }
            
            params_anchor = {
                'ar': '1',
                'k': '6LfYpL0qAAAAAJWUdG9Nki8FBm9H4EZfGhdxLAyU',
                'co': 'aHR0cHM6Ly9ncmVlbm1ldGhvZHMuY29tOjQ0Mw..',
                'hl': 'ar',
                'v': 'MerVUtRoajKEbP7pLiGXkL28',
                'size': 'invisible',
                'anchor-ms': '20000',
                'execute-ms': '30000',
                'cb': None,
            }
            
            response_anchor = await session.get(
                'https://www.google.com/recaptcha/api2/anchor',
                params=params_anchor,
                headers=headers_anchor,
            )
            
            match_token = re.search(r'id="recaptcha-token"\s+value="([^"]+)"', response_anchor.text)
            c = match_token.group(1) if match_token else None
            
            cap = None
            if c:
                # ===== الطلب الثالث: الحصول على reCAPTCHA response =====
                headers_reload = {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
                    "Accept": "*/*",
                    "Accept-Language": "fa,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
                    "Connection": "keep-alive",
                    "Origin": "https://www.google.com",
                    "Referer": "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6LfYpL0qAAAAAJWUdG9Nki8FBm9H4EZfGhdxLAyU&co=aHR0cHM6Ly9ncmVlbm1ldGhvZHMuY29tOjQ0Mw..&hl=ar&v=MerVUtRoajKEbP7pLiGXkL28&size=invisible&anchor-ms=20000&execute-ms=30000&cb=pltjr0hbqzxk",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                
                data_reload = {
                    "v": "MerVUtRoajKEbP7pLiGXkL28",
                    "reason": "q",
                    "c": c,
                    "k": "6LfYpL0qAAAAAJWUdG9Nki8FBm9H4EZfGhdxLAyU",
                    "hl": "en",
                    "size": "invisible",
                }
                
                response_reload = await session.post(
                    "https://www.google.com/recaptcha/api2/reload?k=6LfYpL0qAAAAAJWUdG9Nki8FBm9H4EZfGhdxLAyU",
                    headers=headers_reload,
                    data=data_reload,
                )
                
                if response_reload.status_code == 200:
                    match_cap = re.search(r'\["rresp","(.*?)",null', response_reload.text)
                    cap = match_cap.group(1) if match_cap else None
            
            # ===== الطلب الرابع: تسجيل حساب جديد =====
            if cap and nonce:
                headers_register = {
                    "authority": "greenmethods.com",
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "accept-language": "ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7",
                    "cache-control": "max-age=0",
                    "content-type": "application/x-www-form-urlencoded",
                    "origin": "https://greenmethods.com",
                    "referer": "https://greenmethods.com/my-account/",
                    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
                    "sec-ch-ua-mobile": "?1",
                    "sec-ch-ua-platform": '"Android"',
                    "sec-fetch-dest": "document",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-user": "?1",
                    "upgrade-insecure-requests": "1",
                    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
                }
                
                data_register = {
                    "email": e,
                    "password": "Williams#123CR7",
                    "g-recaptcha-response": cap,
                    "woocommerce-register-nonce": nonce,
                    "_wp_http_referer": "/my-account/",
                    "register": "Register"
                }
                
                response_register = await session.post(
                    url,
                    headers=headers_register,
                    data=data_register
                )
                
                # طباعة النتيجة النهائية فقط
                print(f"تم التسجيل بنجاح - البريد: {e}")
                print(f"كود الحالة: {response_register.status_code}")
            else:
                print("خطأ: لم يتم الحصول على cap أو nonce")
                
        except Exception as e:
            print(f"خطأ في الطلب: {e}")


if __name__ == "__main__":
    asyncio.run(main())
