# حل reCAPTCHA v2 Invisible باستخدام Playwright

## نسخ الكود المتاحة

### 1. النسخة غير المتزامنة (Async) - `recaptcha_playwright_solver.py`
- **الأفضل للتطبيقات الكبيرة**
- تدعم معالجة متعددة بكفاءة
- تحتاج إلى `asyncio`

### 2. النسخة المتزامنة (Sync) - `recaptcha_playwright_solver_sync.py`
- **الأفضل للاستخدام السريع**
- أسهل في الفهم والاستخدام
- مثالية للسكريبتات البسيطة

---

## التثبيت

### 1. تثبيت المكتبات المطلوبة
```bash
pip install -r requirements.txt
```

أو يدويًا:
```bash
pip install playwright
```

### 2. تثبيت متصفح Chromium
```bash
playwright install chromium
```

---

## الاستخدام

### استخدام النسخة المتزامنة (الموصى بها)
```bash
python recaptcha_playwright_solver_sync.py
```

### استخدام النسخة غير المتزامنة
```bash
python recaptcha_playwright_solver.py
```

---

## كيفية عمل الكود

1. **تشغيل المتصفح**: يفتح Chromium في وضع مرئي (headless=False)
2. **اعتراض الطلبات**: يراقب جميع استجابات الشبكة
3. **البحث عن reCAPTCHA**: يبحث عن طلبات تحتوي على `recaptcha` و `reload`
4. **استخراج التوكن**: يستخدم Regex للبحث عن النمط `["rresp","TOKEN_HERE"`
5. **الإرجاع**: يعيد التوكن عند استخراجه

---

## المتغيرات القابلة للتخصيص

### تغيير الموقع المستهدف
```python
target_url = "https://your-website.com"
```

### تغيير مدة الانتظار
```python
token = solver.solve(target_url, timeout=60)  # 60 ثانية
```

### تشغيل المتصفح في وضع مخفي
```python
browser = p.chromium.launch(headless=True)
```

---

## الإخراج المتوقع

```
============================================================
حل reCAPTCHA v2 Invisible باستخدام Playwright
============================================================

[*] جاري فتح الموقع: https://greenmethods.com/my-account/
[*] جاري الانتظار لالتقاط التوكن...
[*] تم اعتراض طلب: https://www.google.com/recaptcha/api2/reload?k=...
[✓] تم استخراج التوكن: 03AOLTBLQwB...

[✓] تم الالتقاط بنجاح!
[✓] TOKEN = 03AOLTBLQwB...

============================================================
النتيجة النهائية:
============================================================
TOKEN = 03AOLTBLQwB...
============================================================
```

---

## استخدام التوكن في الكود الخاص بك

```python
from recaptcha_playwright_solver_sync import RecaptchaSolver

solver = RecaptchaSolver()
token = solver.solve("https://greenmethods.com/my-account/", timeout=30)

if token:
    # استخدم التوكن في طلبات HTTP
    data = {
        "g-recaptcha-response": token,
        # بيانات أخرى...
    }
    response = requests.post("https://greenmethods.com/submit", data=data)
```

---

## استكشاف الأخطاء

### المشكلة: لا يتم استخراج التوكن
**الحل:**
- تأكد من أن الموقع يستخدم reCAPTCHA v2 (وليس v3 أو Enterprise)
- تحقق من أن المتصفح يفتح بشكل صحيح (headless=False)
- زد مدة الانتظار (timeout)
- تحقق من اتصال الإنترنت

### المشكلة: خطأ في تثبيت Playwright
**الحل:**
```bash
pip install --upgrade playwright
playwright install
```

### المشكلة: المتصفح لا يفتح
**الحل:**
```bash
playwright install chromium
```

---

## الفروقات من الكود الأصلي (mitmproxy)

| الميزة | Playwright | mitmproxy |
|--------|-----------|----------|
| سهولة الإعداد | ✅ سهل جداً | ❌ معقد |
| تثبيت الشهادات | ❌ غير مطلوب | ✅ مطلوب |
| الأداء | ✅ سريع | ❌ بطيء |
| الاستقرار | ✅ عالي | ❌ متوسط |
| اكتشاف الوكيل | ❌ لا يُكتشف | ✅ قد يُكتشف |
| سهولة الصيانة | ✅ سهل | ❌ معقد |

---

## ملاحظات مهمة

1. **الموقع المستهدف**: الكود مخصص لـ `greenmethods.com` ولكن يمكن تعديله لأي موقع
2. **نوع reCAPTCHA**: الكود يعمل مع **reCAPTCHA v2 Invisible**
3. **المتصفح**: يستخدم Chromium (يمكن تغييره إلى Firefox أو WebKit)
4. **الترخيص**: استخدم هذا الكود بمسؤوليتك الخاصة وتأكد من توافقه مع شروط الخدمة

---

## المراجع

- [Playwright Documentation](https://playwright.dev/python/)
- [reCAPTCHA Documentation](https://developers.google.com/recaptcha)
- [Python Regex Documentation](https://docs.python.org/3/library/re.html)
