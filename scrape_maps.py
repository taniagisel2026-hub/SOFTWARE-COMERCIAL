"""
Extractor Google Maps → CRM
Uso: python scrape_maps.py

Abre el navegador visible. Si aparece CAPTCHA, resuélvelo manualmente.
El script espera hasta que lo resuelvas y luego extrae automáticamente.
Guarda las empresas directamente en la base de datos del CRM.
"""
import sys
import time
import random
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

# ── Configuración ──────────────────────────────────────────────────────────────

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
    "Bogotá",
    "Medellín",
    "Cali",
    "Barranquilla",
    "Bucaramanga",
    "Pereira",
    "Cartagena",
    "Cúcuta",
    "Ibagué",
    "Villavicencio",
]

CIUDAD_DEPARTAMENTO = {
    "Bogotá": "Bogotá D.C.",
    "Medellín": "Antioquia",
    "Cali": "Valle del Cauca",
    "Barranquilla": "Atlántico",
    "Bucaramanga": "Santander",
    "Pereira": "Risaralda",
    "Cartagena": "Bolívar",
    "Cúcuta": "Norte de Santander",
    "Ibagué": "Tolima",
    "Villavicencio": "Meta",
}

MAX_EMPRESAS = 30  # por sesión

# ── Menú de selección ──────────────────────────────────────────────────────────

def elegir(lista: list, titulo: str) -> str:
    print(f"\n{'='*50}")
    print(f"  {titulo}")
    print(f"{'='*50}")
    for i, item in enumerate(lista, 1):
        print(f"  {i}. {item}")
    while True:
        try:
            opcion = int(input(f"\nElige un número (1-{len(lista)}): "))
            if 1 <= opcion <= len(lista):
                return lista[opcion - 1]
        except ValueError:
            pass
        print("  Número inválido, intenta de nuevo.")


# ── Extracción Google Maps ─────────────────────────────────────────────────────

def extraer_google_maps(ciudad: str, sector: str) -> list[dict]:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    query = f"{sector} en {ciudad} Colombia"
    url = f"https://www.google.com/maps/search/{quote(query)}"
    empresas = []

    print(f"\n🌐 Abriendo Google Maps: {query}")
    print("   Si aparece 'No soy un robot', resuélvelo en el navegador.")
    print("   El script espera hasta que los resultados carguen.\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,800",
            ],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="es-CO",
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = ctx.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # Aceptar cookies si aparece
            for btn_text in ["Aceptar todo", "Accept all", "Acepto"]:
                try:
                    btn = page.get_by_text(btn_text, exact=True)
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    pass

            # Esperar feed sin límite de tiempo (el usuario resuelve el CAPTCHA)
            print("   Esperando resultados", end="", flush=True)
            feed_encontrado = False
            for _ in range(120):  # espera hasta 4 minutos
                if page.locator("div[role='feed']").count() > 0:
                    feed_encontrado = True
                    break
                print(".", end="", flush=True)
                time.sleep(2)
            print()

            if not feed_encontrado:
                print("❌ No aparecieron resultados. Intenta de nuevo.")
                browser.close()
                return []

            # Scroll para cargar más resultados
            print("   Cargando más resultados...")
            for _ in range(6):
                page.evaluate("document.querySelector('div[role=\"feed\"]')?.scrollBy(0, 800)")
                time.sleep(random.uniform(1.5, 2.5))

            cards = page.locator("a[href*='/maps/place/']").all()
            print(f"   {len(cards)} empresas encontradas. Extrayendo detalles...\n")

            for i, card in enumerate(cards[:MAX_EMPRESAS]):
                try:
                    nombre = (card.get_attribute("aria-label") or "").strip()
                    if not nombre or len(nombre) < 3:
                        continue
                    nombre = nombre.split(",")[0].strip()

                    # Clic en la card para ver detalles (teléfono, web)
                    card.click()
                    time.sleep(random.uniform(1.5, 2.5))

                    telefono = ""
                    sitio_web = ""
                    direccion = ""

                    try:
                        tel_btn = page.locator("button[data-item-id^='phone']").first
                        if tel_btn.is_visible(timeout=2000):
                            telefono = tel_btn.get_attribute("data-value") or ""
                    except Exception:
                        pass

                    try:
                        web_el = page.locator("a[data-item-id='authority']").first
                        if web_el.is_visible(timeout=2000):
                            sitio_web = web_el.get_attribute("href") or ""
                    except Exception:
                        pass

                    try:
                        addr_btn = page.locator("button[data-item-id^='address']").first
                        if addr_btn.is_visible(timeout=2000):
                            direccion = addr_btn.get_attribute("data-value") or ""
                    except Exception:
                        pass

                    empresa = {
                        "razon_social": nombre,
                        "ciudad": ciudad,
                        "telefono": telefono,
                        "sitio_web": sitio_web,
                        "direccion": direccion,
                    }
                    empresas.append(empresa)

                    tel_txt = f"📞 {telefono}" if telefono else "sin teléfono"
                    web_txt = f"🌐 {sitio_web[:40]}" if sitio_web else "sin web"
                    print(f"  [{i+1:02d}] {nombre[:40]:<40} | {tel_txt} | {web_txt}")

                    # Volver al listado
                    try:
                        page.locator("button[aria-label='Atrás']").first.click(timeout=2000)
                        time.sleep(1)
                    except Exception:
                        page.go_back()
                        time.sleep(1)

                except Exception as e:
                    print(f"  [{i+1:02d}] Error extrayendo empresa: {e}")
                    continue

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            browser.close()

    return empresas


