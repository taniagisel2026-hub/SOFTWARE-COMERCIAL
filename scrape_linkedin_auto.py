"""
Extractor LinkedIn Automático → CRM
Uso: python scrape_linkedin_auto.py

Primera vez: abre el navegador, inicias sesión una vez, guarda la sesión.
Siguientes veces: corre solo sin necesitar login.
Busca empresas por sector y ciudad, extrae webs y encuentra emails/teléfonos.
"""
import sys
import time
import re
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
SESSION_FILE = ROOT / "linkedin_session.json"

SECTORES = [
    "Construcción",
    "Manufactura / Industria",
    "Transporte y Logística",
    "Comercio y Retail",
    "Servicios Empresariales",
    "Salud y Clínicas",
    "Educación",
    "Alimentos y Bebidas",
    "Seguridad Privada",
    "Ingeniería y Consultoría",
    "Tecnología y Software",
    "Minería y Energía",
]

CIUDADES = [
    "Bogotá", "Medellín", "Cali", "Barranquilla",
    "Bucaramanga", "Pereira", "Cartagena", "Cúcuta",
    "Ibagué", "Villavicencio",
]

CIUDAD_DEPARTAMENTO = {
    "bogotá": "Bogotá D.C.", "bogota": "Bogotá D.C.",
    "medellín": "Antioquia",  "medellin": "Antioquia",
    "cali": "Valle del Cauca",
    "barranquilla": "Atlántico",
    "bucaramanga": "Santander",
    "pereira": "Risaralda",
    "cartagena": "Bolívar",
    "cúcuta": "Norte de Santander",
    "ibagué": "Tolima",
    "villavicencio": "Meta",
}

SECTOR_KEYWORD = {
    "Construcción":             "construcción",
    "Manufactura / Industria":  "manufactura industria",
    "Transporte y Logística":   "transporte logística",
    "Comercio y Retail":        "comercio",
    "Servicios Empresariales":  "servicios empresariales",
    "Salud y Clínicas":         "salud clínica",
    "Educación":                "educación",
    "Alimentos y Bebidas":      "alimentos bebidas",
    "Seguridad Privada":        "seguridad vigilancia",
    "Ingeniería y Consultoría": "ingeniería consultoría",
    "Tecnología y Software":    "tecnología software",
    "Minería y Energía":        "minería energía",
}


def elegir(lista, titulo):
    print(f"\n{'='*50}\n  {titulo}\n{'='*50}")
    for i, item in enumerate(lista, 1):
        print(f"  {i}. {item}")
    while True:
        try:
            op = int(input(f"\nElige (1-{len(lista)}): "))
            if 1 <= op <= len(lista):
                return lista[op - 1]
        except ValueError:
            pass


def buscar_contacto_en_web(url: str) -> tuple[str, str]:
    """Busca email y teléfono en el sitio web corporativo."""
    if not url or not url.startswith("http"):
        return "", ""
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
        base = url.rstrip("/")
        email_found, tel_found = "", ""

        for ruta in ["", "/contacto", "/contactenos", "/contact", "/nosotros", "/about"]:
            try:
                r = requests.get(base + ruta, headers=headers, timeout=8)
                if r.status_code != 200:
                    continue
                texto = r.text
                if not email_found:
                    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", texto)
                    emails = [e for e in emails if not any(x in e.lower() for x in
                              ["example","sentry","schema","w3","png","jpg","gif","wix","wordpress","jquery"])]
                    if emails:
                        email_found = emails[0]
                if not tel_found:
                    tels = re.findall(r'\b(?:\+57[\s\-]?)?(?:60[1-9]|3[0-9]{2})[\s\-]?\d{3}[\s\-]?\d{4}\b', texto)
                    if tels:
                        tel_found = tels[0].strip()
                if email_found and tel_found:
                    break
            except Exception:
                continue
        return email_found, tel_found
    except Exception:
        return "", ""


