import webbrowser
import threading
import time
import re
import gzip
import asyncio
from mitmproxy.tools.dump import DumpMaster
from mitmproxy.options import Options
from mitmproxy import http
TOKEN = None

def watch():
    class Addon:
        def response(self, flow: http.HTTPFlow):
            global TOKEN
            if "recaptcha/enterprise/reload" in flow.request.pretty_url:
                raw_body = flow.response.content               
                try:
                    body = gzip.decompress(raw_body).decode('utf-8', errors='ignore')
                except Exception:
                    body = raw_body.decode('utf-8', errors='ignore')

                m = re.search(r'rresp","(.+?)"', body)
                if m:
                    TOKEN = m.group(1)

    async def run_proxy():
        opts = Options(listen_host="0.0.0.0", listen_port=8080)
        m = DumpMaster(opts, with_termlog=False, with_dumper=False)
        m.addons.add(Addon())
        await m.run()
    asyncio.run(run_proxy())


threading.Thread(target=watch, daemon=True).start()
time.sleep(2)
webbrowser.open(
    "https://recaptcha-demo.appspot.com/recaptcha-v2-invisible.php"
)
print("جاري الانتظار لالتقاط التوكن...")
while TOKEN is None:
    time.sleep(1)
    
print("\nتم الالتقاط بنجاح!")
print("TOKEN =", TOKEN)
