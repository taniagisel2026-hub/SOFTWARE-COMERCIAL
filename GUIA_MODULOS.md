# Guía de Módulos — Panel Comercial Medina SST Empresarial SAS

Este software es una herramienta de uso **interno** para gestión comercial. Solo lo maneja el equipo de Medina SST desde su computador. Los clientes no tienen acceso.

---

## Cómo abrir el software

1. Doble clic en **`start.bat`**, en la carpeta del proyecto
2. Se abren dos ventanas: el scheduler automático (minimizado, envía los correos diarios — no cerrar) y el panel, que se abre solo en `http://localhost:8501`

Si el computador tiene el arranque automático configurado (`setup_autostart.bat`), estas ventanas ya aparecen solas al encenderlo — no volver a abrir `start.bat` manualmente ese día, porque duplicaría el scheduler.

---

## Módulos del sistema

### 1. Panel de Control
**Ícono:** 📊

Es la pantalla principal que se ve al abrir el software. Muestra un resumen en tiempo real de toda la actividad comercial:

- **KPIs principales:** total de prospectos en base de datos, cotizaciones generadas, correos enviados y tasa de apertura de correos.
- **Embudo de ventas:** gráfico que muestra cuántas empresas hay en cada etapa del proceso (nuevo lead → contactado → cotización enviada → negociación → cierre).
- **Actividad reciente:** últimas empresas registradas y últimas interacciones realizadas.

Se actualiza automáticamente cada 30 segundos.

---

### 2. Cotizador
**Ícono:** 🧮

Herramienta para crear propuestas económicas de forma rápida y profesional.

**Cómo funciona:**
1. Se ingresan los datos del cliente (razón social, NIT, nombre del contacto, cargo, ciudad, teléfono, email).
2. Se seleccionan los servicios que se van a ofrecer de la lista de los 14 servicios de Medina SST.
3. Al marcar cada servicio, aparece un campo para ingresar el precio manualmente (el precio lo define el jefe según cada caso).
4. Opcionalmente se puede agregar un descuento y personalizar las condiciones de pago.
5. Al presionar **Generar cotización**, el sistema crea un PDF profesional con el logo de Medina SST listo para enviar al cliente.

**El cliente nunca entra al software** — solo recibe el PDF por correo o WhatsApp.

---

### 3. Motor de Prospección
**Ícono:** 🕵️

Busca automáticamente empresas potenciales clientes en internet y las guarda en la base de datos.

**Fuentes de búsqueda:**
- **Google Maps:** encuentra empresas por ciudad y sector económico.
- **LinkedIn:** extrae perfiles de empresas en búsqueda pública.
- **WebScraper:** visita páginas web de empresas para extraer correos de contacto.

**Cómo funciona:**
1. Se elige la ciudad y el sector económico objetivo (ej: Bogotá, Construcción).
2. Se define cuántas empresas máximo buscar por fuente.
3. Se activan o desactivan las fuentes deseadas.
4. Opcionalmente se puede activar el envío automático de correos a los nuevos prospectos encontrados.
5. Al ejecutar, el sistema busca, filtra duplicados y guarda las empresas nuevas en la base de datos.

Cumple con la **Ley 1581 de 2012 (Habeas Data)** — solo contacta empresas que no han solicitado salir de la lista.

---

### 4. Campañas y Habeas Data
**Ícono:** ✉️

Gestiona el envío de correos y mensajes de WhatsApp a los prospectos, y controla quién ha pedido no ser contactado.

**Secciones:**

- **Lista de prospectos:** tabla con todas las empresas en la base de datos, su estado, fuente y datos de contacto. Se puede filtrar por ciudad, sector y estado.
- **Envío de campañas:** permite enviar correos personalizados a los prospectos seleccionados. Si la API de Gemini está configurada, el gancho de apertura de cada correo es redactado de forma única por inteligencia artificial según el sector de la empresa. Si no, usa uno de los textos de respaldo (rotan varias opciones para no repetir siempre el mismo).
- **Lista negra (Habeas Data):** registra las empresas que han pedido no ser contactadas. El sistema las excluye automáticamente de todos los envíos futuros.

Los correos se envían respetando un límite diario para no ser marcados como spam, y **de lunes a viernes se envían solos a las 8:30 a.m.** vía el scheduler automático (`start.bat`) — no es necesario enviarlos manualmente cada día. Antes de eso, a las 8:15 se limpian los rebotes y a las 8:20 se revisan las respuestas de los prospectos: si alguien dice que no le interesa, se va automáticamente a la lista negra; si dice que sí, queda marcado como "pidió portafolio" listo para enviarle.

---

### 5. Analítica y Conversión
**Ícono:** 📈

Muestra estadísticas detalladas para medir qué tan efectiva está siendo la estrategia comercial.

**Métricas disponibles:**
- **Tasa de apertura:** porcentaje de correos enviados que el cliente abrió.
- **Tasa de respuesta:** porcentaje de correos que recibieron respuesta.
- **Tasa de conversión:** cuántos prospectos avanzaron a cotización o cierre.
- **Pipeline por etapa:** cuántas empresas hay en cada etapa del embudo de ventas.
- **Evolución en el tiempo:** gráficas de cómo han cambiado las métricas semana a semana.

Sirve para que identifiquen qué está funcionando y qué se debe mejorar en el proceso comercial.

---

### 6. Fábrica de Contenido
**Ícono:** 🎨

Genera automáticamente contenido de redes sociales sobre temas de Seguridad y Salud en el Trabajo (SST) usando inteligencia artificial (API de Gemini).

**Qué genera con un solo clic:**
- Un **artículo completo** en Markdown (500–700 palabras) sobre un tema SST del día.
- **Copy para LinkedIn** (tono profesional, 150–200 palabras).
- **Copy para Facebook** (tono directo y cercano, 100–130 palabras).
- **Copy para Instagram** (tono impactante, 80–100 palabras).
- **8 hashtags** relevantes para el sector.
- **3 prompts de imágenes** listos para generar en herramientas como DALL-E o Midjourney.

El sistema rota automáticamente los temas por día del año para que el contenido siempre sea diferente. Requiere que la clave `GEMINI_API_KEY` esté configurada en el archivo `.env` (la misma que usan los correos).

---

### 7. Alianza Compecer
**Ícono:** 🤝

Lleva el registro de las empresas referidas a Compecer para certificaciones ISO (9001, 45001, 14001, 27001, entre otras) y en qué etapa va cada referido: enviado, en negociación, contrato firmado o bonificación cobrada.

---

## Base de datos

El software guarda toda la información en una base de datos local (`comercial.db`) que incluye:

- Empresas prospecto y su estado en el pipeline
- Historial de correos y mensajes enviados
- Cotizaciones generadas
- Contenido de redes sociales producido
- Registros de Habeas Data (opt-out)

---

## Tecnologías usadas

| Componente | Tecnología |
|---|---|
| Interfaz visual | Streamlit (Python) |
| Base de datos | SQLite (local) |
| Generación de PDF | ReportLab |
| Correos (envío y lectura) | Gmail API (OAuth2) |
| Gancho de correos y artículos | Gemini API (Google, capa gratuita) |
| Optimización de asuntos | Claude API (Anthropic) — solo en Analítica |
| WhatsApp | Twilio — instalado en el código, aún sin activar (falta configurar credenciales) |
| Scraping web | Playwright + BeautifulSoup |
| Automatización diaria | Librería `schedule` (Python), corre en `src/scheduler/auto_scheduler.py` |

---

*Panel Comercial · Medina SST Empresarial SAS · v1.0.0 · Actualizado 20 de agosto de 2026*
