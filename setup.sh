#!/bin/bash
# سكريبت الإعداد التلقائي لبيئة Codespaces
echo "========================================"
echo " إعداد بيئة حل reCAPTCHA v2 Invisible"
echo "========================================"

echo ""
echo "[1/3] تثبيت مكتبة Playwright..."
pip install playwright

echo ""
echo "[2/3] تثبيت متصفح Chromium..."
playwright install chromium

echo ""
echo "[3/3] تثبيت المكتبات الإضافية المطلوبة..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "✅ تم الإعداد بنجاح! يمكنك الآن تشغيل:"
echo "   python recaptcha_playwright_solver_sync.py"
echo "========================================"
