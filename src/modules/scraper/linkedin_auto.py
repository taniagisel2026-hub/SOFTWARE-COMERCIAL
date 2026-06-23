"""
LinkedInAutoScraper — usa sesión guardada, extrae datos completos de empresas.
Para crear sesión: python scrape_linkedin_auto.py --solo-login
"""
import json
import random
import re
import time
from pathlib import Path

from .base import BaseScraperAdapter, ProspectoExtraido, estimar_nivel_riesgo

_ROOT = Path(__file__).parent.parent.parent.parent
SESSION_FILE = _ROOT / "linkedin_session.json"

_SECTOR_KEYWORD: dict[str, str] = {
    "construcción":             "construcción",
    "construccion":             "construcción",
    "manufactura / industria":  "manufactura industria",
    "manufactura":              "manufactura",
    "transporte y logística":   "transporte logística",
    "transporte":               "transporte",
    "comercio y retail":        "comercio",
    "comercio":                 "comercio",
    "servicios empresariales":  "servicios empresariales",
    "salud y clínicas":         "salud clínica",
    "salud":                    "salud",
    "educación":                "educación",
    "alimentos y bebidas":      "alimentos bebidas",
    "seguridad privada":        "seguridad vigilancia",
    "ingeniería y consultoría": "ingeniería consultoría",
    "tecnología y software":    "tecnología software",
    "tecnología":               "tecnología",
    "minería y energía":        "minería energía",
    "minería":                  "minería",
}

_CIUDAD_DEPARTAMENTO: dict[str, str] = {
    "bogotá d.c.": "Bogotá D.C.", "bogotá": "Bogotá D.C.", "bogota": "Bogotá D.C.",
    "medellín": "Antioquia",      "medellin": "Antioquia",
    "cali": "Valle del Cauca",
    "barranquilla": "Atlántico",
    "bucaramanga": "Santander",
    "pereira": "Risaralda",
    "cartagena": "Bolívar",
    "cúcuta": "Norte de Santander", "cucuta": "Norte de Santander",
    "ibagué": "Tolima",            "ibague": "Tolima",
    "villavicencio": "Meta",
}

# Palabras que identifican que la tarjeta es de Colombia
_PALABRAS_COLOMBIA = [
    "Bogotá","Bogota","Medellín","Medellin","Cali","Barranquilla",
    "Bucaramanga","Pereira","Cartagena","Cúcuta","Cucuta","Ibagué","Ibague",
    "Villavicencio","Manizales","Pasto","Armenia","Neiva","Montería",
    "Colombia","Cundinamarca","Antioquia","Atlántico","Santander",
]


class LinkedInSinSesionError(Exception):
    pass


