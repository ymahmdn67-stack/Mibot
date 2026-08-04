import re
import base64
import asyncio
from curl_cffi.requests import AsyncSession
from faker import Faker

# الاعتماد على الهوية الأمريكية
fake = Faker("en_US")

async def get_initial_tokens():
    # استخدام محاكاة متصفح Chrome لتخطي الحماية
    async with AsyncSession(impersonate="chrome120") as session:
        
        # تمرير الترويسات التوجيهية فقط، وترك الباقي لمكتبة curl-cffi
        headers = {
            "referer": "https://bukjeh.org/",
            "upgrade-insecure-requests": "1"
        }
        
        print("🔄 جاري إرسال الطلب الأولي...")
        response = await session.get(
            'https://bukjeh.org/donations/donation-2023-2-3/',
            headers=headers
        )
        
        html = response.text
        
        try:
            # استخراج البيانات باستخدام التعابير القياسية (Regex)
            form_hash = re.search(r'name="give-form-hash"\s+value="([^"]+)"', html).group(1)
            pre = re.search(r'name="give-form-id-prefix"\s+value="([^"]+)"', html).group(1)
            give = re.search(r'name="give-form-id"\s+value="([^"]+)"', html).group(1)
            
            enc = re.search(r'"data-client-token":"([^"]+)"', html).group(1)
            dec = base64.b64decode(enc).decode("utf-8")
            au = re.search(r'"accessToken":"([^"]+)"', dec).group(1)
            
            print("✅ تم استخراج البيانات بنجاح:")
            print(f"give-form-hash: {form_hash}")
            print(f"give-form-id-prefix: {pre}")
            print(f"give-form-id: {give}")
            print(f"accessToken: {au[:30]}...") # طباعة جزء من التوكن لتجنب ازدحام الشاشة
            
            return {
                "hash": form_hash,
                "pre": pre,
                "give": give,
                "au": au
            }
            
        except AttributeError:
            print("❌ فشل استخراج البيانات. قد يكون الموقع قام بحظر الطلب أو تغير هيكل الصفحة.")
            print("أول 500 حرف من الاستجابة للتحقق:")
            print(html[:500])
            return None

if __name__ == "__main__":
    # تشغيل الدالة غير المتزامنة
    asyncio.run(get_initial_tokens())
