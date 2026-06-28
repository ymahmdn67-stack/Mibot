import random, base64, re, asyncio, json
from faker import Faker
from curl_cffi.requests import AsyncSession


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


async def main():
    try:
        async with AsyncSession(
            impersonate="chrome139",
            timeout=30
        ) as session:

            response = await session.request(
                method="GET",
                url=url,
                headers=headers,
                cookies=cookies,
            )

            print(response.status_code)
            print(response.text)

    except Exception as e:
        print(f"Request failed: {e}")


nonce = re.search(
    r'name="woocommerce-register-nonce" value="([^"]+)"',
    response.text
)

if not nonce:
    continue

nonce = nonce.group(1)
