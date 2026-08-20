# Manual de Usuario
## Ecosistema Inteligente de Prospección Comercial — Medina SST Empresarial SAS

---

## Índice

1. [¿Qué es este software?](#1-qué-es-este-software)
2. [Primer uso — Configuración inicial](#2-primer-uso--configuración-inicial)
3. [Cómo iniciar la aplicación](#3-cómo-iniciar-la-aplicación)
4. [Panel de Control](#4-panel-de-control)
5. [Cotizador Inteligente](#5-cotizador-inteligente)
6. [Motor de Prospección](#6-motor-de-prospección)
7. [Campañas y Habeas Data](#7-campañas-y-habeas-data)
8. [Analítica y Conversión](#8-analítica-y-conversión)
9. [Fábrica de Contenido](#9-fábrica-de-contenido)
10. [Alianza Compecer](#10-alianza-compecer)
11. [Flujo de trabajo diario recomendado](#11-flujo-de-trabajo-diario-recomendado)
12. [Preguntas frecuentes](#12-preguntas-frecuentes)
13. [Glosario](#13-glosario)

---

## 1. ¿Qué es este software?

Este ecosistema es una herramienta comercial diseñada exclusivamente para **Medina SST Empresarial SAS**. Su función es ayudarte a conseguir clientes nuevos de forma ordenada, profesional y legal, sin tener que hacer todo manualmente.

**En resumen, el software hace esto por ti:**

| Tarea manual antes | Con el software ahora |
|---|---|
| Buscar empresas una por una en Google | El Motor de Prospección las extrae automáticamente |
| Calcular el precio de un SG-SST a mano | El Cotizador lo hace en segundos y genera el PDF |
| Enviar correos uno a uno | El sistema los envía en secuencia automáticamente |
| Adivinar qué empresas están interesadas | La Ficha Centralizada muestra todo el historial |
| Crear posts para redes sociales | La Fábrica de Contenido los genera con IA |

---

## 2. Primer uso — Configuración inicial

Antes de arrancar, debes decirle al software quién eres. Esto se hace en un archivo llamado **`.env`** que está en la carpeta principal del proyecto.

### Abre el archivo `.env` y llena estos campos obligatorios:

```
EMPRESA_NOMBRE=Medina SST Empresarial SAS
EMPRESA_NIT=901234567-8          ← Tu NIT real aquí
EMPRESA_TELEFONO=+57 300 000 0000 ← Tu teléfono aquí
EMPRESA_EMAIL=taniagisel2026@gmail.com
```

> **¿Dónde encuentro el archivo `.env`?**
> Está en la carpeta `SOFTWARE COMERCIAL`, la misma donde está el archivo `app.py`.
> Puedes abrirlo con cualquier editor de texto (el Bloc de notas funciona).

### Campos opcionales (puedes dejarlos vacíos por ahora):

```
GEMINI_API_KEY=       ← Para que los correos y los artículos sean únicos con IA (gratis)
ANTHROPIC_API_KEY=    ← Solo para "Optimizar con IA" en Analítica (sugerir mejores asuntos)
OPENAI_API_KEY=       ← Para generar imágenes automáticas
TRACKING_URL=         ← Para saber si los prospectos abrieron tus correos
```

### Inicializar la base de datos (solo la primera vez):

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
python -m src.database.init_db
```

Esto crea el archivo `comercial.db` donde se guardarán todos tus datos.

---

## 3. Cómo iniciar la aplicación

Cada vez que quieras usar el software, haz doble clic en **`start.bat`** (en la carpeta `SOFTWARE COMERCIAL`).

Esto abre dos ventanas:
- Una minimizada llamada **"Medina SST Scheduler"** — es el proceso que envía los correos automáticos todos los días de lunes a viernes a las 8:30 a.m. **No la cierres**, aunque no la vayas a usar directamente.
- El **panel visual**, que se abre solo en tu navegador en **http://localhost:8501**

Para apagar el software, cierra la ventana del panel (la del navegador se puede cerrar sin problema, pero la ventana de la consola detrás debe cerrarse para que todo se detenga).

> **¿El computador ya lo abre solo al encenderlo?** Si en algún momento se configuró el arranque automático (`setup_autostart.bat`), el scheduler y el panel ya aparecen solos al prender el equipo. En ese caso **no vuelvas a hacer doble clic en `start.bat`** — abriría una segunda copia del scheduler enviando correos en paralelo con la primera.

La aplicación tiene un **menú lateral izquierdo** con 7 páginas. Haz clic en cualquiera para navegar.

---

## 4. Panel de Control

**¿Para qué sirve?** Es la pantalla principal. Te da una visión general de todo lo que está pasando en tu CRM en este momento.

### ¿Qué significa cada número?

**Primera fila de métricas:**

| Métrica | Qué significa |
|---|---|
| Total Prospectos | Cuántas empresas tienes en tu base de datos |
| Cotizaciones | Cuántas propuestas has generado en total |
| Emails Enviados | Cuántos correos salieron desde el sistema |
| Cierres Ganados | Cuántos contratos cerraste gracias al CRM |

**Segunda fila (KPIs del negocio):**

| Métrica | Qué significa |
|---|---|
| Open Rate correos | % de correos que los prospectos abrieron (requiere configuración adicional) |
| Conversión a cotización | % de prospectos que llegaron a pedir una propuesta |
| Velocidad cotización | Días promedio desde que registras una empresa hasta que le envías cotización |
| ROI / Ingresos CRM | Dinero generado por contratos cerrados con el sistema |

### El embudo de ventas

El gráfico de embudo muestra cuántas empresas están en cada etapa:
- **Leads Nuevos** → recién ingresados, no contactados
- **Contactados** → ya les enviaste un correo
- **Cotización Enviada** → tienen propuesta tuya
- **En Negociación** → están considerando aceptar
- **Cierre** → firmaron contrato

**Regla de oro:** El embudo debe siempre tener muchas empresas arriba (Leads Nuevos) y algunas llegando al fondo (Cierre). Si el embudo está vacío, usa el **Motor de Prospección**.

### Actividad reciente

Muestra los últimos 6 eventos del sistema: correos enviados, WhatsApp, interacciones.

---

## 5. Cotizador Inteligente

**¿Para qué sirve?** Genera propuestas comerciales en PDF en menos de 2 minutos. El precio se calcula automáticamente según la ley (Resolución 0312 de 2019).

### Paso a paso para generar una cotización:

**1. Llena el formulario izquierdo:**
- **Razón Social** → nombre completo de la empresa cliente (obligatorio)
- **NIT** → opcional, pero lo agrega al PDF
- **Ciudad** → importante para calcular los viáticos
- **Sector Económico** → afecta el tipo de servicio
- **N.° Trabajadores** → determina cuántos estándares le aplican
- **Riesgo ARL** → si no sabes cuál es, elige III (Medio) para industria general

**2. Servicios adicionales (opcional):**
Marca los checkboxes si el cliente también necesita:
- Mediciones Ambientales (ruido, iluminación)
- Análisis de Puestos de Trabajo
- Batería de Riesgo Psicosocial
- Plan de Seguridad Vial (PESV)
- Certificación ISO 45001

**3. Haz clic en "⚡ Calcular Cotización"**

El sistema te muestra en el lado derecho:
- Cuántos estándares le aplican y por qué ley
- El valor total del proyecto en COP
- La cuota mensual equivalente
- Un desglose detallado de todos los servicios

**4. Descarga el PDF** con el botón naranja "📄 Descargar PDF"

**5. Guarda en el CRM** con "💾 Guardar en CRM" si quieres que quede registrado el prospecto y su cotización en la base de datos.

> **Tip:** Si el cliente está en una ciudad fuera de Bogotá, el sistema calcula automáticamente los viáticos y los agrega al precio.

---

## 6. Motor de Prospección

**¿Para qué sirve?** Busca empresas automáticamente en Google Maps, LinkedIn e internet, y las agrega directamente a tu CRM.

> **Importante:** Esta función requiere conexión a internet y puede tardar varios minutos dependiendo de cuántas empresas busques.

### Cómo buscar prospectos:

1. Selecciona la **fuente de búsqueda**: Google Maps, LinkedIn o búsqueda web general
2. Escribe la **ciudad** donde quieres buscar (ej: Bogotá, Medellín)
3. Escribe el **sector** (ej: construcción, manufactura, transporte)
4. Define cuántas empresas quieres buscar
5. Haz clic en **"Iniciar Prospección"**

El sistema extrae: nombre de la empresa, email de contacto, teléfono, ciudad y la inyecta automáticamente en tu CRM.

> **Consejo:** Empieza con búsquedas pequeñas (20-30 empresas) para validar la calidad antes de hacer búsquedas masivas.

---

## 7. Campañas y Habeas Data

**¿Para qué sirve?** Aquí gestionas todas las empresas de tu CRM, envías correos, ves la Ficha de cada cliente y controlas el cumplimiento de la Ley 1581 (privacidad de datos).

### Pestaña: Prospectos en CRM

#### Ver la Ficha Centralizada de un cliente

1. En la parte superior, busca el **selectbox "Ficha Centralizada del Cliente"**
2. Selecciona una empresa del listado
3. Se despliega su ficha completa con:
   - NIT, ciudad, riesgo ARL, sector
   - Estado actual en el embudo (badge de color)
   - Historial de todos los correos y WhatsApp enviados
   - Todas las cotizaciones con botón para descargar el PDF

#### Enviar un correo a un prospecto

Cada empresa en la tabla tiene un botón **"📨 Enviar correo"** (solo aparece si tiene email registrado). Al hacer clic:
- El sistema verifica que no está en lista negra (Ley 1581)
- Verifica que no excediste el límite diario de envíos
- Envía el correo y lo registra en el historial

#### Envío masivo a todos los prospectos nuevos

Baja hasta **"Acciones masivas"** y haz clic en **"🚀 Enviar PRIMER CONTACTO"**. El sistema envía a todos los prospectos con estado "NUEVO" que tienen email.

> **Esto también corre solo, todos los días.** No es obligatorio usar este botón manualmente: de lunes a viernes a las 8:30 a.m. el scheduler automático (`start.bat`) envía la cadencia completa — Día 1 a los nuevos, Día 4 a quien no respondió tras 4 días, y Día 8 como cierre — mientras el software esté abierto. El botón manual sirve para forzar un envío antes de esa hora o si el computador estuvo apagado ese día.

#### Filtros

Puedes filtrar por:
- Estado en el embudo (NUEVO, EN SEGUIMIENTO, etc.)
- Ciudad
- Texto libre (nombre, email, sector)

### Pestaña: Lista Negra (Opt-Out)

Aquí aparecen las empresas que **no quieren ser contactadas**. El sistema bloquea automáticamente cualquier intento de enviarles correos.

**Para registrar una exclusión manual:**
1. Baja hasta "Registrar nueva exclusión manual"
2. Ingresa el ID de la empresa y el motivo
3. Haz clic en "🚫 Registrar Opt-Out"

**Para reactivar una empresa** (solo si el titular lo autorizó expresamente):
- Haz clic en "↩️ Reactivar" al lado de la empresa

> **Nota legal:** Registrar el opt-out cuando alguien lo pide NO es opcional. Es una obligación de la Ley 1581 de 2012. El sistema te protege automatizando esto.

---

## 8. Analítica y Conversión

**¿Para qué sirve?** Mide el rendimiento de tu estrategia comercial y te dice qué está funcionando y qué no.

### Pestaña: Embudo de Conversión

Muestra en detalle cuántas empresas hay en cada etapa y **qué porcentaje abandona** entre una etapa y la siguiente.

**Ejemplo de lectura:**
- 100 empresas en Leads Nuevos
- 60 llegaron a Contactados → 40% abandonó antes de ser contactado (hay que enviar más correos)
- 20 llegaron a Cotización Enviada → 67% no siguió (el correo de primer contacto puede mejorar)

### Pestaña: Rendimiento de Correos

Muestra:
- Total de correos enviados
- **Tasa de apertura** (solo si tienes `TRACKING_URL` configurado en `.env`)
- **Tasa de respuesta** (detectada automáticamente si tienes Gmail configurado)
- Gráfico de correos enviados por semana
- Qué asuntos de correo tienen mejor respuesta

### Pestaña: Optimización IA

Si tienes `ANTHROPIC_API_KEY` en el `.env`:
1. Haz clic en **"⚡ Analizar y Optimizar con Claude"**
2. Claude analiza los asuntos de tus correos y su rendimiento
3. Te devuelve diagnóstico + 3 nuevos asuntos optimizados para el mercado SST colombiano

### Pestaña: Detección de Respuestas

Si tienes Gmail configurado, esto corre **automáticamente todos los días a las 8:20 a.m.**, 10 minutos antes de que salga la cadencia de correos. También puedes forzarlo manualmente:
1. Haz clic en **"📥 Detectar Respuestas Ahora"**
2. El sistema escanea tu bandeja de entrada de los últimos 30 días
3. Según lo que haya contestado el prospecto:
   - **Respuesta negativa** ("no me interesa", "ya contamos con ese servicio", "quítenme de la lista", etc.) → lo registra automáticamente en la **lista negra (opt-out)** y el software deja de escribirle para siempre. Cumple la Ley 1581 sin que tengas que hacerlo a mano.
   - **Respuesta afirmativa** ("sí", "me interesa", "cuéntenme más", etc.) → lo marca como **"pidió portafolio"**, y la empresa aparece lista en la pestaña de Portafolio para enviarle el PDF con un clic.
   - Cualquier otra respuesta queda marcada como "RESPONDIDO" en el historial para que la revises tú misma.

> **Nota:** La primera vez que uses esta función puede pedir que re-autorices Gmail porque necesita permiso de lectura adicional.

### Pestaña: ROI del Software

Calcula cuánto dinero te ha generado el sistema:

1. **Valor promedio contrato SST**: ¿Cuánto cobra Medina SST en promedio por contrato? (ej: $5.000.000 COP)
2. **Costo del software**: cuánto costó desarrollarlo
3. El sistema calcula automáticamente los **contratos cerrados desde la BD**
4. Te muestra el ROI en % y la curva de break-even (cuántos contratos necesitas para recuperar la inversión)

Haz clic en **"💾 Guardar como valores por defecto"** para que no tengas que volverlos a ingresar.

---

## 9. Fábrica de Contenido

**¿Para qué sirve?** Genera automáticamente artículos técnicos sobre SST para publicar en redes sociales. Un artículo diario = 365 posts al año sin esfuerzo manual.

> **Requiere:** `GEMINI_API_KEY` en el `.env` (la misma que usan los correos)

### Cómo generar el artículo del día:

**1. Ve a la pestaña "✍️ Generar Artículo"**

Verás el **tema del día** seleccionado automáticamente (hay 28 temas en rotación mensual sobre normatividad SST).

**2. Opciones antes de generar:**
- **Motor de imágenes**: si tienes `OPENAI_API_KEY`, selecciona "DALL-E 3" para imágenes reales. Si no, usa "Mock" y el sistema guarda los prompts listos para usar en Midjourney o DALL-E web.
- **Plataforma principal**: selecciona si quieres ver el copy de LinkedIn, Facebook, Instagram o todos.
- Si quieres un tema diferente al automático, expande "🔄 Cambiar tema manualmente".

**3. Haz clic en "⚡ Generar Artículo de Hoy"**

En 10-20 segundos, Gemini te genera:
- Artículo completo en Markdown (500-700 palabras)
- Copy listo para LinkedIn, Facebook e Instagram por separado
- 8 hashtags relevantes
- Llamado a la acción

**4. Panel de publicación:**

Por cada plataforma (LinkedIn, Facebook, Instagram) verás:

- Si NO tienes los tokens OAuth configurados → **Modo Manual**: el texto está listo para copiar y pegar. El contador te dice cuántos caracteres usas (LinkedIn permite hasta 3.000, Instagram hasta 2.200).
- Si SÍ tienes los tokens configurados → botón **"📤 Publicar en [Plataforma]"** que lo publica directamente.

**5. Guarda en el Calendario:**
Haz clic en **"💾 Guardar en Calendario"** para registrar el artículo en la base de datos.

### Cómo configurar la publicación automática (cuando tengas las credenciales):

Abre el `.env` y llena la sección **"REDES SOCIALES"**:

**Para LinkedIn:**
1. Ve a https://www.linkedin.com/developers/apps → crea una app
2. Activa permisos: `w_organization_social` + `r_organization_social`
3. Genera el Access Token
4. Pega en: `LINKEDIN_ACCESS_TOKEN=` y `LINKEDIN_ORGANIZATION_ID=`

**Para Facebook e Instagram:**
1. Ve a https://developers.facebook.com → crea app de tipo Business
2. Agrega el producto "Pages API"
3. Genera Page Access Token
4. Pega en: `META_PAGE_ACCESS_TOKEN=`, `META_FACEBOOK_PAGE_ID=`, `META_INSTAGRAM_ACCOUNT_ID=`

Después de llenar los tokens, **reinicia el software**: cierra la ventana del panel y la del scheduler, y vuelve a abrir `start.bat`.

### Pestaña: Calendario

Muestra el contenido programado. Cada artículo tiene un estado:
- **PENDIENTE**: generado pero aún no publicado
- **PUBLICADO**: ya está en redes
- **ERROR**: hubo un problema al publicar

Cuando publiques manualmente en una red social, haz clic en **"✅ Publicado"** para registrarlo.

---

## 10. Alianza Compecer

**¿Para qué sirve?** Lleva el registro de las empresas que le refieres a Compecer para certificaciones ISO (9001, 45001, 14001, 27001, entre otras), y en qué punto va cada referido: enviado, en negociación, contrato firmado o bonificación cobrada.

**Cómo funciona:**
1. Registras el referido con su razón social, NIT, contacto y la norma ISO que le interesa
2. Actualizas el estado a medida que avanza la negociación con Compecer
3. Cuando se firma el contrato y se cobra la bonificación, lo marcas como "Bonificación cobrada"

Esto te permite ver de un vistazo cuántos referidos tienes activos y cuánto representan en comisiones pendientes.

---

## 11. Flujo de trabajo diario recomendado

### Lunes — Prospección (20 min)

1. Abre el **Motor de Prospección**
2. Busca 30-50 empresas nuevas por ciudad y sector
3. Revisa en el **Panel de Control** que el embudo recibió nuevas empresas

### Martes a Jueves — Seguimiento (15 min/día)

1. Abre **Campañas y Habeas Data**
2. Revisa si hay prospectos NUEVOS sin contactar → envía correos masivos
3. Revisa la **Ficha** de los prospectos que respondieron
4. Si alguno está interesado → genera cotización en el **Cotizador**

### Viernes — Análisis (10 min)

1. Abre **Analítica y Conversión**
2. Revisa la tasa de respuesta de la semana
3. Haz clic en **"Detectar Respuestas"** para actualizar el CRM
4. Si tienes ANTHROPIC_API_KEY → ejecuta **"Optimizar con IA"** para mejorar los asuntos de correo

### Todos los días — Contenido (5 min)

1. Abre **Fábrica de Contenido**
2. Genera el artículo del día
3. Copia el copy de la plataforma que vayas a usar
4. Publica en redes → marca como Publicado en el Calendario

---

## 12. Preguntas frecuentes

**¿Por qué no puedo enviar correos?**

Posibles causas:
- No tienes el archivo `credentials/gmail_credentials.json`. Sigue las instrucciones de configuración de Gmail en el módulo de correos.
- Llegaste al límite diario de envíos (el sistema te avisará cuándo ocurra).
- La empresa está en la Lista Negra (Opt-Out activo).

**¿Por qué el Cotizador no genera PDF?**

- Verifica que la carpeta `output/` exista. Si no, créala manualmente.
- Verifica que `reportlab` esté instalado: `pip install reportlab`

**¿Por qué no veo datos en el Panel de Control?**

La base de datos está vacía. Primero debes:
1. Ejecutar `python -m src.database.init_db`
2. Agregar empresas con el **Motor de Prospección** o el **Cotizador** (botón "Guardar en CRM")

**¿Qué pasa si apago el computador?**

Todos los datos están guardados en `comercial.db` (la base de datos local). Al volver a abrir `start.bat` todo estará exactamente como lo dejaste.

**¿Se pueden perder los datos?**

Los datos solo se perderían si eliminas el archivo `comercial.db`. Se recomienda hacer una copia de seguridad periódica de ese archivo a una carpeta en la nube (OneDrive, Google Drive).

**¿El software funciona sin internet?**

Sí, para: Cotizador, Panel de Control, ver el CRM, Analítica.

No, para: Motor de Prospección (necesita buscar en internet), envío de correos (necesita Gmail), Fábrica de Contenido (necesita conectarse a Gemini).

**¿Cómo sé si un correo fue recibido?**

Por ahora puedes ver en la **Ficha del Cliente** si el correo aparece como ENVIADO. Para saber si fue ABIERTO necesitas configurar `TRACKING_URL` (servidor externo adicional).

**¿Cómo cambio el precio por hora de las cotizaciones?**

En el archivo `src/modules/cotizador/calculator.py`, línea 14:
```python
VALOR_HORA_COP = Decimal("88_000")
```
Cambia `88_000` por el valor deseado (en pesos colombianos, sin puntos).

---

## 13. Glosario

| Término | Significado |
|---|---|
| **CRM** | Base de datos de clientes y prospectos. Sigla de Customer Relationship Management. |
| **Prospecto** | Empresa que aún no es cliente pero podría serlo. |
| **Embudo de ventas** | El camino que recorre un prospecto desde que lo conoces hasta que firma contrato. |
| **Opt-Out / Lista Negra** | Empresa que pidió no ser contactada. Ley 1581/2012 obliga a respetar esta solicitud. |
| **SG-SST** | Sistema de Gestión de Seguridad y Salud en el Trabajo. |
| **Resolución 0312/2019** | Ley que define cuántos estándares mínimos de seguridad debe tener cada empresa según su tamaño y riesgo. |
| **ARL** | Administradora de Riesgos Laborales. La riesgo va de I (bajo) a V (muy alto). |
| **Viáticos** | Costos de transporte y alojamiento cuando el servicio se presta fuera de Bogotá. |
| **OAuth** | Sistema de permisos para conectar el software con Gmail, LinkedIn o Meta sin compartir contraseñas. |
| **API Key** | Contraseña especial que identifica al software frente a un servicio externo (Claude, Gmail, etc.). |
| **`.env`** | Archivo de configuración con las claves y datos privados. Nunca se comparte públicamente. |
| **BD / Base de datos** | Archivo `comercial.db` donde se guardan todos los prospectos, cotizaciones e interacciones. |
| **Token** | Clave de acceso temporal o permanente para una API. Similar a una contraseña de sesión. |
| **Gemini** | El modelo de Inteligencia Artificial de Google que usa el software para redactar el gancho de cada correo y los artículos de la Fábrica de Contenido. Es el que le da variedad al texto según el sector de cada empresa. |
| **Claude** | El modelo de Inteligencia Artificial de Anthropic. En este software se usa solo en Analítica, para sugerir mejores asuntos de correo según su rendimiento histórico. |
| **Open Rate** | Porcentaje de correos enviados que los destinatarios abrieron. |
| **ROI** | Retorno de Inversión. Cuánto ganaste en relación a lo que gastaste. |
| **Break-even** | Punto de equilibrio: cuántos contratos necesitas cerrar para recuperar lo que costó el software. |

---

*Manual actualizado el 20 de agosto de 2026 · Medina SST Empresarial SAS · v1.0*
