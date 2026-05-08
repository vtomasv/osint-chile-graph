import requests
from urllib.parse import urlencode
q='"60803000-K" Chile'
url='https://html.duckduckgo.com/html/?'+urlencode({'q':q})
r=requests.get(url,timeout=20,headers={'User-Agent':'Mozilla/5.0 OSINT-Chile-Graph evidence connector; operator-controlled research'})
print(r.status_code,r.url,len(r.text),r.headers.get('content-type'))
print(r.text[:1200].replace('\n',' ')[:1200])
