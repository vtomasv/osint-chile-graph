import requests
from bs4 import BeautifulSoup
urls = [
    'https://proveedor.mercadopublico.cl/busqueda',
    'https://www.mercadopublico.cl/Home/BusquedaLicitacion',
    'https://api.mercadopublico.cl/servicios/v1/Publico/Empresas/BuscarProveedor?rutempresaproveedor=76960560&ticket=F8537A18-6766-4DEF-9E59-426B4FEE2844',
    'https://tramites.subtel.gob.cl/actos-administrativos/',
    'https://www.diariooficial.interior.gob.cl/',
    'https://www.sii.cl/servicios_online/1047-1690.html',
]
headers={'User-Agent':'Mozilla/5.0 OSINTChileGraph/0.1 (+passive public-source probe)'}
for url in urls:
    print('\nURL', url)
    try:
        r=requests.get(url,headers=headers,timeout=15,allow_redirects=True)
        print('status', r.status_code, 'final', r.url, 'type', r.headers.get('content-type'), 'len', len(r.text))
        text=r.text[:500].replace('\n',' ') if isinstance(r.text,str) else ''
        print('head', text)
        if 'captcha' in r.text.lower() or 'support id' in r.text.lower() or 'challenge' in r.text.lower(): print('BLOCK_HINT yes')
        soup=BeautifulSoup(r.text,'html.parser')
        for a in soup.find_all('a', href=True)[:8]: print(' link', a.get_text(' ',strip=True)[:60], a['href'][:120])
        scripts=[s.get('src') for s in soup.find_all('script') if s.get('src')]
        for s in scripts[:10]: print(' script', s)
    except Exception as e:
        print('error', type(e).__name__, e)
