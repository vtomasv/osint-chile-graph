import httpx
from app.osint_connectors import SEARCH_ENDPOINT, USER_AGENT

query = "site:diariooficial.interior.gob.cl Chile"
with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
    response = client.get(SEARCH_ENDPOINT, params={"q": query})
print("status", response.status_code)
print("url", str(response.url))
print("length", len(response.text))
print("contains result__a", "result__a" in response.text)
print("contains captcha", "captcha" in response.text.lower())
open("/tmp/ddg_sample.html", "w", encoding="utf-8").write(response.text[:20000])
