"""
Extractor Páginas Amarillas → CRM
Uso: python scrape_paginas_amarillas.py

Abre el navegador en Páginas Amarillas.
Tú buscas el sector y ciudad manualmente.
Cuando carguen los resultados, el script extrae todo automáticamente.
"""
import sys
import time
import re
from datetime import date
from pathlib import Path

CIUDAD_DEPARTAMENTO = {
    "bogotá": "Bogotá D.C.", "bogota": "Bogotá D.C.",
    "medellín": "Antioquia",  "medellin": "Antioquia",
    "cali": "Valle del Cauca",
    "barranquilla": "Atlántico",
    "bucaramanga": "Santander",
    "pereira": "Risaralda",
    "cartagena": "Bolívar",
    "cúcuta": "Norte de Santander", "cucuta": "Norte de Santander",
    "ibagué": "Tolima",  "ibague": "Tolima",
    "villavicencio": "Meta",
}

def buscar_email_en_web(url: str) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0"}, timeout=8)
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", r.text)
        emails = [e for e in emails if not any(x in e.lower() for x in
                  ["example","sentry","schema","w3","png","jpg","gif","wix","wordpress"])]
        return emails[0] if emails else ""
    except Exception:
        return ""

def guardar_en_crm(empresas: list[dict], sector: str) -> tuple[int, int]:
    ROOT = Path(__file__).parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.database.connection import get_session
    from src.database.models import EmpresaProspecto
    import uuid

    insertadas, duplicadas = 0, 0
    with get_session() as session:
        for emp in empresas:
            existe = session.query(EmpresaProspecto).filter(
                EmpresaProspecto.razon_social.ilike(emp["razon_social"]),
            ).first()
            if existe:
                duplicadas += 1
                continue
            ciudad = emp.get("ciudad", "").lower().strip()
            depto = CIUDAD_DEPARTAMENTO.get(ciudad, "Colombia")
            nueva = EmpresaProspecto(
                razon_social=emp["razon_social"],
                nit=f"PA-{uuid.uuid4().hex[:8].upper()}",
                ciudad=emp.get("ciudad", "Colombia"),
                departamento=depto,
                nivel_riesgo_arl="I",
                num_empleados=10,
                sector_economico=sector,
                telefono=emp.get("telefono") or None,
                email_contacto=emp.get("email") or None,
                direccion=emp.get("direccion") or None,
                estado_prospecto="NUEVO",
                fuente_origen="Páginas Amarillas",
                fecha_registro=date.today(),
                fecha_ultima_actualizacion=date.today(),
                opt_out=False,
            )
            session.add(nueva)
            insertadas += 1
        session.commit()
    return insertadas, duplicadas

