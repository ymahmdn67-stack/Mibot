import asyncio
import importlib.util
import os
import sys
import time
import traceback
from contextlib import contextmanager

# --- إعدادات المحاكي ---
CARD_DATA = "5334670035839519|10|28|948"  # بيانات افتراضية
PROXY = None
TIMEOUT_SECONDS = 60.0

# ---------------------------------------------------------------------------
# تعريفات البوابات — مستخرجة من الملف المرفق Gataway-cf.zip
# ---------------------------------------------------------------------------
GATEWAY_GROUPS = [
    {
        "name": "B3 Auth",
        "gateways": [
            ("auth/B3 Auth/B3-1.py", "process_B3_1"),
            ("auth/B3 Auth/B3-2.py", "process_B3_2"),
            ("auth/B3 Auth/B3-3.py", "process_B3_3"),
            ("auth/B3 Auth/B3-4.py", "process_B3_4"),
        ]
    },
    {
        "name": "SQ Auth",
        "gateways": [
            ("auth/SQ Auth/SQ-1.py", "process_SQ_1"),
            ("auth/SQ Auth/SQ-2.py", "process_SQ_2"),
            ("auth/SQ Auth/SQ-3.py", "process_SQ_3"),
        ]
    },
    {
        "name": "ST Auth",
        "gateways": [
            ("auth/ST Auth/ST-1.py", "process_ST_1"),
            ("auth/ST Auth/ST-2.py", "process_ST_2"),
        ]
    },
    {
        "name": "SQ Charge",
        "gateways": [
            ("charge /SQ charge /SQ_1_charge.py", "process_SQ_1_charge"),
        ]
    },
    {
        "name": "ST Charge",
        "gateways": [
            ("charge /St charge /ST-1-Charge.py", "process_ST_1_charge"),
            ("charge /St charge /ST-2-Charge.py", "process_ST_2_charge"),
        ]
    },
    {
        "name": "Authorize.Net",
        "gateways": [
            ("charge /Authorize.Net/Au-1.py", "process_Au_1"),
        ]
    },
    {
        "name": "PayPal",
        "gateways": [
            ("charge /paypal/paypal-1.py", "process_paypal_1"),
            ("charge /paypal/paypal-2.py", "process_paypal_2"),
        ]
    },
    {
        "name": "LookUp Passed",
        "gateways": [
            ("lookup /LookUp Passed/LookUp1_passed.py", "process_LookUp1_passed"),
            ("lookup /LookUp Passed/LookUp2_passed.py", "process_LookUp2_passed"),
            ("lookup /LookUp Passed/LookUp3_passed.py", "process_LookUp3_passed"),
        ]
    },
    {
        "name": "B3 LookUp 3DS",
        "gateways": [
            ("lookup /B3_LookUp 3ds/B3_LookUp1_secure.py", "process_B3_LookUp1_secure"),
            ("lookup /B3_LookUp 3ds/B3_LookUp2_secure.py", "process_B3_LookUp2_secure"),
            ("lookup /B3_LookUp 3ds/B3_LookUp3_secure.py", "process_B3_LookUp3_secure"),
        ]
    },
    {
        "name": "Global 3DS/Passed",
        "gateways": [
            ("lookup /Global 3ds/GP-1.py", "process_GP_1"),
            ("lookup /Global 3ds/GP-2.py", "process_GP_2"),
            ("lookup /Global_Passed/GP-1-passed.py", "process_GP_1_passed"),
            ("lookup /Global_Passed/GP-2-Passed.py", "process_GP_2_passed"),
        ]
    }
]

# ---------------------------------------------------------------------------
# وظائف المساعدة
# ---------------------------------------------------------------------------

def get_base_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "Gataway-cf")

@contextmanager
def pushd(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)

