# Panel Comercial — Medina SST Empresarial SAS

**Medina SST Empresarial SAS**
`v1.0.0` | `2026-08-20` | `Estado: En Producción`

---

## Descripción del Proyecto

Software de uso interno que automatiza el ciclo comercial de Medina SST: encuentra empresas colombianas que necesitan implementar su SG-SST, les escribe una secuencia de correos de forma automática, detecta si responden (positiva o negativamente) y deja todo registrado en un CRM local para que la asesora comercial solo tenga que atender a quien ya mostró interés.

Es una aplicación **Streamlit** que corre en el computador local — no es una app web pública, no tiene backend separado ni base de datos en la nube. Los prospectos y clientes nunca acceden al software; solo reciben correos, PDFs de cotización o mensajes de WhatsApp.

---

## Módulos del Panel

| Módulo | Qué hace |
|---|---|
| 📊 Panel de Control | Resumen en tiempo real: prospectos, cotizaciones, correos enviados, embudo de ventas |
| 🧮 Cotizador | Genera la propuesta económica en PDF según la Resolución 0312/2019 |
| 🕵️ Motor de Prospección | Busca empresas en Google Maps / LinkedIn / web por ciudad y sector, y las guarda en el CRM |
| ✉️ Campañas y Habeas Data | Envío de correos, ficha de cada prospecto, lista negra (opt-out) |
| 📈 Analítica y Conversión | Tasas de apertura/respuesta/conversión, detección de respuestas, optimización de asuntos con IA |
| 🎨 Fábrica de Contenido | Artículos y copys para redes sociales sobre SST, generados con IA |
| 🤝 Alianza Compecer | Seguimiento de referidos enviados a Compecer para certificaciones ISO (comisión) |

Ver el detalle de cada uno en [`GUIA_MODULOS.md`](./GUIA_MODULOS.md) y el paso a paso de uso en [`MANUAL_USUARIO.md`](./MANUAL_USUARIO.md).

---

## Automatización diaria

Además del uso manual del panel, un proceso en segundo plano (`src/scheduler/auto_scheduler.py`) corre de lunes a viernes sin que nadie tenga que hacer nada, **siempre que el computador esté encendido con el software abierto**:

| Hora | Tarea |
|---|---|
| 08:15 | Revisa Gmail por rebotes (correos inválidos) y los excluye antes de enviar |
| 08:20 | Revisa Gmail por respuestas de prospectos — si alguien dice que no le interesa, lo marca automáticamente en la lista negra (Habeas Data); si dice que sí, lo marca como "pidió portafolio" listo para enviarle |
| 08:30 | Envía la cadencia de correos: Día 1 (primer contacto), Día 4 (recordatorio) y Día 8 (último contacto) a quien corresponda |
| 14:00 | Busca prospectos nuevos en un municipio distinto cada día (rotación automática) |

El `start.bat` es lo que arranca este proceso junto con el panel visual. También puede configurarse para que arranque solo al encender el computador (`setup_autostart.bat`) — ver la sección de inicio en [`MANUAL_USUARIO.md`](./MANUAL_USUARIO.md).

---

## Estructura del Repositorio

```
SOFTWARE COMERCIAL/
├── app.py                      # Punto de entrada del panel (Streamlit)
├── start.bat                   # Inicia el scheduler automático + el panel
├── setup_autostart.bat         # Registra el arranque automático con Windows
├── comercial.db                # Base de datos SQLite (todo el CRM vive aquí)
├── requirements.txt
├── credentials/                # Credenciales OAuth2 de Gmail (no se sube a git)
├── data/                       # Logs del scheduler, configuración
├── output/                     # PDFs de cotizaciones generados
├── docs/
│   └── arquitectura_y_diseno.md   # Documento técnico del diseño inicial (jun/2026)
├── src/
│   ├── config.py                # Lee variables de entorno (.env)
│   ├── database/                 # Modelos SQLAlchemy + inicialización de la BD
│   ├── domain/                   # Entidades y reglas de negocio (estados, riesgos)
│   ├── frontend/
│   │   ├── pages/                 # Una página Streamlit por módulo del panel
│   │   └── components/            # Piezas de UI reutilizables (tarjetas, métricas)
│   ├── modules/
│   │   ├── cotizador/              # Cálculo de estándares y generación de PDF
│   │   ├── scraper/                # Motor de prospección (Google Maps, LinkedIn, web)
│   │   ├── email/                  # Plantillas, envío (Gmail API), IA del gancho, límites de envío
│   │   ├── whatsapp/                # Cliente de WhatsApp (Twilio) — instalado, aún no activo
│   │   ├── compliance/              # Habeas Data / Ley 1581 (opt-out)
│   │   ├── tracking/                # Detección de rebotes y de respuestas en Gmail
│   │   ├── contenido/               # Fábrica de contenido para redes sociales
│   │   └── outreach/                # Orquestador de la cadencia Día 1 / 4 / 8
│   └── scheduler/
│       └── auto_scheduler.py        # Tareas automáticas diarias (ver arriba)
├── README.md
├── FLUJO_COMERCIAL.md            # Cómo funciona el software de principio a fin
├── MANUAL_USUARIO.md             # Manual paso a paso de cada módulo
└── GUIA_MODULOS.md               # Ficha rápida de cada módulo
```

---

## Requisitos Previos

- Python 3.11+ (el proyecto usa su propio entorno virtual en `venv/`, no el Python global de Windows)
- Credenciales Gmail API (OAuth2) — para enviar y leer correos
- `GEMINI_API_KEY` (Google AI Studio, capa gratuita) — para redactar el gancho de cada correo y los artículos de la Fábrica de Contenido
- `ANTHROPIC_API_KEY` (opcional) — solo para la función "Optimizar con IA" de Analítica, que sugiere mejores asuntos de correo
- Twilio (opcional, aún no configurado) — para activar el envío de WhatsApp

## Inicio Rápido

```bash
# 1. Crear el entorno virtual (solo la primera vez)
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt

# 2. Configurar credenciales
#    - Copiar credentials/gmail_credentials.json (OAuth2 de Gmail)
#    - Llenar el archivo .env con GEMINI_API_KEY, EMPRESA_*, etc.

# 3. Abrir el software
start.bat
```

`start.bat` abre dos ventanas: el scheduler automático (minimizado) y el panel en `http://localhost:8501`. Cerrar la ventana del panel apaga el software.

---

## Marco Regulatorio

El módulo de cotización se parametriza en cumplimiento de la **Resolución 0312 de 2019** del Ministerio del Trabajo de Colombia (60 estándares mínimos del SG-SST según tamaño y riesgo de la empresa). El envío de correos respeta la **Ley 1581 de 2012 (Habeas Data)**: toda empresa que pide no ser contactada queda excluida automáticamente de futuros envíos.

---

## Contacto

**Medina SST Empresarial SAS**
Email: proyectos1@medinaempresarial.com

---

*Para el detalle técnico del diseño inicial ver [`./docs/arquitectura_y_diseno.md`](./docs/arquitectura_y_diseno.md) — algunos componentes descritos ahí (backend separado, frontend en React, PostgreSQL) fueron parte del plan original y no reflejan la implementación final, que es la descrita en este README.*
