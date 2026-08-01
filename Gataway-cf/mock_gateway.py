import asyncio

async def process_mock(card_line: str, proxy: str = None):
    # محاكاة تأخير بسيط
    await asyncio.sleep(1)
    return "Success", "Mock Gateway Response: Card Received ✅", True
