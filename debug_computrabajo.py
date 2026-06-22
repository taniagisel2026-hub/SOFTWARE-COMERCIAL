"""Debug Computrabajo — ver estructura HTML. Corre: python debug_computrabajo.py"""
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-CO,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Intentar varias URLs posibles
urls = [
    "https://co.computrabajo.com/trabajo-de-construccion",
    "https://co.computrabajo.com/ofertas-de-trabajo?q=construccion&l=Bogota",
    "https://co.computrabajo.com/trabajo-de-construccion-en-bogota",
]

for url in urls:
    print(f"\nProbando: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"  Status: {r.status_code} | URL final: {r.url}")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            # Buscar artículos de empleo
            for sel in ["article", "div[class*='offer']", "div[class*='job']", "li[class*='offer']"]:
                items = soup.select(sel)
                if items:
                    print(f"  Selector '{sel}': {len(items)} elementos")
                    for item in items[:2]:
                        print(f"    -> {item.get_text()[:100].strip()}")
                    break
            # Buscar emails en la página
            import re
            emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', r.text)
            emails = [e for e in emails if not any(x in e for x in ['computrabajo', 'example', 'sentry'])]
            if emails:
                print(f"  Emails encontrados: {emails[:5]}")
    except Exception as e:
        print(f"  Error: {e}")

print("\nListo.")
