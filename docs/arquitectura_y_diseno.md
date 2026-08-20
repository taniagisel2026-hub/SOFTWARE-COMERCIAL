# Arquitectura y Diseño del Sistema
## Ecosistema Inteligente de Prospección Comercial, CRM y Automatización de Cotizaciones para Servicios SST

**Cliente:** Medina SST Empresarial SAS
**Versión:** 1.2.0
**Fecha:** 2026-08-20
**Clasificación:** Documentación Técnica Interna

---

## 1. Introducción

Medina SST Empresarial SAS es una empresa colombiana especializada en la prestación de servicios de Seguridad y Salud en el Trabajo (SST), con capacidad de atender empresas en múltiples ciudades del territorio nacional. El crecimiento del mercado regulado por la **Resolución 0312 de 2019** del Ministerio del Trabajo exige una operación comercial ágil, trazable y escalable.

El presente sistema constituye un **ecosistema de software integrado** diseñado para automatizar el ciclo completo de prospección, relacionamiento y cotización de clientes empresariales. Sus pilares funcionales son:

- **Motor de Prospección:** scraping automatizado de empresas objetivo en Google Maps y web/LinkedIn, segmentado por ciudad y sector económico en Colombia.
- **CRM Central:** gestión del ciclo de vida del prospecto desde el primer contacto hasta el cierre comercial.
- **Cotizador SST:** generación de propuestas económicas parametrizadas según los estándares de la Resolución 0312.
- **Cadencia de Outreach por Email:** secuencia automatizada Día 1 → Día 4 → Día 8, íntegramente por correo (con un botón de contacto directo por WhatsApp dentro del mensaje), con el objetivo de generar interés y que el prospecto contacte directamente a la empresa.
- **Automatización diaria (Scheduler):** de lunes a viernes, sin intervención manual, el sistema limpia rebotes, detecta respuestas de prospectos y dispara la cadencia de correos a la hora que corresponde.
- **Habeas Data automático:** las respuestas negativas de un prospecto activan su exclusión (opt-out) sin que nadie tenga que hacerlo a mano, cumpliendo la Ley 1581 de 2012.
- **Fábrica de Contenido:** generación diaria automatizada de artículos y copys para redes sociales.

---

## 2. Diagrama de Componentes

El siguiente diagrama representa la arquitectura de alto nivel del sistema, mostrando los módulos principales y sus dependencias de comunicación. El bloque **"Construido, aún no activo"** agrupa componentes que existen en el código pero no están en operación (faltan credenciales o infraestructura adicional).

```mermaid
graph TD
    subgraph FUENTES["Fuentes de Datos Externas"]
        GM[Google Maps]
        WEB[Web / LinkedIn]
    end

    subgraph MOTOR_PROSPECCION["Motor de Prospección"]
        SCRAPER["Scraper por Ciudad\n(Colombia)"]
        GM --> SCRAPER
        WEB --> SCRAPER
    end

    subgraph AUTOMATIZACION["Scheduler Automático\n(lunes a viernes, requiere\nel software abierto)"]
        SCHED_REBOTES["08:15\nLimpieza de rebotes"]
        SCHED_RESP["08:20\nDetección de respuestas"]
        SCHED_CAD["08:30\nCadencia Día 1/4/8"]
        SCHED_SCRAPE["14:00\nExtracción de prospectos"]
    end

    subgraph NUCLEO["Núcleo del Sistema"]
        CRM["CRM Central\n(Gestión de Prospectos\ny Pipeline Comercial)"]
        COTIZADOR["Cotizador SST\n(Herramienta interna —\napoyo al asesor comercial)"]
        OUTREACH["Orquestador de Cadencia\nDía 1 / Día 4 / Día 8"]
        FABRICA["Fábrica de Contenido\n(Gemini)"]
        HABEAS["Habeas Data\n(Ley 1581/2012)"]
        REPLY["Detección de Respuestas\n(negativas / afirmativas)"]
    end

    subgraph COMUNICACION["Canales de Comunicación"]
        GMAIL["Gmail API\n(envío y lectura\nde correos)"]
        RRSS["Publicación en\nRedes Sociales\n(manual, copy-paste)"]
    end

    subgraph PENDIENTE["Construido, aún no activo"]
        WHATSAPP["Envío directo por WhatsApp\n(Twilio API) —\nsin credenciales configuradas"]
        PIXEL["Pixel de apertura de correo —\nrequiere servidor propio expuesto"]
    end

    subgraph ALMACENAMIENTO["Capa de Persistencia"]
        DB[("Base de Datos\nSQLite")]
    end

    SCRAPER -->|"Empresas identificadas"| CRM
    SCHED_SCRAPE -.->|"1 municipio/día, rotativo"| SCRAPER
    SCHED_REBOTES -->|"Marca opt-out por rebote"| DB
    SCHED_RESP --> REPLY
    REPLY -->|"Negativa → opt-out"| HABEAS
    REPLY -->|"Afirmativa → estado PIDIO_PORTAFOLIO"| CRM
    HABEAS -->|"Excluye de envíos futuros"| DB
    SCHED_CAD --> OUTREACH
    OUTREACH -->|"Día 1, Día 4 y Día 8"| GMAIL
    GMAIL -.->|"El correo trae un botón\nde contacto directo"| WHATSAPP
    GMAIL -.->|"apertura no medida"| PIXEL
    COTIZADOR -->|"Uso manual por el asesor"| CRM
    FABRICA -->|"Contenido publicable"| RRSS
    CRM -->|"Lee / Escribe"| DB
    COTIZADOR -->|"Lee / Escribe"| DB
    FABRICA -->|"Lee / Escribe"| DB
    OUTREACH -->|"Registra historial"| DB
```