def main():
    from playwright.sync_api import sync_playwright

    print("\n" + "="*55)
    print("  EXTRACTOR PÁGINAS AMARILLAS — MEDINA SST")
    print("="*55)
    print("\n  1. Se abrirá el navegador en Páginas Amarillas")
    print("  2. Busca el sector y ciudad que quieras")
    print("  3. Cuando carguen los resultados, presiona Enter aquí")
    print("  4. El script extrae todo automáticamente\n")

    sector = input("¿Qué sector estás buscando? (para guardar en CRM): ").strip() or "General"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--window-size=1280,900"],
        )
        page = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="es-CO",
        ).new_page()

        page.goto("https://www.paginasamarillas.com.co", wait_until="domcontentloaded", timeout=20_000)
        print("\n  Navegador abierto. Busca tu sector y ciudad en la página.")
        print("  Cuando veas los resultados cargados, vuelve aquí y presiona Enter.")
        input("\n  [Presiona Enter cuando los resultados estén visibles] ")

        print("\n  Esperando que la página termine de cargar...")
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        time.sleep(3)

        # Capturar HTML actual de la página de resultados
        try:
            html = page.content()
        except Exception:
            time.sleep(3)
            html = page.content()
        url_actual = page.url
        print(f"  URL: {url_actual}")

        # Intentar extraer con selectores dinámicos
        empresas = []

        # Probar múltiples selectores posibles
        selectores_nombre = [
            "h2[class*='title']", "h2[class*='name']", "h2[class*='business']",
            "h3[class*='title']", "h3[class*='name']",
            "a[class*='name']", "span[class*='name']",
            ".business-name", ".company-name", ".result-name",
        ]
        selectores_tel = [
            "[class*='phone']", "[class*='tel']", "[class*='telefono']",
            "span[class*='number']", "a[href^='tel:']",
        ]
        selectores_web = [
            "a[href^='http'][class*='web']", "a[href^='http'][class*='site']",
            "a[class*='website']", "a[class*='url']",
        ]

        # Intentar encontrar tarjetas de empresas
        cards = []
        for sel in ["article", "li[class*='result']", "div[class*='result']",
                    "div[class*='listing']", "div[class*='business']", "div[class*='card']"]:
            found = page.locator(sel).all()
            if len(found) > 2:
                cards = found
                print(f"  Selector usado: {sel} | {len(cards)} elementos")
                break

        if cards:
            for card in cards[:50]:
                try:
                    nombre = ""
                    for sel in selectores_nombre:
                        try:
                            el = card.locator(sel).first
                            if el.count() > 0:
                                nombre = el.text_content(timeout=500) or ""
                                if nombre.strip():
                                    break
                        except Exception:
                            pass

                    if not nombre.strip():
                        # Último recurso: texto del primer heading
                        for tag in ["h2", "h3", "h4"]:
                            try:
                                el = card.locator(tag).first
                                if el.count() > 0:
                                    nombre = el.text_content(timeout=500) or ""
                                    if nombre.strip():
                                        break
                            except Exception:
                                pass

                    if not nombre.strip() or len(nombre.strip()) < 3:
                        continue

                    telefono = ""
                    for sel in selectores_tel:
                        try:
                            el = card.locator(sel).first
                            if el.count() > 0:
                                tel = el.get_attribute("href") or el.text_content(timeout=500) or ""
                                tel = tel.replace("tel:", "").strip()
                                if tel:
                                    telefono = tel
                                    break
                        except Exception:
                            pass

                    sitio_web = ""
                    for sel in selectores_web:
                        try:
                            el = card.locator(sel).first
                            if el.count() > 0:
                                href = el.get_attribute("href") or ""
                                if href.startswith("http") and "paginasamarillas" not in href:
                                    sitio_web = href
                                    break
                        except Exception:
                            pass

                    # Buscar tel en href tel:
                    if not telefono:
                        try:
                            tel_links = card.locator("a[href^='tel:']").all()
                            if tel_links:
                                telefono = (tel_links[0].get_attribute("href") or "").replace("tel:", "").strip()
                        except Exception:
                            pass

                    # Buscar web en links externos
                    if not sitio_web:
                        try:
                            links = card.locator("a[href^='http']").all()
                            for lnk in links:
                                href = lnk.get_attribute("href") or ""
                                if "paginasamarillas" not in href and href.startswith("http"):
                                    sitio_web = href
                                    break
                        except Exception:
                            pass

                    empresa = {
                        "razon_social": nombre.strip(),
                        "ciudad": "",
                        "telefono": telefono,
                        "sitio_web": sitio_web,
                    }
                    empresas.append(empresa)

                    tel_txt = f"📞 {telefono}" if telefono else "sin tel"
                    web_txt = f"🌐 {sitio_web[:35]}" if sitio_web else "sin web"
                    print(f"  ✅ {nombre.strip()[:40]:<40} | {tel_txt} | {web_txt}")

                except Exception:
                    continue
        else:
            # Si no encontramos cards, buscar con BeautifulSoup en el HTML
            print("  Intentando extracción alternativa del HTML...")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            # Buscar todos los números de teléfono en la página
            telefonos = re.findall(r'\b(?:\+57\s?)?(?:60[1-9]|3[0-9]{2})\s?\d{3}\s?\d{4}\b', html)
            print(f"  Teléfonos encontrados en HTML: {telefonos[:10]}")
            # Buscar URLs externas
            links = soup.select("a[href^='http']")
            externos = [l['href'] for l in links if 'paginasamarillas' not in l['href']]
            print(f"  URLs externas: {externos[:5]}")

        browser.close()

    if not empresas:
        print("\n⚠️  No se pudieron extraer empresas automáticamente.")
        print("   Prueba con el script de Google Maps: python scrape_maps.py")
        return

    # Buscar emails en sitios web
    print(f"\n🔍 Buscando emails en {sum(1 for e in empresas if e.get('sitio_web'))} sitios web...")
    con_email = 0
    for emp in empresas:
        if emp.get("sitio_web"):
            email = buscar_email_en_web(emp["sitio_web"])
            if email:
                emp["email"] = email
                con_email += 1
                print(f"  ✉️  {emp['razon_social'][:35]} → {email}")

    # Pedir ciudad al usuario
    ciudad = input("\n¿En qué ciudad buscaste? (ej: Bogotá): ").strip()
    for emp in empresas:
        emp["ciudad"] = ciudad

    # Guardar en CRM
    print(f"\n💾 Guardando {len(empresas)} empresas en CRM...")
    insertadas, duplicadas = guardar_en_crm(empresas, sector)

    print(f"\n{'='*55}")
    print(f"  RESUMEN")
    print(f"{'='*55}")
    print(f"  Empresas extraídas   : {len(empresas)}")
    print(f"  Con teléfono         : {sum(1 for e in empresas if e.get('telefono'))}")
    print(f"  Con email            : {con_email}")
    print(f"  Nuevas en CRM        : {insertadas}")
    print(f"  Ya existían          : {duplicadas}")
    print(f"{'='*55}")
    print(f"\n✅ Listo. Abre Campañas en el sistema para ver las empresas.\n")

if __name__ == "__main__":
    main()
