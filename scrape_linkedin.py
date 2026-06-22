"""
Extractor LinkedIn → CRM
Uso: python scrape_linkedin.py

Abre el navegador en LinkedIn.
Tú inicias sesión y buscas empresas del sector.
Cuando veas los resultados, presionas Enter aquí.
El script extrae nombre, ciudad y sitio web, luego busca el email en cada web.
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
    "villavicencio": "Meta",
}


def buscar_email_y_telefono_en_web(url: str) -> tuple[str, str]:
    """Visita el sitio web de la empresa y busca email y teléfono."""
    if not url or not url.startswith("http"):
        return "", ""
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
        # Intentar página principal y /contacto
        urls_a_revisar = [url, url.rstrip("/") + "/contacto",
                          url.rstrip("/") + "/contactenos", url.rstrip("/") + "/contact"]
        email_encontrado = ""
        tel_encontrado = ""

        for u in urls_a_revisar:
            try:
                r = requests.get(u, headers=headers, timeout=8, allow_redirects=True)
                if r.status_code != 200:
                    continue
                texto = r.text

                # Emails
                if not email_encontrado:
                    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", texto)
                    emails = [e for e in emails if not any(x in e.lower() for x in
                              ["example", "sentry", "schema", "w3", "png", "jpg", "gif",
                               "wix", "wordpress", "jquery", "bootstrap"])]
                    if emails:
                        email_encontrado = emails[0]

                # Teléfonos colombianos
                if not tel_encontrado:
                    tels = re.findall(
                        r'\b(?:\+57[\s\-]?)?(?:60[1-9]|3[0-9]{2})[\s\-]?\d{3}[\s\-]?\d{4}\b', texto
                    )
                    if tels:
                        tel_encontrado = tels[0].strip()

                if email_encontrado and tel_encontrado:
                    break
            except Exception:
                continue

        return email_encontrado, tel_encontrado
    except Exception:
        return "", ""


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
                nit=f"LI-{uuid.uuid4().hex[:8].upper()}",
                ciudad=emp.get("ciudad", "Colombia"),
                departamento=depto,
                nivel_riesgo_arl="I",
                num_empleados=emp.get("num_empleados", 10),
                sector_economico=sector,
                telefono=emp.get("telefono") or None,
                email_contacto=emp.get("email") or None,
                direccion=None,
                estado_prospecto="NUEVO",
                fuente_origen="LinkedIn",
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

    print("\n" + "="*58)
    print("  EXTRACTOR LINKEDIN → CRM — MEDINA SST")
    print("="*58)
    print("""
  PASOS:
  1. Se abre el navegador en LinkedIn
  2. Inicia sesión con tu cuenta
  3. Busca empresas: Ej: 'empresas construcción Bogotá'
     → Haz clic en 'Empresas' en los filtros de búsqueda
  4. Cuando veas la lista de empresas, vuelve aquí y presiona Enter
  5. El script extrae los datos y busca emails en sus webs
