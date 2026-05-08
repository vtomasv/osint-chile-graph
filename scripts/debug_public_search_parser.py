from app.osint_connectors import public_search

for query in ["site:diariooficial.interior.gob.cl Chile", "Tomás Vera Chile", "22091655-3 Chile"]:
    out = public_search(query, source="debug", max_results=5)
    print("QUERY", query)
    print("STATUS", out["status"])
    print("RESULTS", len(out["results"]))
    for result in out["results"]:
        print(" -", result)
