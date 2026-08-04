import re
import base64
import asyncio
from curl_cffi.requests import AsyncSession
from faker import Faker

# تم استخدام الهوية الأمريكية 
fake = Faker("en_US")

async def get_initial_tokens():
    # الإبقاء على المحاكاة كما طلبت للتجربة
    async with AsyncSession(impersonate="chrome120") as session:
        
        # الإبقاء على الترويسات اليدوية بالكامل (مع توحيد إصدار الكروم إلى 120 لمنع التعارض)
        headers = {
            'authority': 'bukjeh.org',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        }
        
        print("🔄 جاري إرسال الطلب الأولي (مع impersonate والهيدرز اليدوية)...")
        response = await session.get(
            'https://bukjeh.org/donations/donation-2023-2-3/',
            headers=headers
        )
        
        html = response.text
        
        try:
            # استخراج البيانات
            form_hash = re.search(r'name="give-form-hash"\s+value="([^"]+)"', html).group(1)
            pre = re.search(r'name="give-form-id-prefix"\s+value="([^"]+)"', html).group(1)
            give = re.search(r'name="give-form-id"\s+value="([^"]+)"', html).group(1)
            
            enc = re.search(r'"data-client-token":"([^"]+)"', html).group(1)
            dec = base64.b64decode(enc).decode("utf-8")
            au = re.search(r'"accessToken":"([^"]+)"', dec).group(1)
            
            print("✅ تم استخراج البيانات بنجاح، جدار الحماية سمح بالمرور!")
            print(f"give-form-hash: {form_hash}")
            print(f"give-form-id-prefix: {pre}")
            print(f"give-form-id: {give}")
            print(f"accessToken: {au[:30]}...") 
            
            return {
                "hash": form_hash,
                "pre": pre,
                "give": give,
                "au": au
            }
            
        except AttributeError:
            print("❌ لا يزال عالقاً في صفحة الحماية (One moment, please...).")
            print("أول 300 حرف من الاستجابة للتحقق:")
            print(html[:300])
            return None

if __name__ == "__main__":
    asyncio.run(get_initial_tokens())
