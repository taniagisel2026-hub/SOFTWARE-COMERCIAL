# Flujo Comercial — Cómo funciona el software de principio a fin

Panel Comercial · Medina SST Empresarial SAS

---

## ¿Para qué sirve este software?

Conseguir clientes para Medina SST de forma organizada y automatizada — desde encontrar empresas que necesitan el servicio, hasta enviarles una propuesta económica. Todo queda registrado y nada se pierde.

---

## Paso 1 — Motor de Prospección 🕵️

**Aquí empieza todo.**

Entras al módulo y le dices al software: *"Búscame empresas en Bogotá del sector Construcción"*. El sistema sale a internet, revisa Google Maps, LinkedIn y páginas web, y trae una lista de empresas con su nombre, teléfono, email y dirección. Todo eso lo guarda automáticamente en la base de datos.

Esas empresas son tus **leads** — clientes potenciales que todavía no saben que existen.

---

## Paso 2 — Campañas y Habeas Data ✉️

**Ahora les escribes — y esto ya corre solo, todos los días.**

Con las empresas ya guardadas, el sistema envía automáticamente de lunes a viernes a las 8:30 a.m. una secuencia de tres correos por empresa: **Día 1** (primer contacto), **Día 4** (recordatorio, si no respondió) y **Día 8** (último contacto, cierre cordial). Cada correo trae un gancho de apertura distinto generado con IA según el sector de la empresa, y un botón verde para escribir directo por WhatsApp. También puedes enviarlos manualmente desde el módulo si lo prefieres.

El sistema respeta un límite diario de envíos para que los correos no lleguen a spam, y todos los días a las 8:15 revisa Gmail para excluir de la cadencia los correos que rebotan (direcciones inválidas).

**A las 8:20, antes de enviar nada, el sistema también revisa si algún prospecto respondió:**
- Si la respuesta es negativa ("no me interesa", "ya contamos con eso", etc.) → lo registra automáticamente en la **lista negra (opt-out)** y el software deja de escribirle para siempre.
- Si la respuesta es afirmativa ("sí", "me interesa", etc.) → lo marca como **"pidió portafolio"**, y aparece listo en el panel para enviarle el portafolio con un clic.

Esto cumple con la **Ley 1581 de 2012 (Habeas Data)** — protección de datos personales en Colombia. También puedes registrar una exclusión manual en cualquier momento desde la pestaña de Lista Negra.

---

## Paso 3 — Panel de Control 📊

**Ves cómo va todo.**

Después de enviar correos puedes entrar aquí y ver en tiempo real cuántos correos se enviaron, cuántos fueron abiertos, y en qué etapa del proceso está cada empresa. El embudo de ventas muestra cuántas empresas están en cada paso:

```
Nuevo lead → Contactado → Cotización enviada → Negociación → Cierre
```

Se actualiza automáticamente cada 30 segundos.

---

## Paso 4 — Analítica y Conversión 📈

**Mides qué está funcionando.**

Si ves que muchos correos se abren pero nadie responde, algo está fallando en el mensaje. Si nadie abre los correos, puede ser el asunto. Este módulo da estadísticas detalladas para tomar decisiones: cambiar el texto del correo, enfocarse en otro sector, o priorizar las empresas que ya respondieron.

**Métricas disponibles:**
- Tasa de apertura de correos
- Tasa de respuesta
- Tasa de conversión a cotización
- Evolución del pipeline semana a semana

---

## Paso 5 — Cotizador 🧮

**Una empresa interesada pide precio.**

Cuando una empresa responde y quiere saber cuánto cuesta el servicio, entras al cotizador. Ingresas los datos de esa empresa, seleccionas los servicios que necesita, indica cuánto cobrar por cada uno. El sistema suma todo y genera un **PDF profesional con el logo de Medina SST** listo para enviarle al cliente por correo o WhatsApp.



---

## Paso 6 — Fábrica de Contenido 🎨

**Mientras tanto, construyes presencia en redes.**

Este módulo trabaja en paralelo con todo lo anterior. Con un clic genera un artículo sobre SST y los textos listos para publicar en LinkedIn, Facebook e Instagram. La idea es que mientras el software busca clientes y envía correos, Medina SST también aparezca en redes sociales como empresa experta en el tema — eso genera confianza cuando un prospecto busca la empresa en internet antes de responder.

---

## El ciclo completo

```
1. Buscar empresas (Motor de Prospección)
        ↓
2. Enviarles correos personalizados (Campañas)
        ↓
3. Ver quién abrió y en qué etapa está (Panel de Control)
        ↓
4. Analizar qué está funcionando (Analítica)
        ↓
5. Cotizar a los interesados (Cotizador → PDF al cliente)
        ↓
6. Publicar en redes para generar confianza (Fábrica de Contenido)
```

---

## Lo que queda registrado en la base de datos

Todo el proceso queda guardado. En cualquier momento se puede saber:

- Qué empresa está en qué etapa del proceso
- Cuándo fue el último contacto con cada empresa
- Si ya recibió una propuesta y cuál fue el valor
- Quién pidió no ser contactado (Habeas Data)
- Qué contenido se ha publicado en redes

---

## Cómo abrir el software

1. Doble clic en **`start.bat`**
2. Se abren dos ventanas: una minimizada con el nombre "Medina SST Scheduler" (es la que envía los correos automáticos todos los días a las horas de arriba — **no la cierres**) y el panel visual, que se abre solo en el navegador
3. Para apagar el software, cierra la ventana del panel

Si el computador tiene configurado el arranque automático (`setup_autostart.bat`), estas dos ventanas ya aparecen solas al encender el equipo — no hace falta darle doble clic a `start.bat` de nuevo, porque eso abriría una segunda copia del scheduler.

El software corre en el computador local — solo lo ve quien lo abre. Los clientes no tienen acceso.

---

*Panel Comercial · Medina SST Empresarial SAS · v1.0.0*
