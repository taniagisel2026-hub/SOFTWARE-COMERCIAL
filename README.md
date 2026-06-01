# Ecosistema Inteligente de Prospección Comercial, CRM y Automatización de Cotizaciones SST

**Medina SST Empresarial SAS**  
`v1.0.0` | `2026-06-01` | `Estado: En Desarrollo`

---

## Descripción del Proyecto

Sistema de software integrado que automatiza el ciclo comercial completo para la prestación de servicios de Seguridad y Salud en el Trabajo (SST) en Colombia. El ecosistema conecta la prospección automatizada de empresas, la gestión de relaciones con clientes (CRM), la generación de cotizaciones parametrizadas bajo la **Resolución 0312 de 2019** y la producción diaria de contenido para redes sociales.

---

## Módulos Principales

| Módulo | Descripción |
|---|---|
| Motor de Prospección | Scraping de Google Maps y LinkedIn por ciudad y sector en Colombia |
| CRM Central | Pipeline comercial completo desde prospecto hasta cierre |
| Cotizador SST | Generación automática de propuestas según Resolución 0312/2019 |
| Canal Gmail | Envío, seguimiento y registro de comunicaciones vía Gmail API |
| Fábrica de Contenido | 1 artículo diario + 3 imágenes automáticas para RRSS |

---

## Índice de Documentación

- [Arquitectura y Diseño del Sistema](./docs/arquitectura_y_diseno.md)
  - Diagrama de Componentes (Mermaid)
  - Diagrama Entidad-Relación — DER (Mermaid)
  - Flujo de Prospección End-to-End (Mermaid)
  - Stack Tecnológico Propuesto

---

## Estructura del Repositorio

```
SOFTWARE COMERCIAL/
├── README.md                        # Presentación oficial del repositorio
├── docs/
│   └── arquitectura_y_diseno.md    # Documentación técnica y diagramas
├── backend/                         # API FastAPI + lógica de negocio
│   ├── scraper/                     # Motor de prospección
│   ├── crm/                         # Módulo CRM
│   ├── cotizador/                   # Generador de cotizaciones SST
│   └── contenido/                   # Fábrica de contenido IA
├── frontend/                        # Interfaz React + TailwindCSS
├── database/
│   └── migrations/                  # Scripts de migración PostgreSQL
└── docker-compose.yml               # Orquestación de servicios
```

---

## Requisitos Previos

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Docker y Docker Compose
- Credenciales Gmail API (OAuth 2.0)
- API Key Anthropic (Claude)

---

## Inicio Rápido

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd "SOFTWARE COMERCIAL"

# 2. Levantar servicios con Docker
docker-compose up -d

# 3. Ejecutar migraciones de base de datos
python backend/database/migrate.py

# 4. Iniciar el backend
uvicorn backend.main:app --reload

# 5. Iniciar el frontend
cd frontend && npm install && npm run dev
```

---

## Marco Regulatorio

El módulo de cotización se parametriza en cumplimiento de la **Resolución 0312 de 2019** del Ministerio del Trabajo de Colombia, que establece los Estándares Mínimos del Sistema de Gestión de Seguridad y Salud en el Trabajo.

---

## Contacto

**Medina SST Empresarial SAS**  
Email: proyectos1@medinaempresarial.com

---

*Para documentación técnica detallada ver [./docs/arquitectura_y_diseno.md](./docs/arquitectura_y_diseno.md)*