def guardar_en_crm(empresas: list[dict], sector: str) -> tuple[int, int]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.database.connection import get_session
    from src.database.models import EmpresaProspecto
    import uuid

    insertadas, duplicadas = 0, 0
    with get_session() as session:
        for emp in empresas:
            existe = session.query(EmpresaProspecto).filter(
                EmpresaProspecto.razon_social.ilike(emp["razon_social"])
            ).first()
            if existe:
                duplicadas += 1
                continue
            ciudad_key = emp.get("ciudad", "").lower().strip()
            depto = CIUDAD_DEPARTAMENTO.get(ciudad_key, "Colombia")
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
    from urllib.parse import quote

    print("\n" + "="*58)
    print("  LINKEDIN AUTOMÁTICO → CRM — MEDINA SST")
    print("="*58)

    sector = elegir(SECTORES, "¿Qué sector quieres buscar?")
    ciudad = elegir(CIUDADES, "¿En qué ciudad?")
    keyword = SECTOR_KEYWORD.get(sector, sector)

    tiene_sesion = SESSION_FILE.exists()
    if tiene_sesion:
        print(f"\n✅ Sesión guardada encontrada — entrando automáticamente...")
    else:
        print(f"\n⚠️  Primera vez: deberás iniciar sesión en LinkedIn.")
        print("   Después de eso, las próximas veces será automático.\n")
        input("  Presiona Enter para continuar... ")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--window-size=1280,900",
                  "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="es-CO",
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Cargar cookies guardadas
        if tiene_sesion:
            try:
                cookies = json.loads(SESSION_FILE.read_text())
                ctx.add_cookies(cookies)
                print("  Cookies cargadas.")
            except Exception as e:
                print(f"  Error cargando sesión: {e}. Necesitas iniciar sesión de nuevo.")
                SESSION_FILE.unlink(missing_ok=True)
                tiene_sesion = False

        page = ctx.new_page()

        # Verificar si ya estamos logueados
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20_000)
        time.sleep(3)

        if "login" in page.url or "authwall" in page.url or not tiene_sesion:
            print("\n  Inicia sesión en el navegador que se abrió.")
            print("  Cuando veas tu feed de LinkedIn, vuelve aquí y presiona Enter.")
            input("\n  [Presiona Enter después de iniciar sesión] ")
            time.sleep(2)
            # Guardar cookies para la próxima vez
            cookies = ctx.cookies()
            SESSION_FILE.write_text(json.dumps(cookies))
            print("  ✅ Sesión guardada — la próxima vez será automático.")

        # IDs geográficos LinkedIn para ciudades colombianas
        _GEO = {
            "Bogotá": "102364368", "Medellín": "100996579", "Cali": "106057199",
            "Barranquilla": "104421764", "Bucaramanga": "105255724",
            "Pereira": "105303307", "Cartagena": "100550483",
            "Cúcuta": "105302813", "Ibagué": "105305387", "Villavicencio": "105303044",
        }
        geo_id = _GEO.get(ciudad, "")
        if geo_id:
            search_url = (
                f"https://www.linkedin.com/search/results/companies/"
                f"?keywords={quote(keyword)}&origin=FACETED_SEARCH"
                f"&companyHqGeo=%5B%22{geo_id}%22%5D"
            )
        else:
            search_url = (
                f"https://www.linkedin.com/search/results/companies/"
                f"?keywords={quote(keyword)}&origin=GLOBAL_SEARCH_HEADER"
            )
        print(f"\n🔍 Buscando: {keyword}")
        page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
        time.sleep(4)

        empresas = []
        pagina = 1
        max_paginas = 5  # hasta 50 empresas (10 por página)

        while pagina <= max_paginas:
            print(f"\n  Página {pagina}...")
            time.sleep(2)

            # Esperar resultados y extraer tarjetas
            try:
                page.wait_for_selector("a[href*='/company/']", timeout=8_000)
            except Exception:
                pass
            cards = page.locator("li.reusable-search__result-container").all()
            if not cards:
                cards = page.locator("li[class*='reusable-search']").all()
            if not cards:
                cards = page.locator("li[class*='result']").all()

            if not cards:
                print("  No se encontraron más resultados.")
                break

            for card in cards:
                try:
                    # Nombre
                    nombre = ""
                    for sel in ["span[aria-hidden='true']", "span.entity-result__title-text",
                                "a span[aria-hidden='true']"]:
                        try:
                            el = card.locator(sel).first
                            if el.count() > 0:
                                txt = (el.text_content(timeout=500) or "").strip()
                                if txt and len(txt) > 2 and txt.lower() not in ["linkedin", "ver perfil"]:
                                    nombre = txt
                                    break
                        except Exception:
                            pass

                    if not nombre:
                        continue

                    # Link al perfil
                    link = ""
                    try:
                        a = card.locator("a[href*='/company/']").first
                        if a.count() > 0:
                            link = a.get_attribute("href") or ""
                            if link and not link.startswith("http"):
                                link = "https://www.linkedin.com" + link
                            # Limpiar parámetros
                            link = link.split("?")[0].rstrip("/")
                    except Exception:
                        pass

                    # Empleados desde el snippet
                    num_emp = 10
                    try:
                        snippet = card.text_content(timeout=500) or ""
                        m = re.search(r'(\d[\d.,]+)\s*(?:empleados|seguidores)', snippet, re.I)
                        if m:
                            num_emp = int(re.sub(r'[.,]', '', m.group(1)))
                    except Exception:
                        pass

                    empresas.append({
                        "razon_social": nombre,
                        "ciudad": ciudad,
                        "num_empleados": num_emp,
                        "link": link,
                        "sitio_web": "",
                        "email": "",
                        "telefono": "",
                    })
                    print(f"  ✅ {nombre[:55]}")

                except Exception:
                    continue

            # Siguiente página
            try:
                next_btn = page.locator("button[aria-label='Siguiente']").first
                if next_btn.is_visible(timeout=2000) and next_btn.is_enabled(timeout=2000):
                    next_btn.click()
                    pagina += 1
                    time.sleep(3)
                else:
                    break
            except Exception:
                break

        # Obtener sitio web de cada empresa desde su página "Acerca de"
        print(f"\n🌐 Obteniendo sitios web de {len(empresas)} empresas...")
        for i, emp in enumerate(empresas):
            if not emp["link"]:
                continue
            try:
                about_url = emp["link"] + "/about/"
                page.goto(about_url, wait_until="domcontentloaded", timeout=15_000)
                time.sleep(random_delay())

                # Buscar link externo en la página about
                links = page.locator("a[href^='http']").all()
                for lnk in links:
                    try:
                        href = lnk.get_attribute("href") or ""
                        if href.startswith("http") and "linkedin" not in href and "javascript" not in href:
                            emp["sitio_web"] = href.split("?")[0]
                            break
                    except Exception:
                        pass

                if emp["sitio_web"]:
                    print(f"  [{i+1:02d}] {emp['razon_social'][:40]} → {emp['sitio_web'][:45]}")
                else:
                    print(f"  [{i+1:02d}] {emp['razon_social'][:40]} → sin web")

            except Exception as e:
                print(f"  [{i+1:02d}] Error: {e}")
                continue

        browser.close()

    # Buscar emails y teléfonos en los sitios web
    con_web = sum(1 for e in empresas if e.get("sitio_web"))
    print(f"\n📧 Buscando emails y teléfonos en {con_web} sitios web...")
    con_email, con_tel = 0, 0
    for emp in empresas:
        if emp.get("sitio_web"):
            email, tel = buscar_contacto_en_web(emp["sitio_web"])
            if email:
                emp["email"] = email
                con_email += 1
            if tel:
                emp["telefono"] = tel
                con_tel += 1
            if email or tel:
                print(f"  {emp['razon_social'][:35]:<35} | ✉️ {email or '—':<30} | 📞 {tel or '—'}")

    # Guardar en CRM
    print(f"\n💾 Guardando en CRM...")
    insertadas, duplicadas = guardar_en_crm(empresas, sector)

    print(f"\n{'='*58}")
    print(f"  RESUMEN — {sector} / {ciudad}")
    print(f"{'='*58}")
    print(f"  Empresas encontradas : {len(empresas)}")
    print(f"  Con sitio web        : {con_web}")
    print(f"  Con email            : {con_email}")
    print(f"  Con teléfono         : {con_tel}")
    print(f"  Nuevas en CRM        : {insertadas}")
    print(f"  Ya existían          : {duplicadas}")
    print(f"{'='*58}")
    print(f"\n✅ Listo. Vuelve a correr el script con otro sector o ciudad.\n")


def random_delay():
    import random
    return random.uniform(1.5, 3.0)


def solo_login():
    """Abre el navegador, el usuario inicia sesión, guarda la sesión y sale."""
    from playwright.sync_api import sync_playwright

    print("\n" + "="*55)
    print("  CONFIGURAR SESIÓN LINKEDIN — MEDINA SST")
    print("="*55)
    print("\n  Se abrirá el navegador en LinkedIn.")
    print("  Inicia sesión con tu cuenta.")
    print("  Cuando veas tu feed, vuelve aquí y presiona Enter.\n")
    input("  Presiona Enter para abrir el navegador... ")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="es-CO",
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = ctx.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        input("\n  [Inicia sesión en el navegador y presiona Enter aquí] ")

        cookies = ctx.cookies()
        SESSION_FILE.write_text(json.dumps(cookies))
        browser.close()

    print(f"\n✅ Sesión guardada en {SESSION_FILE}")
    print("   El sistema ahora usará LinkedIn automáticamente.\n")


if __name__ == "__main__":
    import sys as _sys
    if "--solo-login" in _sys.argv:
        solo_login()
    else:
        main()