class LinkedInAutoScraper(BaseScraperAdapter):
    SOURCE = "LinkedIn"

    def __init__(self, max_paginas: int = 10, delay: float = 2.0):
        self._max_paginas = max_paginas
        self._delay = delay

    @staticmethod
    def sesion_existe() -> bool:
        return SESSION_FILE.exists()

    # ── JavaScript: extrae tarjetas de la página de resultados ───────────────

    _JS_LISTA = r"""
    () => {
        const seen = new Set();
        const results = [];

        // Buscar directamente todos los <a href*="/company/"> sin depender de <li>
        document.querySelectorAll('a[href*="/company/"]').forEach(a => {
            const href = a.href.split('?')[0].replace(/\/+$/, '');
            if (!href || seen.has(href)) return;
            // Ignorar sub-páginas y páginas genéricas
            if (/\/company\/(people|jobs|posts|videos|about|services|life)\b/.test(href)) return;
            if (/\/company\/?$/.test(href)) return;

            // ── Nombre: intentar varias fuentes ──────────────────────────
            let name = '';

            // 1. aria-label del propio link
            name = (a.getAttribute('aria-label') || '').trim();
            name = name.replace(/^(Ver página de empresa para|View company page for)\s*/i, '');

            // 2. Heading más cercano (h3/h4) subiendo por el DOM
            if (!name || name.length < 2) {
                let el = a.parentElement;
                for (let i = 0; i < 8 && el; i++) {
                    const h = el.querySelector('h1,h2,h3,h4,[role="heading"]');
                    if (h) {
                        const sp = h.querySelector('span[aria-hidden="true"]') || h;
                        name = (sp.textContent || '').trim().split('\n')[0].trim();
                        break;
                    }
                    el = el.parentElement;
                }
            }

            // 3. Texto del propio link como fallback
            if (!name || name.length < 2) {
                name = (a.textContent || '').trim().split('\n')[0].trim();
            }

            // Limpiar nombre
            name = name.replace(/\s*(Seguir|Follow|Ver perfil|View profile)[\s\S]*$/i, '').trim();
            name = name.replace(/[\s·\-–|,]+$/, '').trim();

            if (!name || name.length < 2) return;
            // Filtrar nombres falsos que LinkedIn pone cuando detecta bots
            const invalidos = ['LinkedIn','Ver perfil','Seguir','Follow','Inicio','Home',
                'Opciones de publicidad','Advertising options','Publicidad','Ad options'];
            if (invalidos.some(v => name.toLowerCase().includes(v.toLowerCase()))) return;

            seen.add(href);
            results.push({ href, name });
        });
        return results;
    }
    """

    # ── JavaScript: extrae datos de la página "Acerca de" ────────────────────

    _JS_ABOUT = r"""
    () => {
        const data = { web: '', telefono: '', empleados: 0, ciudad: '' };

        // Sitio web: primer link externo (no linkedin)
        for (const a of document.querySelectorAll('a[href^="http"]')) {
            if (!a.href.includes('linkedin.com') && !a.href.includes('javascript')) {
                data.web = a.href.split('?')[0];
                break;
            }
        }

        // Teléfono: link tel: primero
        const telLink = document.querySelector('a[href^="tel:"]');
        if (telLink) {
            data.telefono = telLink.href.replace('tel:', '').replace(/\s/g, '').trim();
        }
        if (!data.telefono) {
            const body = document.body.innerText || '';
            const m = body.match(/\(?\+?57[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4}|\b[36]\d{9}\b|\(\d{3}\)\s?\d{7}/);
            if (m) data.telefono = m[0].trim();
        }

        // Empleados
        const bodyTxt = document.body.innerText || '';
        let m = bodyTxt.match(/(\d[\d.,]*)\s*[\-–]\s*(\d[\d.,]*)\s*empleados/i);
        if (m) {
            data.empleados = parseInt(m[2].replace(/[.,]/g, ''));
        } else {
            m = bodyTxt.match(/(\d[\d.,]+)\s*empleados/i);
            if (m) data.empleados = parseInt(m[1].replace(/[.,]/g, ''));
        }

        // Ciudad real: buscar sección "Sede principal" o "Headquarters"
        const etiquetas = ['Sede principal','Headquarters','Ubicación','Location'];
        const todos = Array.from(document.querySelectorAll('dt, h3, span, div, p'));
        for (const el of todos) {
            const txt = (el.textContent || '').trim();
            if (etiquetas.some(e => txt === e)) {
                // El valor está en el siguiente sibling o dentro del padre
                const next = el.nextElementSibling;
                if (next) { data.ciudad = next.textContent.trim().split(',')[0].trim(); break; }
                const parent = el.parentElement;
                if (parent) {
                    const val = parent.textContent.replace(txt, '').trim().split(',')[0].trim();
                    if (val) { data.ciudad = val; break; }
                }
            }
        }
        // Fallback: buscar ciudad colombiana en el texto visible
        if (!data.ciudad) {
            const ciudades = ['Bogotá','Medellín','Cali','Barranquilla','Bucaramanga',
                'Pereira','Cartagena','Cúcuta','Ibagué','Villavicencio','Manizales',
                'Pasto','Armenia','Neiva','Montería','Sincelejo','Valledupar','Popayán'];
            for (const c of ciudades) {
                if (bodyTxt.includes(c)) { data.ciudad = c; break; }
            }
        }

        return data;
    }
    """

    def extraer(
        self,
        ciudad: str,
        sector: str,
        max_resultados: int = 30,
    ) -> list[ProspectoExtraido]:
        if not SESSION_FILE.exists():
            raise LinkedInSinSesionError(
                "Sesión LinkedIn no configurada. "
                "Corre: python scrape_linkedin_auto.py --solo-login"
            )

        from playwright.sync_api import sync_playwright
        from urllib.parse import quote

        ciudad_norm = ciudad.lower().strip()
        depto = _CIUDAD_DEPARTAMENTO.get(ciudad_norm, "Colombia")
        nivel_riesgo = estimar_nivel_riesgo(sector)
        keyword = _SECTOR_KEYWORD.get(sector.lower().strip(), sector)

        prospectos: list[ProspectoExtraido] = []

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

            # Cargar sesión guardada
            try:
                cookies = json.loads(SESSION_FILE.read_text())
                ctx.add_cookies(cookies)
            except Exception as exc:
                browser.close()
                raise LinkedInSinSesionError(f"Error cargando sesión: {exc}") from exc

            page = ctx.new_page()

            # Verificar sesión activa
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20_000)
            time.sleep(2)
            if "login" in page.url or "authwall" in page.url:
                browser.close()
                SESSION_FILE.unlink(missing_ok=True)
                raise LinkedInSinSesionError(
                    "Sesión expirada. Corre: python scrape_linkedin_auto.py --solo-login"
                )

            # ── Paso 1: Buscar ──────────────────────────────────────────────
            search_url = (
                "https://www.linkedin.com/search/results/companies/"
                f"?keywords={quote(keyword)}&origin=GLOBAL_SEARCH_HEADER"
            )
            page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
            time.sleep(3)

            # ── Paso 2: Aplicar filtro de ciudad ────────────────────────────
            # Simplificar el nombre: "Bogotá D.C." → "Bogotá", "Medellín" → "Medellín"
            ciudad_busqueda = ciudad.split(" D.C.")[0].split(",")[0].strip()
            self._aplicar_filtro_ciudad(page, ciudad_busqueda)

            # ── Paso 3: Recolectar links de empresas (hasta 10 páginas) ─────
            empresas_raw: list[dict] = []
            max_pag = min(10, max(1, max_resultados // 10 + 1))

            for pagina in range(1, max_pag + 1):
                print(f"  Página {pagina}...")
                try:
                    # Sin 'li' — LinkedIn puede usar div u otros contenedores
                    page.wait_for_selector("a[href*='/company/']", timeout=12_000)
                    time.sleep(1.5)
                except Exception:
                    print(f"  No cargaron resultados en página {pagina}.")
                    break

                items: list[dict] = page.evaluate(self._JS_LISTA) or []
                nuevos = 0
                for item in items:
                    if len(empresas_raw) >= max_resultados:
                        break
                    nombre = item.get("name", "").strip()
                    link   = item.get("href", "").strip()

                    if not nombre or not link:
                        continue
                    if any(e["link"] == link for e in empresas_raw):
                        continue

                    empresas_raw.append({"nombre": nombre, "link": link})
                    nuevos += 1
                    print(f"    [{len(empresas_raw):03d}] {nombre}")

                if len(empresas_raw) >= max_resultados:
                    break

                # Siguiente página
                avanzado = False
                for sel in [
                    "button[aria-label='Siguiente']",
                    "button[aria-label='Next']",
                    "button.artdeco-pagination__button--next",
                    "li.artdeco-pagination__button--next button",
                ]:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=2000) and btn.is_enabled(timeout=1000):
                            btn.click()
                            time.sleep(2.5)
                            avanzado = True
                            break
                    except Exception:
                        pass

                if not avanzado:
                    # Intentar clic en el número de página siguiente
                    try:
                        btn = page.locator(f"button[aria-label='{pagina + 1}'], button:has-text('{pagina + 1}')").first
                        if btn.is_visible(timeout=1500):
                            btn.click()
                            time.sleep(2.5)
                            avanzado = True
                    except Exception:
                        pass

                if not avanzado:
                    print(f"  No hay más páginas.")
                    break

            print(f"  Total empresas encontradas: {len(empresas_raw)}")

            # ── Paso 4: Visitar Acerca de y extraer web, tel, empleados ─────
            # Límite de seguridad: máximo 50 empresas por sesión para no activar el sistema de LinkedIn
            MAX_DIARIO = 50
            if len(empresas_raw) > MAX_DIARIO:
                print(f"  [Seguridad] Limitando a {MAX_DIARIO} empresas (tenía {len(empresas_raw)}) para proteger la cuenta")
                empresas_raw = empresas_raw[:MAX_DIARIO]

            for i, emp in enumerate(empresas_raw):
                web, telefono, empleados = "", "", 0
                about_url = emp["link"].rstrip("/") + "/about/"

                # Pausa larga cada 20 empresas para imitar comportamiento humano
                if i > 0 and i % 20 == 0:
                    pausa = 90 + (i * 2)  # 90s en empresa 20, 130s en empresa 40
                    print(f"  [Seguridad] Pausa de {pausa}s después de {i} empresas...")
                    time.sleep(pausa)

                try:
                    page.goto(about_url, wait_until="domcontentloaded", timeout=15_000)

                    # Detectar si LinkedIn pidió verificación — parar inmediatamente
                    url_actual = page.url.lower()
                    if "checkpoint" in url_actual or "challenge" in url_actual or "authwall" in url_actual:
                        print(f"  ⛔ LinkedIn solicitó verificación en empresa {i+1}. Deteniendo para proteger la cuenta.")
                        break

                    try:
                        page.wait_for_selector("section, main", timeout=5_000)
                    except Exception:
                        pass
                    time.sleep(random.uniform(3, 7))  # delay humano entre páginas

                    data = page.evaluate(self._JS_ABOUT) or {}
                    web       = data.get("web", "") or ""
                    telefono  = data.get("telefono", "") or ""
                    empleados = int(data.get("empleados", 0) or 0)
                    ciudad_real = data.get("ciudad", "").strip() or ciudad
                    depto_real  = _CIUDAD_DEPARTAMENTO.get(ciudad_real.lower(), depto)

                    tag = "✅" if (web or telefono) else "·"
                    print(f"    [{i+1:03d}] {emp['nombre'][:38]} | {ciudad_real} {tag} tel={telefono or '—'}")
                except Exception as e:
                    ciudad_real = ciudad
                    depto_real  = depto
                    web = telefono = ""
                    empleados = 0
                    print(f"    [{i+1:03d}] {emp['nombre'][:45]} ERROR about: {e}")

                # Solo agregar si tiene algún dato de contacto útil
                if not web and not telefono:
                    print(f"    [{i+1:03d}] OMITIDO — sin web ni teléfono")
                    continue

                prospectos.append(ProspectoExtraido(
                    razon_social=emp["nombre"],
                    ciudad=ciudad_real,
                    departamento=depto_real,
                    fuente=self.SOURCE,
                    sector_economico=sector,
                    sitio_web=web,
                    telefono=telefono,
                    num_empleados=empleados,
                    nivel_riesgo_arl=nivel_riesgo,
                    confianza=0.8,
                ))

            browser.close()

        return prospectos

    # ── Aplicar filtro de ciudad ──────────────────────────────────────────────

    @staticmethod
    def _aplicar_filtro_ciudad(page, ciudad: str) -> None:
        """
        Clic en 'Ubicaciones' → escribe la ciudad → primera sugerencia → Mostrar resultados.
        Guarda capturas de pantalla en debug_li_*.png para diagnóstico visual.
        """
        _DBG = _ROOT / "debug_li_{}.png"

        def snap(nombre: str):
            try:
                page.screenshot(path=str(_DBG).format(nombre))
                print(f"  [filtro ciudad] 📸 debug_li_{nombre}.png guardada")
            except Exception:
                pass

        try:
            time.sleep(2)
            snap("1_antes_ubicaciones")

            # 1. Clic en botón Ubicaciones — busca en buttons y divs con role=button
            res_btn = page.evaluate("""() => {
                const todos = Array.from(document.querySelectorAll(
                    'button, [role="button"], [role="tab"]'
                ));
                const btn = todos.find(b => {
                    const t = (b.innerText || b.textContent || b.getAttribute('aria-label') || '')
                               .toLowerCase();
                    return t.includes('ubicaci') || t.includes('location');
                });
                if (btn) {
                    btn.scrollIntoView({block:'center'});
                    btn.click();
                    return 'OK:' + (btn.innerText || btn.getAttribute('aria-label') || '').trim().slice(0,50);
                }
                const etiquetas = todos.slice(0,25).map(b =>
                    (b.innerText || b.getAttribute('aria-label') || '').trim().slice(0,20)
                );
                return 'FAIL:' + etiquetas.join(' | ');
            }""")
            print(f"  [filtro ciudad] Ubicaciones: {res_btn}")

            if "FAIL" in res_btn:
                snap("1b_ubicaciones_fallo")
                return

            time.sleep(2.5)
            snap("2_dropdown_abierto")

            # 2. Encontrar y enfocar el input del dropdown
            res_inp = page.evaluate("""() => {
                const inputs = Array.from(document.querySelectorAll('input')).filter(i => {
                    const r = i.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                });
                // Excluir barra de búsqueda principal (type=search o en el nav)
                const inp = inputs.find(i => {
                    const ph = (i.placeholder || '').toLowerCase();
                    const ar = (i.getAttribute('aria-label') || '').toLowerCase();
                    const tp = (i.type || '').toLowerCase();
                    if (tp === 'search') return false;
                    return ph.includes('ciudad') || ph.includes('ubica') || ph.includes('location')
                        || ph.includes('agrega') || ph.includes('add')
                        || ar.includes('ciudad') || ar.includes('ubica') || ar.includes('location');
                }) || inputs.find(i => i.type !== 'search');
                if (inp) {
                    inp.focus();
                    return 'OK:ph=' + inp.placeholder + '|tp=' + inp.type + '|ar=' + (inp.getAttribute('aria-label')||'');
                }
                return 'FAIL:inputs=' + inputs.map(i => 'ph='+i.placeholder+'|tp='+i.type).join(', ');
            }""")
            print(f"  [filtro ciudad] Input: {res_inp}")

            if not res_inp.startswith("OK"):
                snap("2b_input_no_encontrado")
                return

            # 3. Escribir ciudad
            time.sleep(0.3)
            page.keyboard.type(ciudad, delay=100)
            print(f"  [filtro ciudad] Escribió '{ciudad}' — esperando sugerencias...")
            time.sleep(3)
            snap("3_sugerencias")

            # 4. Clic en primera sugerencia que tenga texto (espera activa)
            res_sug = "FAIL: sin sugerencias"
            for intento in range(3):
                res_sug = page.evaluate("""() => {
                    const sels = ['[role="option"]','li[role="option"]','div[role="option"]',
                                  '[role="listbox"] li','[role="listbox"] div'];
                    for (const s of sels) {
                        const items = Array.from(document.querySelectorAll(s));
                        // Solo considerar elementos con texto visible
                        const con_texto = items.filter(i => (i.innerText || '').trim().length > 0);
                        if (con_texto.length > 0) {
                            con_texto[0].click();
                            return 'OK:' + con_texto[0].innerText.trim().slice(0,50);
                        }
                    }
                    return 'FAIL: sin sugerencias con texto';
                }""")
                print(f"  [filtro ciudad] Sugerencia (intento {intento+1}): {res_sug}")
                if res_sug.startswith("OK"):
                    break
                time.sleep(1.5)
            time.sleep(2.5)
            snap("4_sugerencia_seleccionada")

            # 5. Mostrar resultados — buscar junto a "Restablecer" (siempre aparece como par)
            time.sleep(2)
            snap("5_antes_mostrar")

            res_show = page.evaluate("""() => {
                // Buscar "Restablecer" — su hermano en el mismo contenedor ES "Mostrar resultados"
                const todos = Array.from(document.querySelectorAll('*'));
                const restablecer = todos.find(el => {
                    const t = (el.innerText || el.textContent || '').trim().toLowerCase();
                    return (t === 'restablecer' || t === 'reset') && el.children.length === 0;
                });

                if (restablecer) {
                    // Subir hasta encontrar el contenedor que tiene ambos botones
                    let contenedor = restablecer.parentElement;
                    for (let i = 0; i < 5 && contenedor; i++) {
                        const hijos = Array.from(contenedor.querySelectorAll(
                            'button, a, [role="button"], div[tabindex]'
                        )).filter(h => {
                            const t = (h.innerText || h.textContent || '').trim().toLowerCase();
                            return t.length > 0 && !t.includes('restablecer') && !t.includes('reset');
                        });
                        if (hijos.length > 0) {
                            // Preferir el que tenga texto tipo "mostrar" o tenga número
                            const preferido = hijos.find(h => {
                                const t = (h.innerText || '').toLowerCase();
                                return t.includes('mostrar') || t.includes('show') || /\d/.test(t);
                            }) || hijos[hijos.length - 1];
                            preferido.click();
                            return 'OK-restablecer-sibling:' + (preferido.innerText || '').trim().slice(0, 50);
                        }
                        contenedor = contenedor.parentElement;
                    }
                    return 'FAIL-no-sibling: Restablecer encontrado pero sin hermano';
                }

                // Si no hay "Restablecer", buscar cualquier elemento con texto de acción
                const accion = todos.find(el => {
                    const t = (el.innerText || el.textContent || '').trim().toLowerCase();
                    const r = el.getBoundingClientRect();
                    return r.width > 50 && r.height > 20 && t.length < 60 && (
                        t.includes('mostrar') || t.includes('show result') ||
                        t.includes('aplicar') || t.includes('apply') || t.includes('done')
                    );
                });
                if (accion) { accion.click(); return 'OK-accion:' + (accion.innerText||'').trim().slice(0,50); }

                return 'FAIL-sin-restablecer';
            }""")
            print(f"  [filtro ciudad] Mostrar resultados: {res_show}")

            if res_show.startswith("OK"):
                time.sleep(3)
                snap("5_filtro_aplicado")
                print(f"  [filtro ciudad] ✅ {ciudad} aplicado")
            else:
                # NO presionar Escape — cerrar con clic fuera del dropdown
                print(f"  [filtro ciudad] ⚠ No encontró botón. Cerrando con clic externo...")
                page.mouse.click(640, 200)
                time.sleep(2)
                snap("5_clic_externo")
                print(f"  [filtro ciudad] Continuando sin confirmar filtro")

        except Exception as e:
            print(f"  [filtro ciudad] ERROR: {e}")
            try:
                snap("error")
            except Exception:
                pass
