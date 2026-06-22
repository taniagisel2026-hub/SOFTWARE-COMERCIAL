"""Script de diagnóstico — corre con: python debug_scraper.py"""
from urllib.parse import quote
from playwright.sync_api import sync_playwright

query = "Construcción en Bogotá Colombia"
url = f"https://www.google.com/maps/search/{quote(query)}"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)  # abre ventana visible
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        locale="es-CO",
    ).new_page()

    print(f"Navegando a: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(4000)

    # Aceptar cookies si aparece el aviso
    for btn_text in ["Aceptar todo", "Accept all", "Acepto", "Aceptar"]:
        try:
            btn = page.get_by_text(btn_text, exact=True)
            if btn.is_visible(timeout=2000):
                btn.click()
                print(f"  → Cookie banner aceptado: '{btn_text}'")
                page.wait_for_timeout(2000)
                break
        except Exception:
            pass

    page.wait_for_timeout(3000)

    # Verificar feed
    feed = page.query_selector("div[role='feed']")
    print(f"Feed encontrado: {feed is not None}")

    # Contar cards
    cards = page.query_selector_all("a[href*='/maps/place/']")
    print(f"Cards encontradas: {len(cards)}")

    if cards:
        for i, c in enumerate(cards[:3]):
            label = c.get_attribute("aria-label") or c.text_content() or ""
            print(f"  Card {i+1}: {label[:80]}")
    else:
        # Screenshot para ver qué muestra la página
        page.screenshot(path="debug_screenshot.png")
        print("Screenshot guardado en debug_screenshot.png")
        print(f"URL actual: {page.url}")
        print(f"Título: {page.title()}")

    input("Presiona Enter para cerrar el navegador...")
    browser.close()