# ── Búsqueda de email en sitio web ────────────────────────────────────────────

def buscar_email_en_web(url: str) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=8)
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", r.text)
        emails = [
            e for e in emails
            if not any(x in e.lower() for x in ["example", "sentry", "schema", "w3", "png", "jpg", "gif"])
        ]
        return emails[0] if emails else ""
    except Exception:
        return ""


# ── Guardar en CRM ────────────────────────────────────────────────────────────

def guardar_en_crm(empresas: list[dict], sector: str, departamento: str) -> tuple[int, int]:
    ROOT = Path(__file__).parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from src.database.connection import get_session
    from src.database.models import EmpresaProspecto
    import uuid

    insertadas = 0
    duplicadas = 0

    with get_session() as session:
        for emp in empresas:
            # Verificar si ya existe por nombre+ciudad
            existe = session.query(EmpresaProspecto).filter(
                EmpresaProspecto.razon_social.ilike(emp["razon_social"]),
                EmpresaProspecto.ciudad.ilike(emp["ciudad"]),
            ).first()
            if existe:
                duplicadas += 1
                continue

            nit = f"GM-{uuid.uuid4().hex[:8].upper()}"
            nueva = EmpresaProspecto(
                razon_social=emp["razon_social"],
                nit=nit,
                ciudad=emp["ciudad"],
                departamento=departamento,
                nivel_riesgo_arl="I",
                num_empleados=10,
                sector_economico=sector,
                telefono=emp.get("telefono") or None,
                email_contacto=emp.get("email") or None,
                direccion=emp.get("direccion") or None,
                estado_prospecto="NUEVO",
                fuente_origen="Google Maps",
                fecha_registro=date.today(),
                fecha_ultima_actualizacion=date.today(),
                opt_out=False,
            )
            session.add(nueva)
            insertadas += 1
        session.commit()

    return insertadas, duplicadas


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*50)
    print("  EXTRACTOR DE PROSPECTOS — MEDINA SST")
    print("="*50)

    sector = elegir(SECTORES, "¿Qué sector quieres buscar?")
    ciudad = elegir(CIUDADES, "¿En qué ciudad?")
    departamento = CIUDAD_DEPARTAMENTO.get(ciudad, "Colombia")

    empresas = extraer_google_maps(ciudad, sector)

    if not empresas:
        print("\nNo se encontraron empresas. Intenta de nuevo.")
        return

    # Buscar emails en los sitios web encontrados
    print(f"\n🔍 Buscando emails en sitios web...")
    con_email = 0
    for emp in empresas:
        if emp.get("sitio_web"):
            email = buscar_email_en_web(emp["sitio_web"])
            if email:
                emp["email"] = email
                con_email += 1
                print(f"  ✉️  {emp['razon_social'][:35]} → {email}")

    # Guardar en CRM
    print(f"\n💾 Guardando en CRM...")
    insertadas, duplicadas = guardar_en_crm(empresas, sector, departamento)

    print(f"\n{'='*50}")
    print(f"  RESUMEN")
    print(f"{'='*50}")
    print(f"  Empresas encontradas : {len(empresas)}")
    print(f"  Con teléfono         : {sum(1 for e in empresas if e.get('telefono'))}")
    print(f"  Con email            : {con_email}")
    print(f"  Nuevas en CRM        : {insertadas}")
    print(f"  Ya existían          : {duplicadas}")
    print(f"{'='*50}")
    print(f"\n✅ Listo. Abre Campañas en el sistema para ver las empresas.\n")


if __name__ == "__main__":
    main()
