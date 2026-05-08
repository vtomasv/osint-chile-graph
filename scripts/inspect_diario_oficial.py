import requests
from bs4 import BeautifulSoup
urls=['https://www.diariooficial.interior.gob.cl/','https://www.diariooficial.interior.gob.cl/verificacion/','https://www.diariooficial.interior.gob.cl/edicionelectronica/','https://www.diariooficial.interior.gob.cl/versiones-anteriores/']
headers={'User-Agent':'Mozilla/5.0 OSINTChileGraph/0.1'}
for url in urls:
    print('\nURL',url)
    r=requests.get(url,headers=headers,timeout=20)
    print('status',r.status_code,'len',len(r.text),'final',r.url)
    soup=BeautifulSoup(r.text,'html.parser')
    for form in soup.find_all('form'):
        print(' form method',form.get('method'),'action',form.get('action'))
        for inp in form.find_all(['input','select','textarea'])[:20]: print('  field',inp.name,inp.get('name'),inp.get('id'),inp.get('type'),inp.get('value'))
    for a in soup.find_all('a',href=True):
        txt=a.get_text(' ',strip=True)
        href=a['href']
        if any(k in (txt+' '+href).lower() for k in ['buscar','cve','verificar','edicion','electr']):
            print(' link',txt[:80],href[:180])
