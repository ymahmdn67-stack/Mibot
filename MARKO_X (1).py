import requests
import time
import os
import threading

# توكن البوت
TOKEN = "8407059201:AAEZt71bYiznz7Eqix2_b1Gh6tn8hp4MnsI"
BASE_URL = f'https://api.telegram.org/bot{TOKEN}/'

# بوابات الدفع بالإنجليزية
GATEWAY_TERMS = [
    "paypal", "stripe", "square", "razorpay", 
    "cash on delivery", "google pay", "visa", 
    "mastercard", "mada", "apple pay", "amazon pay",  "braintree"
]

# تخزين حالات التحليل لكل مستخدم
user_states = {}
processing_messages = {}

def analyze_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return f"❌ تعذر جلب الموقع: رمز الحالة {response.status_code}"

        content = response.text
        headers = response.headers

        detected_gateways = []
        for term in GATEWAY_TERMS:
            if term.lower() in content.lower():
                detected_gateways.append(term)

        captcha_present = 'captcha' in content.lower() or 're-captcha' in content.lower()
        cloudflare_present = 'cf-ray' in headers or ('set-cookie' in headers and '__cfduid' in headers['set-cookie'].lower())
        graphql_present = '/graphql' in content.lower()

        platform = "غير معروف"
        if "wp-content" in content.lower():
            platform = "WordPress"
        elif "shopify" in content.lower():
            platform = "Shopify"
        elif "magento" in content.lower():
            platform = "Magento"

        result = "✅ تم تحليل الموقع بنجاح\n"
        result += "━━━━━━━━━━━━━━\n"
        result += f"🔗 الرابط: {url}\n"
        result += f"💰 بوابات الدفع: {', '.join(detected_gateways) if detected_gateways else 'غير موجودة'}\n"
        result += f"🛡️ كابتشا: {'نعم' if captcha_present else 'لا'}\n"
        result += f"☁️ كلاودفلير: {'نعم' if cloudflare_present else 'لا'}\n"
        result += f"🔄 GraphQL: {'نعم' if graphql_present else 'لا'}\n"
        result += f"📌 نظام الموقع: {platform}\n"
        result += "━━━━━━━━━━━━━━\n"
        result += "🤖 البوت بواسطة: @PY_X0 /@PY_X00 /@w9_pa"

        return result

    except Exception as e:
        return f"❌ خطأ: {str(e)}"

def send_message(chat_id, text, reply_to_message_id=None):
    url = f"{BASE_URL}sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    if reply_to_message_id:
        data['reply_to_message_id'] = reply_to_message_id
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json().get('result', {}).get('message_id')
    return None

def delete_message(chat_id, message_id):
    url = f"{BASE_URL}deleteMessage"
    data = {'chat_id': chat_id, 'message_id': message_id}
    requests.post(url, json=data)

def download_file(file_id):
    file_info_url = f"{BASE_URL}getFile?file_id={file_id}"
    file_info = requests.get(file_info_url).json()
    if not file_info.get('ok'):
        return None
    file_path = file_info['result']['file_path']
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    response = requests.get(file_url)
    if response.status_code == 200:
        return response.text
    return None

def process_file(file_content):
    try:
        urls = [line.strip() for line in file_content.split('\n') if line.strip()]
        valid_urls = [url for url in urls if url.startswith(('http://', 'https://'))]
        return valid_urls
    except Exception as e:
        print(f"خطأ في معالجة الملف: {e}")
        return []

def analyze_urls_thread(chat_id, urls, file_message_id):
    # تخزين معرفات الرسائل المؤقتة
    temp_messages = []
    
    # إرسال رسالة بدء التحليل
    start_msg_id = send_message(chat_id, f"⏳ بدء تحليل {len(urls)} رابط...")
    if start_msg_id:
        temp_messages.append(start_msg_id)
    
    # حذف رسالة الملف الأصلية إذا طلب المستخدم
    if file_message_id:
        try:
            delete_message(chat_id, file_message_id)
        except:
            pass
    
    # تحليل كل رابط
    for i, url in enumerate(urls, 1):
        # التحقق من طلب الإيقاف
        if user_states.get(chat_id) == 'stop':
            send_message(chat_id, "⏹️ تم إيقاف عملية التحليل بناءً على طلبك")
            break
        
        # إرسال رسالة مؤقتة
        temp_msg_id = send_message(chat_id, f"⏳ جاري تحليل الرابط {i}/{len(urls)}: {url}")
        if temp_msg_id:
            temp_messages.append(temp_msg_id)
        
        # تحليل الموقع
        result = analyze_website(url)
        
        # إرسال النتيجة
        send_message(chat_id, result)
        
        # حذف الرسالة المؤقتة
        if temp_msg_id:
            try:
                delete_message(chat_id, temp_msg_id)
            except:
                pass
    
    # حذف رسالة البداية
    if start_msg_id:
        try:
            delete_message(chat_id, start_msg_id)
        except:
            pass
    
    # إرسال رسالة الإنهاء
    send_message(chat_id, "✅ تم الانتهاء من عملية التحليل")
    
    # إعادة تعيين حالة المستخدم
    user_states[chat_id] = None