---

## 3. Diagrama Entidad-Relación (DER)

El siguiente DER describe el modelo de datos relacional real (`src/database/models.py`). Se representan las cinco tablas con sus atributos, claves primarias (PK) y claves foráneas (FK).

```mermaid
erDiagram

    EMPRESA_PROSPECTO {
        int     id_empresa                 PK
        string  razon_social
        string  nit
        string  sector_economico
        string  ciudad
        string  departamento
        string  direccion
        string  telefono
        string  whatsapp
        string  email_contacto
        string  nombre_contacto
        string  cargo_contacto
        string  nivel_riesgo_arl
        int     num_empleados
        string  estado_prospecto
        string  fuente_origen
        date    fecha_registro
        date    fecha_ultima_actualizacion
        bool    opt_out
        date    fecha_opt_out
        string  motivo_opt_out
    }

    HISTORIAL_INTERACCIONES {
        int     id_interaccion       PK
        int     id_empresa           FK
        int     id_cotizacion        FK
        string  tipo_interaccion
        string  canal
        string  asunto
        text    cuerpo_mensaje
        string  estado_respuesta
        datetime fecha_interaccion
        string  responsable
        text    notas_seguimiento
    }

    COTIZACION {
        int     id_cotizacion              PK
        int     id_empresa                 FK
        string  codigo_cotizacion
        string  version
        int     num_empleados_cotizados
        string  nivel_riesgo
        string  nivel_estandares
        json    servicios_incluidos
        decimal valor_servicios
        decimal valor_viaticos
        decimal valor_total_proyecto
        decimal valor_total_mensual
        decimal valor_total_anual
        string  moneda
        string  estado_cotizacion
        date    fecha_emision
        date    fecha_vencimiento
        string  url_documento_pdf
        string  creado_por
    }

    REFERIDO_COMPECER {
        int     id_referido          PK
        string  razon_social
        string  nit
        string  nombre_contacto
        string  email_contacto
        string  telefono
        string  ciudad
        string  norma_iso
        date    fecha_referido
        string  estado
        decimal valor_bonificacion
        text    notas
        string  registrado_por
        date    fecha_cierre
    }

    CONTENIDO_REDES {
        int     id_contenido        PK
        string  tipo_contenido
        string  plataforma_destino
        text    texto_publicacion
        string  url_imagen_1
        string  url_imagen_2
        string  url_imagen_3
        string  url_articulo
        string  tema_sst
        string  estado_publicacion
        date    fecha_generacion
        date    fecha_publicacion
        string  generado_por_ia
        int     engagement_likes
        int     engagement_shares
    }

    EMPRESA_PROSPECTO ||--o{ HISTORIAL_INTERACCIONES : "tiene"
    EMPRESA_PROSPECTO ||--o{ COTIZACION              : "recibe"
    COTIZACION        ||--o{ HISTORIAL_INTERACCIONES : "genera"
```