""")

    sector = input("¿Qué sector buscas? (para CRM): ").strip() or "General"
    ciudad = input("¿En qué ciudad? (para CRM): ").strip() or "Bogotá"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--window-size=1280,900", "--start-maximized"],
        )
        page = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="es-CO",
        ).new_page()

        page.goto("https://www.linkedin.com/search/results/companies/", wait_until="domcontentloaded")
        print("\n  Navegador abierto. Inicia sesión en LinkedIn y busca las empresas.")
        print("  Filtra por 'Empresas' para ver la lista de tarjetas.")
        input("\n  [Presiona Enter cuando veas la lista de empresas] ")

        print("\n  Esperando que la página termine de cargar...")
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        time.sleep(3)

        # Extraer tarjetas de empresa
        empresas_raw = []

        # Selectores de LinkedIn para resultados de empresas
        cards = page.locator("li.reusable-search__result-container").all()
        if not cards:
            cards = page.locator("li[class*='result']").all()
        if not cards:
            cards = page.locator("div[data-view-name*='search-entity']").all()

        print(f"  {len(cards)} tarjetas encontradas.")

        for card in cards:
            try:
                # Nombre de la empresa
                nombre = ""
                for sel in ["span[aria-hidden='true']", "span.entity-result__title-text",
                            "a[class*='title'] span", "span[class*='name']", "h3", "h4"]:
                    try:
                        el = card.locator(sel).first
                        if el.count() > 0:
                            txt = el.text_content(timeout=500) or ""
                            if txt.strip() and len(txt.strip()) > 2:
                                nombre = txt.strip()
                                break
                    except Exception:
                        pass

                if not nombre:
                    continue

                # URL del perfil de LinkedIn (para luego ir a la web)
                link_perfil = ""
                try:
                    a = card.locator("a[href*='linkedin.com/company']").first
                    if a.count() > 0:
                        link_perfil = a.get_attribute("href") or ""
                except Exception:
                    pass

                # Número de empleados si aparece
                num_emp = 10
                try:
                    snippet = card.text_content(timeout=500) or ""
                    match = re.search(r'(\d[\d.,]+)\s*(?:empleados|employees|seguidores)', snippet, re.I)
                    if match:
                        num_emp = int(re.sub(r'[.,]', '', match.group(1)))
                except Exception:
                    pass

                empresas_raw.append({
                    "razon_social": nombre,
                    "ciudad": ciudad,
                    "num_empleados": num_emp,
                    "link_perfil": link_perfil,
                    "sitio_web": "",
                    "email": "",
                    "telefono": "",
                })
                print(f"  ✅ {nombre[:50]}")

            except Exception:
                continue

        # Visitar cada perfil de LinkedIn para obtener el sitio web
        if empresas_raw:
            print(f"\n  Buscando sitio web en {len(empresas_raw)} perfiles de LinkedIn...")
            for emp in empresas_raw:
                if not emp["link_perfil"]:
                    continue
                try:
                    page.goto(emp["link_perfil"], wait_until="domcontentloaded", timeout=15_000)
                    time.sleep(2)
                    # Buscar el sitio web en la página "Acerca de"
                    about_url = emp["link_perfil"].rstrip("/") + "/about/"
                    page.goto(about_url, wait_until="domcontentloaded", timeout=10_000)
                    time.sleep(1.5)
                    # Buscar link externo
                    links = page.locator("a[href^='http']").all()
                    for lnk in links:
                        href = lnk.get_attribute("href") or ""
                        if "linkedin" not in href and href.startswith("http"):
                            emp["sitio_web"] = href
                            print(f"  🌐 {emp['razon_social'][:35]} → {href[:50]}")
                            break
                except Exception:
                    pass

        browser.close()

    if not empresas_raw:
        print("\n⚠️  No se encontraron empresas. Asegúrate de filtrar por 'Empresas' en LinkedIn.")
        return

    # Buscar email y teléfono en cada sitio web
    con_email = 0
    con_tel = 0
    webs = sum(1 for e in empresas_raw if e.get("sitio_web"))
    if webs:
        print(f"\n🔍 Buscando emails y teléfonos en {webs} sitios web...")
        for emp in empresas_raw:
            if emp.get("sitio_web"):
                email, tel = buscar_email_y_telefono_en_web(emp["sitio_web"])
                if email:
                    emp["email"] = email
                    con_email += 1
                if tel:
                    emp["telefono"] = tel
                    con_tel += 1
                if email or tel:
                    print(f"  {emp['razon_social'][:35]:<35} | ✉️ {email or '—'} | 📞 {tel or '—'}")

    # Guardar en CRM
    print(f"\n💾 Guardando {len(empresas_raw)} empresas en CRM...")
    insertadas, duplicadas = guardar_en_crm(empresas_raw, sector)

    print(f"\n{'='*58}")
    print(f"  RESUMEN")
    print(f"{'='*58}")
    print(f"  Empresas encontradas : {len(empresas_raw)}")
    print(f"  Con sitio web        : {webs}")
    print(f"  Con email            : {con_email}")
    print(f"  Con teléfono         : {con_tel}")
    print(f"  Nuevas en CRM        : {insertadas}")
    print(f"  Ya existían          : {duplicadas}")
    print(f"{'='*58}")
    print(f"\n✅ Listo. Abre Campañas para ver las empresas.\n")


if __name__ == "__main__":
    main()