def get_updates(last_update_id):
    url = f"{BASE_URL}getUpdates?timeout=100"
    if last_update_id:
        url += f"&offset={last_update_id + 1}"
    response = requests.get(url)
    return response.json()

def main():
    last_update_id = 0
    print("✅ البوت يعمل...")
    while True:
        try:
            updates = get_updates(last_update_id)
            if updates.get('ok'):
                for update in updates['result']:
                    last_update_id = update['update_id']
                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        text = message.get('text', '')
                        caption = message.get('caption', '')
                        message_id = message.get('message_id')

                        # معالجة الأمر /start
                        if text.startswith('/start'):
                            welcome = "مرحباً بك في بوت تحليل المواقع!\n\n"
                            welcome += "📌 لتحليل موقع واحد، أرسل:\n"
                            welcome += "/analyze [رابط الموقع]\n"
                            welcome += "مثال: /analyze https://example.com\n\n"
                            welcome += "📁 لتحليل ملف نصي يحتوي على عدة روابط، أرسل:\n"
                            welcome += "/mc\n"
                            welcome += "ثم أرسل الملف بعد ذلك\n\n"
                            welcome += "⏹ لإيقاف عملية التحليل الجارية، أرسل:\n"
                            welcome += "/stop"
                            send_message(chat_id, welcome)

                        # معالجة الأمر /analyze لموقع واحد
                        elif text.startswith('/analyze'):
                            parts = text.split(' ', 1)
                            if len(parts) < 2:
                                send_message(chat_id, "⚠️ يرجى إدخال رابط الموقع بعد الأمر\nمثال: /analyze https://example.com")
                            else:
                                url = parts[1].strip()
                                if not url.startswith(('http://', 'https://')):
                                    send_message(chat_id, "⚠️ الرابط يجب أن يبدأ بـ http:// أو https://")
                                else:
                                    # حذف رسالة الأمر الأصلية
                                    try:
                                        delete_message(chat_id, message_id)
                                    except:
                                        pass
                                    
                                    # إرسال رسالة التحليل ثم النتيجة
                                    temp_msg_id = send_message(chat_id, "⏳ جاري تحليل الموقع...")
                                    result = analyze_website(url)
                                    send_message(chat_id, result)
                                    
                                    # حذف الرسالة المؤقتة
                                    if temp_msg_id:
                                        try:
                                            delete_message(chat_id, temp_msg_id)
                                        except:
                                            pass

                        # معالجة الأمر /mc
                        elif text == '/mc':
                            send_message(chat_id, "📁 يرجى إرسال ملف نصي (.txt) يحتوي على الروابط المراد تحليلها\n(رابط واحد في كل سطر)")

                        # معالجة الأمر /stop
                        elif text == '/stop':
                            if user_states.get(chat_id) == 'processing':
                                user_states[chat_id] = 'stop'
                                send_message(chat_id, "⏹️ تم استلام طلب الإيقاف، جاري التوقف...")
                            else:
                                send_message(chat_id, "⚠️ لا توجد عملية تحليل قيد التنفيذ")

                        # معالجة الملفات المرسلة
                        if 'document' in message:
                            file_id = message['document']['file_id']
                            file_name = message['document']['file_name']
                            
                            # التحقق من نوع الملف
                            if not file_name.endswith('.txt'):
                                send_message(chat_id, "⚠️ يرجى إرسال ملف نصي بصيغة .txt فقط")
                                continue
                            
                            send_message(chat_id, "⏳ جاري تحميل الملف...")
                            file_content = download_file(file_id)
                            
                            if not file_content:
                                send_message(chat_id, "❌ تعذر تحميل الملف")
                                continue
                            
                            send_message(chat_id, "✅ تم تحميل الملف بنجاح، جاري تحليل الروابط...")
                            
                            # معالجة الملف واستخراج الروابط
                            urls = process_file(file_content)
                            
                            if not urls:
                                send_message(chat_id, "❌ لم يتم العثور على روابط صالحة في الملف")
                                continue
                            
                            # بدء عملية التحليل في خيط منفصل
                            user_states[chat_id] = 'processing'
                            threading.Thread(target=analyze_urls_thread, args=(chat_id, urls, message_id)).start()

        except Exception as e:
            print(f"حدث خطأ: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()