import asyncio
import re
import base64
import curl_cffi.requests as requests  # curl_cffi مع دعم async


async def main():
    headers = {
        'authority': 'bukjeh.org',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    url = 'https://bukjeh.org/donations/donation-2023-2-3/'

    async with requests.AsyncSession() as session:
        # impersonate يحاكي بصمة كروم حديثة (مهم لبعض المواقع)
        response = await session.get(url, headers=headers, impersonate="chrome124")
        text = response.text

    # استخراج القيم باستخدام regex (مع التحقق من وجود المطابقة)
    hash_match = re.search(r'name="give-form-hash" value="(.*?)"', text)
    pre_match = re.search(r'name="give-form-id-prefix" value="(.*?)"', text)
    give_match = re.search(r'name="give-form-id" value="(.*?)"', text)
    enc_match = re.search(r'"data-client-token":"(.*?)"', text)

    if not all([hash_match, pre_match, give_match, enc_match]):
        print("❌ تعذّر استخراج أحد الحقول المطلوبة من الصفحة.")
        return

    hash_val = hash_match.group(1)
    pre = pre_match.group(1)
    give = give_match.group(1)
    enc = enc_match.group(1)

    # فك تشفير base64 واستخراج accessToken
    try:
        dec = base64.b64decode(enc).decode("utf-8")
        au_match = re.search(r'"accessToken":"(.*?)"', dec)
        if not au_match:
            print("❌ لم يُعثر على accessToken داخل البيانات.")
            return
        au = au_match.group(1)
    except Exception as e:
        print(f"❌ خطأ أثناء فك التشفير: {e}")
        return

    print("✅ محتوى الصفحة (جزء منه):")
    print(text[:500])  # عرض أول 500 حرف فقط للتأكد
    print("\n--- القيم المستخرجة ---")
    print("give-form-hash:", hash_val)
    print("give-form-id-prefix:", pre)
    print("give-form-id:", give)
    print("accessToken:", au)


if __name__ == "__main__":
    asyncio.run(main())
