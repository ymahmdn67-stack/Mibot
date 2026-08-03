"""
=================================================================
proxy_manager.py — Central Proxy Rotation Helper
=================================================================
هذه الوحدة تقرأ قائمة البروكسيات من proxies.txt وتعيد بروكسي واحداً
لكل طلب مع تجنب تكرار آخر بروكسي مستخدم كلما كان ذلك ممكناً.

السلوك:
    - إذا كان proxies.txt فارغاً أو غير موجود، تُرجع الدالة None.
    - إذا كان هناك بروكسي واحد فقط، تُرجعه دائماً.
    - إذا كان هناك أكثر من بروكسي، تستخدم Round Robin وتمنع تكرار
      نفس البروكسي في طلبين متتاليين داخل نفس عملية التشغيل.
=================================================================
"""
from __future__ import annotations

from pathlib import Path
from threading import Lock

BASE_DIR = Path(__file__).resolve().parent
PROXIES_FILE = BASE_DIR / "proxies.txt"

_proxy_lock = Lock()
_proxy_cache: list[str] = []
_proxy_file_mtime: float | None = None
_proxy_index = 0
_last_proxy: str | None = None


def _normalize_proxy(raw_proxy: str) -> str | None:
    """تنظيف السطر وإرجاع البروكسي بصيغة aiohttp المقبولة أو None.

    الصيغ المدعومة:
        - http://host:port
        - http://user:pass@host:port
        - socks5://host:port
        - socks5://user:pass@host:port
        - host:port
        - host:port:user:pass

    عند استخدام صيغة host:port:user:pass يتم تحويلها تلقائياً إلى:
        http://user:pass@host:port
    """
    proxy = (raw_proxy or "").strip()
    if not proxy or proxy.startswith("#"):
        return None

    allowed_prefixes = ("http://", "https://", "socks4://", "socks5://")
    if proxy.startswith(allowed_prefixes):
        return proxy

    parts = proxy.split(":")
    if len(parts) == 4:
        host, port, username, password = [part.strip() for part in parts]
        if host and port and username and password:
            return f"http://{username}:{password}@{host}:{port}"

    # إذا كُتب البروكسي بصيغة host:port فقط، نضيف http:// تلقائياً.
    return f"http://{proxy}"


def _load_proxies_if_needed() -> list[str]:
    """تحميل القائمة من الملف عند أول استخدام أو عند تغير الملف."""
    global _proxy_cache, _proxy_file_mtime, _proxy_index, _last_proxy

    if not PROXIES_FILE.exists():
        _proxy_cache = []
        _proxy_file_mtime = None
        _proxy_index = 0
        _last_proxy = None
        return _proxy_cache

    current_mtime = PROXIES_FILE.stat().st_mtime
    if _proxy_file_mtime == current_mtime:
        return _proxy_cache

    loaded: list[str] = []
    seen: set[str] = set()
    for line in PROXIES_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        proxy = _normalize_proxy(line)
        if proxy and proxy not in seen:
            loaded.append(proxy)
            seen.add(proxy)

    _proxy_cache = loaded
    _proxy_file_mtime = current_mtime
    _proxy_index = 0
    _last_proxy = None
    return _proxy_cache


def get_next_proxy() -> str | None:
    """
    إرجاع بروكسي للطلب الحالي.

    هذه الدالة مناسبة للاستدعاء مباشرة قبل تنفيذ دالة البوابة. عند وجود أكثر
    من بروكسي، تضمن ألا يكون البروكسي المختار هو نفسه المستخدم في الطلب
    السابق داخل نفس عملية تشغيل البوت.
    """
    global _proxy_index, _last_proxy

    with _proxy_lock:
        proxies = _load_proxies_if_needed()
        if not proxies:
            return None

        if len(proxies) == 1:
            _last_proxy = proxies[0]
            return proxies[0]

        candidate = proxies[_proxy_index % len(proxies)]
        _proxy_index = (_proxy_index + 1) % len(proxies)

        if candidate == _last_proxy:
            candidate = proxies[_proxy_index % len(proxies)]
            _proxy_index = (_proxy_index + 1) % len(proxies)

        _last_proxy = candidate
        return candidate


def get_proxy_count() -> int:
    """إرجاع عدد البروكسيات الصالحة المحملة من الملف."""
    with _proxy_lock:
        return len(_load_proxies_if_needed())