def load_func(abs_path: str, func_name: str):
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"الملف غير موجود: {abs_path}")

    mod_name = os.path.basename(abs_path).replace("-", "_").replace(" ", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(mod_name, abs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"تعذر تحميل الموديل: {abs_path}")

    mod = importlib.util.module_from_spec(spec)
    # إضافة مسار المجلد الحالي للمسارات لضمان عمل الاستيرادات الداخلية في الملفات
    sys.path.insert(0, os.path.dirname(abs_path))
    spec.loader.exec_module(mod)
    sys.path.pop(0)

    if not hasattr(mod, func_name):
        # محاولة البحث عن أي دالة تبدأ بـ process_ إذا لم نجد الدالة المحددة
        for attr in dir(mod):
            if attr.startswith("process_"):
                return getattr(mod, attr)
        raise AttributeError(f"الدالة '{func_name}' غير موجودة في {abs_path}")

    return getattr(mod, func_name)

async def run_gateway(name: str, rel_path: str, func_name: str, card: str, proxy: str = None):
    base = get_base_path()
    abs_path = os.path.join(base, rel_path)
    
    print(f"[{name}] جاري التشغيل...")
    start_time = time.time()
    
    try:
        func = load_func(abs_path, func_name)
        
        # تشغيل الدالة مع مهلة زمنية
        try:
            if asyncio.iscoroutinefunction(func):
                res = await asyncio.wait_for(func(card, proxy), timeout=TIMEOUT_SECONDS)
            else:
                # التحقق مما إذا كانت الدالة ترجع generator (مثل الدوال التي تستخدم yield)
                res = func(card, proxy)
                if hasattr(res, "__await__"):
                    res = await asyncio.wait_for(res, timeout=TIMEOUT_SECONDS)
                elif hasattr(res, "__next__") or hasattr(res, "__iter__"):
                    # إذا كان مولد (generator) نأخذ أول نتيجة منه مع معالجة الاستثناءات الخاصة به
                    try:
                        res = next(iter(res))
                    except StopIteration:
                        res = ("Error", "Generator produced no result")
                    except Exception as e:
                        res = ("Error", f"Generator error: {str(e)}")
        except Exception as e:
            res = ("Error", f"Execution failed: {str(e)}")
            
        elapsed = time.time() - start_time
        
        # تنسيق النتيجة
        if isinstance(res, (tuple, list)):
            status = str(res[0])
            msg = str(res[1]) if len(res) > 1 else ""
        else:
            status = str(res)
            msg = ""
            
        return {
            "name": name,
            "status": status,
            "message": msg,
            "time": f"{elapsed:.2f}s",
            "success": True
        }
    except asyncio.TimeoutError:
        return {"name": name, "status": "Timeout", "message": "انتهت مهلة الانتظار", "time": "-", "success": False}
    except Exception as e:
        return {"name": name, "status": "Error", "message": str(e), "time": "-", "success": False}

async def main():
    print("="*60)
    print(" محاكي بوابات الدفع - بنمط المطور ")
    print("="*60)
    
    card = input(f"أدخل بيانات البطاقة [{CARD_DATA}]: ").strip()
    if not card:
        card = CARD_DATA
        
    proxy = input("أدخل البروكسي (اختياري): ").strip() or PROXY
    
    # عرض المجموعات
    print("\nالمجموعات المتاحة:")
    for i, group in enumerate(GATEWAY_GROUPS, 1):
        print(f"{i}. {group['name']} ({len(group['gateways'])} بوابات)")
    
    choice = input("\nاختر رقم المجموعة (أو 'all' للكل): ").strip()
    
    to_run = []
    if choice.lower() == 'all':
        for group in GATEWAY_GROUPS:
            for rel, func in group['gateways']:
                to_run.append((group['name'], rel, func))
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(GATEWAY_GROUPS):
                group = GATEWAY_GROUPS[idx]
                for rel, func in group['gateways']:
                    to_run.append((group['name'], rel, func))
            else:
                print("اختيار خاطئ")
                return
        except ValueError:
            print("مدخل غير صحيح")
            return

    print(f"\nبدء فحص {len(to_run)} بوابات...\n")
    
    tasks = [run_gateway(name, rel, func, card, proxy) for name, rel, func in to_run]
    results = await asyncio.gather(*tasks)
    
    print("\n" + "="*80)
    print(f"{'Gateway':<25} | {'Status':<15} | {'Time':<8} | {'Response'}")
    print("-" * 80)
    
    for r in results:
        name_display = r['name'][:25]
        status = str(r['status'])[:15]
        msg = str(r['message']).replace('\n', ' ').strip()[:30]
        print(f"{name_display:<25} | {status:<15} | {r['time']:<8} | {msg}")
        
    print("="*80)
    print(f"تم الانتهاء من الفحص. إجمالي البوابات: {len(results)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nتم الإلغاء بواسطة المستخدم.")
    except Exception:
        traceback.print_exc()
