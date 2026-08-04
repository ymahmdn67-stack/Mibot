import asyncio
import re
import base64
from curl_cffi.requests import AsyncSession

async def fetch_donation_tokens():
    url = 'https://bukjeh.org/donations/donation-2023-2-3/'

    # إعدادات البروكسي بصيغة (http://username:password@host:port)
    proxy_url = "http://purevpn0s8732217:i67s60ep@px121102.pointtoserver.com:10780"
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9,ar;q=0.8',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    }

    # تم إضافة البروكسي داخل الجلسة
    async with AsyncSession(impersonate="chrome120", proxies=proxies, timeout=15) as session:
        try:
            print("[*] جاري الاتصال عبر البروكسي...")
            response = await session.get(url, headers=headers, follow_redirects=True)
            print(f"[*] رمز الاستجابة (Status Code): {response.status_code}")
        except Exception as e:
            print(f"[❌] فشل الاتصال بالبروكسي: {e}")
            return

        html_text = response.text

        # حفظ الصفحة للمعاينة في حال استدعت الحاجة
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html_text)

        # فحص وجود حظر أمني
        if "just a moment" in html_text.lower() or "enable javascript" in html_text.lower():
            print("\n[❌] خطأ: لا يزال يتم حظر الطلب من السيرفر.")
            return

        def extract_pattern(patterns, text):
            for p in patterns:
                match = re.search(p, text, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1)
            return None

        # استخراج البارامترات المطلوبة
        form_hash = extract_pattern([
            r'name=["\']give-form-hash["\']\s+value=["\'](.*?)["\']',
            r'value=["\'](.*?)["\']\s+name=["\']give-form-hash["\']',
            r'"form_hash"\s*:\s*["\'](.*?)["\']',
            r'data-hash=["\'](.*?)["\']'
        ], html_text)

        form_prefix = extract_pattern([
            r'name=["\']give-form-id-prefix["\']\s+value=["\'](.*?)["\']',
            r'value=["\'](.*?)["\']\s+name=["\']give-form-id-prefix["\']',
            r'"form_prefix"\s*:\s*["\'](.*?)["\']',
            r'give-form-id-prefix-([a-zA-Z0-9_-]+)'
        ], html_text)

        form_id = extract_pattern([
            r'name=["\']give-form-id["\']\s+value=["\'](.*?)["\']',
            r'value=["\'](.*?)["\']\s+name=["\']give-form-id["\']',
            r'data-form-id=["\'](\d+)["\']',
            r'id=["\']give-form-(\d+)'
        ], html_text)

        client_token = extract_pattern([
            r'["\']data-client-token["\']\s*:\s*["\'](.*?)["\']',
            r'data-client-token=["\'](.*?)["\']',
            r'clientToken["\']?\s*:\s*["\'](.*?)["\']'
        ], html_text)

        access_token = None
        if client_token:
            try:
                decoded = base64.b64decode(client_token).decode("utf-8")
                access_token = extract_pattern([r'["\']accessToken["\']\s*:\s*["\'](.*?)["\']'], decoded)
            except Exception as e:
                print(f"[!] خطأ في فك التشفير: {e}")

        print("\n=== النتائج المستخرجة ===")
        print("give-form-hash:", form_hash)
        print("give-form-id-prefix:", form_prefix)
        print("give-form-id:", form_id)
        print("accessToken:", access_token)

if __name__ == '__main__':
    asyncio.run(fetch_donation_tokens())
