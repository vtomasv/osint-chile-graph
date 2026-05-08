import re
import requests
from urllib.parse import quote_plus

queries = [
    '"60805000-0" Chile',
    'site:diariooficial.interior.gob.cl "60805000-0"',
    'Banco Estado Chile',
]
headers = {"User-Agent": "Mozilla/5.0 OSINT-Chile-Graph responsible-public-osint"}
for q in queries:
    url = "https://lite.duckduckgo.com/lite/?q=" + quote_plus(q)
    resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    print("QUERY", q)
    print("URL", resp.url, "STATUS", resp.status_code, "LEN", len(resp.text), "TYPE", resp.headers.get("content-type"))
    print("MARKERS", "result-link" in resp.text, "result-link" , resp.text.count("result-link"), "web-result" in resp.text)
    for m in re.finditer(r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', resp.text, flags=re.I|re.S):
        title = re.sub(r'<[^>]+>', ' ', m.group(2))
        print("RESULT", title.strip()[:120], m.group(1)[:160])
        break
    print(resp.text[:300].replace('\n', ' '))