> `REFERIDO_COMPECER` es una tabla independiente (no tiene llave foránea hacia `EMPRESA_PROSPECTO`) — los referidos a Compecer se registran aparte porque no siempre son empresas que ya estén en el CRM de Medina SST.

---

## 4. Flujo Diario End-to-End

```mermaid
sequenceDiagram
    participant SCHED as Scheduler (08:15–14:00)
    participant DB as Base de Datos
    participant G  as Gmail API
    participant P  as Prospecto
    participant J  as Asesor Comercial

    Note over SCHED: 08:15 — Limpieza de rebotes
    SCHED->>G: Revisa mailer-daemon / postmaster
    G-->>SCHED: Direcciones inválidas
    SCHED->>DB: Marca opt_out = true (rebote)

    Note over SCHED: 08:20 — Detección de respuestas
    SCHED->>G: Revisa bandeja de entrada (últimos 30 días)
    G-->>SCHED: Respuestas de prospectos conocidos
    alt Respuesta negativa
        SCHED->>DB: opt_out = true (Ley 1581)
    else Respuesta afirmativa
        SCHED->>DB: estado_prospecto = PIDIO_PORTAFOLIO
    else Sin intención clara
        SCHED->>DB: estado_respuesta = RESPONDIDO
    end

    Note over SCHED: 08:30 — Cadencia de correos
    SCHED->>DB: Lee pendientes (excluye opt_out y PIDIO_PORTAFOLIO)
    Note right of SCHED: Prioridad: Día 8 → Día 4 → Día 1
    SCHED->>G: Envía Día 1 / Día 4 / Día 8 según corresponda
    G->>DB: Registra HISTORIAL_INTERACCIONES

    Note over SCHED: 14:00 — Extracción de prospectos
    SCHED->>DB: Inserta EMPRESA_PROSPECTO nuevas (estado NUEVO)

    P->>J: Si le interesa, responde el correo o escribe por WhatsApp
    J->>DB: Actualiza estado → EN_NEGOCIACION / CIERRE (manual)
    Note over J: El asesor cotiza y negocia de forma personalizada.<br/>El sistema no cotiza ni negocia solo.
```

---

## 5. Cadencia de Outreach por Email

La secuencia de contacto automatizado tiene 3 puntos de contacto, todos por correo (`src/modules/outreach/sequence_orchestrator.py`):

| Día | Plantilla | Contenido | Condición para dispararse |
|---|---|---|---|
| **1** | `PRIMER_CONTACTO` | Presentación de Medina SST + gancho generado por IA | Al registrar el prospecto (si tiene email y no está en opt-out) |
| **4** | `RECORDATORIO_VENCIMIENTO` | Recordatorio con nuevo ángulo — objeción de costo/tiempo | ≥3 días desde el Día 1, si aún no respondió |
| **8** | `ULTIMO_CONTACTO` | Cierre cordial, sin presión, puerta abierta | ≥4 días desde el Día 4 |

Los tres correos incluyen un botón verde de contacto directo por WhatsApp — es un enlace `wa.me` dentro del correo, no un envío automático por WhatsApp (ver sección 6, Twilio no está activo).

Si el prospecto responde en cualquier punto de la cadencia, la detección de respuestas (08:20) lo saca del flujo automáticamente: negativa → opt-out, afirmativa → `PIDIO_PORTAFOLIO`. En ambos casos el orquestador deja de enviarle más correos automáticos.

Toda la cadencia queda trazada en `HISTORIAL_INTERACCIONES` con `tipo_interaccion = "SECUENCIA_CADENCIA"` y `notas_seguimiento` con prefijo `[SEQ:DIA_1]`, `[SEQ:DIA_4]` o `[SEQ:DIA_8]`. Cada etapa se **reserva en la base de datos antes de enviar el correo**, apoyándose en un índice único, para que dos disparadores simultáneos (scheduler + botón manual del panel) no dupliquen el envío.

> **Importante:** La cadencia automatizada tiene como único objetivo despertar el interés del prospecto. Una vez que el prospecto contacta al asesor comercial, la negociación y presentación de la propuesta económica se realizan de forma **personalizada y manual** por parte del asesor. El Cotizador SST del sistema es una herramienta de apoyo interno para que el asesor prepare las cifras, no un proceso automático.

---

