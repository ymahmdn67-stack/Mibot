import asyncio
import re
import base64
import logging
from curl_cffi import requests

logging.basicConfig(level=logging.INFO)

def parse_proxy(proxy_str: str) -> str:
    """
    تحويل سلسلة host:port:user:pass إلى صيغة URL مناسبة لـ curl_cffi
    """
    parts = proxy_str.strip().split(':')
    if len(parts) == 4:
        host, port, user, pwd = parts
        return f"http://{user}:{pwd}@{host}:{port}"
    elif len(parts) == 2:  # host:port فقط
        host, port = parts
        return f"http://{host}:{port}"
    else:
        raise ValueError("صيغة البروكسي غير صالحة. استخدم host:port:user:pass أو host:port")

async def main():
    # البروكسي المقدم
    proxy_raw = "px016104.pointtoserver.com:10780:purevpn0s2232045:hww8fqbr72j0"
    proxy_url = parse_proxy(proxy_raw)
    logging.info(f"🛡️ استخدام البروكسي: {proxy_url.split('@')[0]}@*****")  # إخفاء كلمة المرور

    url = 'https://bukjeh.org/donations/donation-2023-2-3/'
    headers = {
        'authority': 'bukjeh.org',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }

    try:
        async with requests.AsyncSession(
            impersonate="chrome120",
            timeout=30,
            proxy=proxy_url  # تمرير البروكسي هنا
        ) as session:
            response = await session.get(url, headers=headers)
            text = response.text

            if len(text) < 500:
                logging.warning("⚠️ نص الاستجابة قصير جدًا، قد يكون هناك حماية")
                logging.debug(text[:500])
    except requests.errors.RequestsError as e:
        logging.error(f"❌ خطأ في الاتصال عبر البروكسي: {e}")
        return
    except Exception as e:
        logging.error(f"❌ خطأ غير متوقع: {e}")
        return

    # استخراج القيم
    patterns = {
        'give-form-hash': r'name="give-form-hash" value="(.*?)"',
        'give-form-id-prefix': r'name="give-form-id-prefix" value="(.*?)"',
        'give-form-id': r'name="give-form-id" value="(.*?)"',
        'data-client-token': r'"data-client-token":"(.*?)"'
    }

    extracted = {}
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if not m:
            logging.error(f"❌ لم يتم العثور على '{key}' في الصفحة")
            return
        extracted[key] = m.group(1)

    # فك client-token
    try:
        dec = base64.b64decode(extracted['data-client-token']).decode("utf-8")
        au_match = re.search(r'"accessToken":"(.*?)"', dec)
        if not au_match:
            logging.error("❌ accessToken غير موجود في البيانات المفكوكة")
            return
        access_token = au_match.group(1)
    except Exception as e:
        logging.error(f"❌ فشل فك التشفير: {e}")
        return

    print("\n✅ نجحت العملية عبر البروكسي!")
    print("give-form-hash:", extracted['give-form-hash'])
    print("give-form-id-prefix:", extracted['give-form-id-prefix'])
    print("give-form-id:", extracted['give-form-id'])
    print("accessToken:", access_token)


if __name__ == "__main__":
    asyncio.run(main())
