import random, base64, re, asyncio, json
from faker import Faker
from curl_cffi.requests import AsyncSession


class tools:
    @staticmethod
    def find_between(s: str, first: str, last: str) -> str | None:
        try:
            return s.split(first, 1)[1].split(last, 1)[0]
        except:
            return None
    
    @staticmethod
    def userdata() -> dict:
        f = Faker()
        fn, ln = f.first_name(), f.last_name()
        return {
            "name": f"{fn} {ln}",
            "first": fn,
            "last": ln,
            "address": f.street_address(),
            "city": f.city(),
            "state": f.state_abbr(),
            "zip": f.postcode(),
            "email": f.email(),
            "phone": f"2{random.randint(10**8, 10**9-1)}"
        }


class gateway:
    @staticmethod
    async def code(prox: str = None) -> tuple:
        proxy = f"http://{prox}" if prox and "://" not in prox else prox
        
        for _ in range(1):
            try:
                async with AsyncSession(impersonate="chrome120", proxy=proxy) as session:
                    
                    user = tools.userdata()
                    
                    # ========== >_ Req 1: الحصول على صفحة حسابي واستخراج nonce
                    headers = {
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                        'cache-control': 'max-age=0',
                        'priority': 'u=0, i',
                        'referer': 'https://greenmethods.com/',
                        'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                        'sec-ch-ua-mobile': '?1',
                        'sec-ch-ua-platform': '"Android"',
                        'sec-fetch-dest': 'document',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'same-origin',
                        'sec-fetch-user': '?1',
                        'upgrade-insecure-requests': '1',
                        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
                    }
                    resp = await session.get('https://greenmethods.com/my-account/', headers=headers)
                    _nonce = tools.find_between(resp.text, 'name="woocommerce-register-nonce" value="', '"')
                    if not _nonce:
                        continue
                    
                    # ========== >_ Req 1.5: الحصول على reCAPTCHA token
                    headers_anchor = {
                        'authority': 'www.google.com',
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                        'referer': 'https://greenmethods.com/',
                        'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                        'sec-ch-ua-mobile': '?1',
                        'sec-ch-ua-platform': '"Android"',
                        'sec-fetch-dest': 'iframe',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'cross-site',
                        'upgrade-insecure-requests': '1',
                        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
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
                    
                    resp_anchor = await session.get(
                        'https://www.google.com/recaptcha/api2/anchor',
                        params=params_anchor,
                        headers=headers_anchor,
                    )
                    
                    _token = tools.find_between(resp_anchor.text, 'id="recaptcha-token"\\s+value="', '"')
                    if not _token:
                        continue
                    
                    # ========== >_ Req 1.6: الحصول على reCAPTCHA response
                    headers_reload = {
                        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
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
                        "c": _token,
                        "k": "6LfYpL0qAAAAAJWUdG9Nki8FBm9H4EZfGhdxLAyU",
                        "hl": "en",
                        "size": "invisible",
                    }
                    
                    resp_reload = await session.post(
                        "https://www.google.com/recaptcha/api2/reload?k=6LfYpL0qAAAAAJWUdG9Nki8FBm9H4EZfGhdxLAyU",
                        headers=headers_reload,
                        data=data_reload,
                    )
                    
                    _cap = None
                    if resp_reload.status_code == 200:
                        _match_cap = re.search(r'\["rresp","(.*?)",null', resp_reload.text)
                        _cap = _match_cap.group(1) if _match_cap else None
                    
                    if not _cap:
                        continue
                    
                    # ========== >_ Req 2: تسجيل حساب جديد
                    headers = {
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                        'cache-control': 'max-age=0',
                        'content-type': 'application/x-www-form-urlencoded',
                        'origin': 'https://greenmethods.com',
                        'priority': 'u=0, i',
                        'referer': 'https://greenmethods.com/my-account/',
                        'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                        'sec-ch-ua-mobile': '?1',
                        'sec-ch-ua-platform': '"Android"',
                        'sec-fetch-dest': 'document',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'same-origin',
                        'sec-fetch-user': '?1',
                        'upgrade-insecure-requests': '1',
                        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
                    }
                    data = [
                        ('email', user['email']),
                        ('password', 'Williams#123CR7'),
                        ('g-recaptcha-response', _cap),
                        ('woocommerce-register-nonce', _nonce),
                        ('_wp_http_referer', '/my-account/'),
                        ('register', 'Register'),
                    ]
                    resp = await session.post('https://greenmethods.com/my-account/', headers=headers, data=data)
                    
                    # ========== >_ Req 3: الوصول إلى صفحة تعديل العنوان واستخراج _nonce
                    headers = {
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                        'priority': 'u=0, i',
                        'referer': 'https://greenmethods.com/my-account/edit-address/',
                        'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                        'sec-ch-ua-mobile': '?1',
                        'sec-ch-ua-platform': '"Android"',
                        'sec-fetch-dest': 'document',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'same-origin',
                        'sec-fetch-user': '?1',
                        'upgrade-insecure-requests': '1',
                        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    }
                    resp = await session.get('https://greenmethods.com/my-account/edit-address/billing/', headers=headers)
                    _nonce_edit = tools.find_between(resp.text, 'name="woocommerce-edit-address-nonce" value="', '"')
                    if not _nonce_edit:
                        continue
                    
                    # ========== >_ Req 4: تحديث بيانات العنوان
                    headers = {
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                        'cache-control': 'max-age=0',
                        'content-type': 'application/x-www-form-urlencoded',
                        'origin': 'https://greenmethods.com',
                        'priority': 'u=0, i',
                        'referer': 'https://greenmethods.com/my-account/edit-address/billing/',
                        'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                        'sec-ch-ua-mobile': '?1',
                        'sec-ch-ua-platform': '"Android"',
                        'sec-fetch-dest': 'document',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'same-origin',
                        'sec-fetch-user': '?1',
                        'upgrade-insecure-requests': '1',
                        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    }
                    data = {
                        'billing_email': user['email'],
                        'billing_first_name': user['first'],
                        'billing_last_name': user['last'],
                        'billing_company': '',
                        'billing_country': 'GB',
                        'billing_address_1': 'Studio 7 Gerald crossing',
                        'billing_address_2': '',
                        'billing_city': 'Port Carolyntown',
                        'billing_state': '',
                        'billing_postcode': 'G5H 3DQ',
                        'billing_phone': '+44 7582 444 8798',
                        'save_address': 'Save address',
                        'woocommerce-edit-address-nonce': _nonce_edit,
                        '_wp_http_referer': '/my-account/edit-address/billing/',
                        'action': 'edit_address',
                    }
                    resp = await session.post('https://greenmethods.com/my-account/edit-address/billing/', headers=headers, data=data)
                    
                    # ========== >_ Result
                    _result = re.search(r'<ul class="woocommerce-error"[^>]*>.*?<li>(.*?)</li>', resp.text, re.DOTALL)
                    if _result:
                        return 'Failed!', _result.group(1).strip()
                    else:
                        return 'Success!', f'Email: {user["email"]}'
                    
            except Exception as e:
                continue
        
        return "Error!", "Connection error"


if __name__ == "__main__":
    print(asyncio.run(gateway.code(None)))