## 6. Stack Tecnológico Implementado

| Capa | Tecnología | Estado |
|---|---|---|
| Frontend / CRM | Python + **Streamlit** | Implementado |
| Visualización | Plotly + Pandas | Implementado |
| Base de datos | **SQLite** (local, `comercial.db`) | Implementado |
| ORM | SQLAlchemy 2.0 + Alembic | Implementado |
| Scraping | Playwright + BeautifulSoup + httpx | Implementado |
| IA — gancho de correos | **Gemini** (`gemini-2.5-flash`, Google — capa gratuita) | Implementado |
| IA — artículos y redes | **Gemini** (`gemini-flash-lite-latest`) | Implementado |
| IA — optimización de asuntos | **Claude** (`claude-haiku-4-5`, Anthropic) — solo en Analítica | Implementado |
| Generación de imágenes | Prompts automáticos (DALL-E 3 / Stable Diffusion — opcional) | Prompts listos, activación pendiente |
| Email (envío y lectura) | Gmail API (OAuth 2.0) | Implementado |
| Detección de rebotes | Escaneo Gmail (mailer-daemon/postmaster) | Implementado |
| Detección de respuestas | Escaneo Gmail (frases negativas/afirmativas) | Implementado |
| WhatsApp — envío automático | Twilio API | Código instalado, **sin credenciales — no activo** |
| WhatsApp — contacto directo | Enlace `wa.me` dentro de los correos | Implementado |
| Apertura de correos (open rate) | Pixel de tracking | Diseñado, **requiere servidor propio expuesto a internet — no activo** |
| Automatización diaria | Librería `schedule` (Python) | Implementado |
| Documentos | ReportLab + Pillow | Implementado |
| Plantillas HTML | Jinja2 | Implementado |
| Compliance | Habeas Data (Ley 1581/2012) — automático | Implementado |
| Configuración | python-dotenv (`.env`) | Implementado |

---

## 7. Estructura de Módulos del Proyecto

```
SOFTWARE COMERCIAL/
├── app.py                          # Punto de entrada Streamlit
├── start.bat                       # Inicia scheduler + panel
├── data/                           # Logs del scheduler, configuración (auto_dia1, etc.)
├── src/
│   ├── config.py                   # Configuración global (AppConfig singleton)
│   ├── data/
│   │   └── ciudades_colombia.py    # Referencia de ciudades + zonas de viáticos
│   ├── database/
│   │   ├── models.py               # Modelos ORM (5 entidades)
│   │   ├── connection.py           # Gestión de sesiones SQLAlchemy
│   │   └── init_db.py              # Creación de tablas + migraciones incrementales
│   ├── domain/
│   │   ├── entities.py             # Dataclasses puras + enums de negocio
│   │   └── resolution_0312.py      # Lógica Res. 0312/2019 (60 estándares)
│   ├── frontend/
│   │   ├── pages/                  # dashboard, cotizador, scraper, campanas,
│   │   │                           #   analitica, contenido, compecer
│   │   ├── components/             # Componentes reutilizables (métricas)
│   │   └── styles.py               # Estilos CSS personalizados
│   ├── modules/
│   │   ├── cotizador/              # Calculadora + viáticos + exportador PDF
│   │   ├── email/                  # Gmail client + plantillas + gancho IA + rate limiter
│   │   ├── whatsapp/               # Twilio client + plantillas (sin activar)
│   │   ├── outreach/                # Orquestador de cadencia Día 1/4/8
│   │   ├── scraper/                 # Engine + Google Maps + LinkedIn + pipeline
│   │   ├── contenido/                # Generador de artículos y copys (Gemini)
│   │   ├── tracking/                 # bounce_detector, reply_detector, pixel (inactivo)
│   │   └── compliance/               # Habeas Data (Ley 1581/2012)
│   └── scheduler/
│       └── auto_scheduler.py        # Tareas automáticas diarias (sección 4)
├── assets/                         # Logos (Medina SST, Compecer)
├── credentials/                    # Tokens OAuth Gmail (gitignored)
├── output/                         # Cotizaciones PDF + contenido generado
└── docs/
    └── arquitectura_y_diseno.md    # Este documento
```

---

*Documento actualizado el 2026-08-20 tras revisión contra el código real del repositorio. Para consultas contactar al equipo de desarrollo.*
