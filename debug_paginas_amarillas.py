"""Debug Páginas Amarillas — ver estructura HTML real. Corre: python debug_paginas_amarillas.py"""
from playwright.sync_api import sync_playwright
from urllib.parse import quote

query = "construccion"
ciudad = "Bogota"
url = f"https://www.paginasamarillas.com.co/busqueda/?que={quote(query)}&donde={quote(ciudad)}"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        locale="es-CO",
    ).new_page()

    print(f"Navegando a: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(4000)

    # Probar varios selectores comunes
    selectores = [
        "article",
        "div[class*='result']",
        "div[class*='listing']",
        "div[class*='business']",
        "div[class*='empresa']",
        "div[class*='card']",
        "li[class*='result']",
        "section[class*='result']",
        "a[class*='business']",
        "h2", "h3",
    ]
    for sel in selectores:
        items = page.locator(sel).all()
        if items:
            print(f"Selector '{sel}': {len(items)} elementos")
            if len(items) <= 5:
                for item in items[:3]:
                    print(f"  -> {item.text_content()[:80].strip()}")

    # Tomar screenshot
    page.screenshot(path="debug_pa.png")
    print("\nScreenshot guardado: debug_pa.png")
    print(f"URL actual: {page.url}")
    input("Presiona Enter para cerrar...")
    browser.close()
