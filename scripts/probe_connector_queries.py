from app.osint_connectors import public_search

queries = [
    'Tomas Vera Chile',
    'site:diariooficial.interior.gob.cl Tomas Vera',
    '22091655-3 Chile',
    '"22091655-3" Chile',
    'Mercado Público ChileCompra proveedor',
]

for q in queries:
    r = public_search(q, source='probe', max_results=3)
    print('\nQUERY', q, flush=True)
    print('STATUS', r['status'], flush=True)
    print('RESULTS', len(r['results']), flush=True)
    for item in r['results']:
        print('-', item['title'][:90], item['url'][:120], item['snippet'][:120], flush=True)
