# Arquitectura y Diseño del Sistema
## Ecosistema Inteligente de Prospección Comercial, CRM y Automatización de Cotizaciones para Servicios SST

**Cliente:** Medina SST Empresarial SAS  
**Versión:** 1.0.0  
**Fecha:** 2026-06-01  
**Clasificación:** Documentación Técnica Interna

---

## 1. Introducción

Medina SST Empresarial SAS es una empresa colombiana especializada en la prestación de servicios de Seguridad y Salud en el Trabajo (SST), con capacidad de atender empresas en múltiples ciudades del territorio nacional. El crecimiento del mercado regulado por la **Resolución 0312 de 2019** del Ministerio del Trabajo exige una operación comercial ágil, trazable y escalable.

El presente sistema constituye un **ecosistema de software integrado** diseñado para automatizar el ciclo completo de prospección, relacionamiento y cotización de clientes empresariales. Sus pilares funcionales son:

- **Motor de Prospección:** scraping automatizado de empresas objetivo en Google Maps y LinkedIn, segmentado por ciudad y sector económico en Colombia.
- **CRM Central:** gestión del ciclo de vida del prospecto desde el primer contacto hasta el cierre comercial.
- **Cotizador SST:** generación de propuestas económicas parametrizadas según los estándares de la Resolución 0312.
- **Canal de Comunicación:** integración con la API de Gmail para el envío y seguimiento automatizado de correos.
- **Fábrica de Contenido:** generación diaria automatizada de contenido para redes sociales (1 artículo + 3 imágenes).

---

## 2. Diagrama de Componentes

El siguiente diagrama representa la arquitectura de alto nivel del sistema, mostrando los módulos principales y sus dependencias de comunicación.

```mermaid
graph TD
    subgraph FUENTES["Fuentes de Datos Externas"]
        GM[Google Maps API]
        LI[LinkedIn / Web Scraping]
    end

    subgraph MOTOR_PROSPECCION["Motor de Prospección"]
        SCRAPER["Scraper por Ciudad\n(Colombia)"]
        GM --> SCRAPER
        LI --> SCRAPER
    end

    subgraph NUCLEO["Núcleo del Sistema"]
        CRM["CRM Central\n(Gestión de Prospectos\ny Pipeline Comercial)"]
        COTIZADOR["Cotizador SST\n(Parametrizado según\nResolución 0312/2019)"]
        FABRICA["Fábrica de Contenido\n(1 artículo diario +\n3 imágenes automáticas)"]
    end

    subgraph COMUNICACION["Canales de Comunicación"]
        GMAIL["Gmail API\n(Envío y seguimiento\nde correos)"]
        RRSS["Publicación\nRedes Sociales"]
    end

    subgraph ALMACENAMIENTO["Capa de Persistencia"]
        DB[("Base de Datos\nRelacional\n(PostgreSQL)")]
    end

    SCRAPER -->|"Empresas identificadas"| CRM
    CRM -->|"Solicita propuesta"| COTIZADOR
    CRM -->|"Dispara comunicación"| GMAIL
    COTIZADOR -->|"PDF de cotización"| GMAIL
    FABRICA -->|"Contenido publicable"| RRSS
    CRM -->|"Lee / Escribe"| DB
    COTIZADOR -->|"Lee / Escribe"| DB
    FABRICA -->|"Lee / Escribe"| DB
    GMAIL -->|"Registra historial"| DB
```

---

## 3. Diagrama Entidad-Relación (DER)

El siguiente DER describe el modelo de datos relacional que sostiene el ecosistema. Se representan las cuatro entidades centrales con sus atributos, claves primarias (PK) y claves foráneas (FK).

```mermaid
erDiagram

    EMPRESA_PROSPECTO {
        int     id_empresa          PK
        string  razon_social
        string  nit
        string  sector_economico
        string  ciudad
        string  departamento
        string  direccion
        string  telefono
        string  email_contacto
        string  nombre_contacto
        string  cargo_contacto
        string  nivel_riesgo_arl
        int     num_empleados
        string  estado_prospecto
        string  fuente_origen
        date    fecha_registro
        date    fecha_ultima_actualizacion
    }

    HISTORIAL_INTERACCIONES {
        int     id_interaccion      PK
        int     id_empresa          FK
        int     id_cotizacion       FK
        string  tipo_interaccion
        string  canal
        string  asunto
        text    cuerpo_mensaje
        string  estado_respuesta
        date    fecha_interaccion
        string  responsable
        text    notas_seguimiento
    }

    COTIZACION {
        int     id_cotizacion       PK
        int     id_empresa          FK
        string  codigo_cotizacion
        string  version
        int     num_empleados_cotizados
        string  nivel_riesgo
        json    servicios_incluidos
        decimal valor_total_mensual
        decimal valor_total_anual
        string  moneda
        string  estado_cotizacion
        date    fecha_emision
        date    fecha_vencimiento
        string  url_documento_pdf
        string  creado_por
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

---

## 4. Flujo de Prospección End-to-End

```mermaid
sequenceDiagram
    participant S  as Scraper
    participant DB as Base de Datos
    participant C  as CRM
    participant Q  as Cotizador SST
    participant G  as Gmail API

    S->>DB: Inserta EMPRESA_PROSPECTO (estado: NUEVO)
    C->>DB: Lee prospectos en estado NUEVO
    C->>G: Envía correo de primer contacto
    G->>DB: Registra HISTORIAL_INTERACCIONES (tipo: EMAIL_SALIENTE)
    C->>DB: Actualiza estado → EN_SEGUIMIENTO
    C->>Q: Solicita generación de cotización
    Q->>DB: Inserta COTIZACION (estado: BORRADOR)
    Q->>G: Envía PDF de cotización al prospecto
    G->>DB: Registra HISTORIAL_INTERACCIONES (tipo: COTIZACION_ENVIADA)
    C->>DB: Actualiza estado → COTIZACION_ENVIADA
```

---

## 5. Stack Tecnológico Propuesto

| Capa | Tecnología | Justificación |
|---|---|---|
| Backend / API | Python (FastAPI) | Alto rendimiento, tipado estático, ideal para automatizaciones |
| Base de Datos | PostgreSQL | Soporte JSON, robustez relacional, escalabilidad |
| ORM | SQLAlchemy | Mapeo objeto-relacional maduro para Python |
| Scraping | Playwright + BeautifulSoup | Renderizado JS (Google Maps) y parsing HTML |
| IA / Contenido | Claude API (Anthropic) | Generación de artículos y textos SST de alta calidad |
| Imágenes | Stable Diffusion / DALL·E | Generación automática de imágenes para RRSS |
| Comunicación | Gmail API (OAuth 2.0) | Integración nativa con cuentas corporativas Google |
| Frontend / CRM | React + TailwindCSS | Interfaz moderna y responsiva |
| Documentos | ReportLab / WeasyPrint | Generación de PDFs de cotizaciones |
| Contenedor | Docker + Docker Compose | Despliegue reproducible y aislado |

---

*Documento generado el 2026-06-01. Para actualizaciones contactar al equipo de desarrollo.*
