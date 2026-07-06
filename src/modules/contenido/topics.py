"""
Catálogo de temas SST con rotación diaria automática.
56 temas cubren un ciclo de ~8 semanas sin repetición.
"""
import json
from datetime import date
from pathlib import Path
from typing import NamedTuple

# Estado persistido de la rotación: {"fecha": "2026-07-06", "indice": 0}.
# Avanza un tema por dia calendario, en el mismo orden del CATALOGO_TEMAS
# (antes rotaba por dia del año, lo que hacia empezar a mitad de la lista
# segun la fecha en que se usara por primera vez).
_ESTADO_PATH = Path(__file__).parent.parent.parent.parent / "data" / "tema_contenido_estado.json"


class TemaSSTInfo(NamedTuple):
    categoria: str
    titulo_base: str
    descripcion_brief: str
    palabras_clave: list[str]
    angulo_narrativo: str


CATALOGO_TEMAS: list[TemaSSTInfo] = [

    # ── DOLORES DEL CLIENTE (7 temas) ────────────────────────────────────────
    TemaSSTInfo(
        categoria="DOLOR_CLIENTE",
        titulo_base="PYMEs colombianas sin SG-SST: el costo real que nadie calcula",
        descripcion_brief="Las microempresas desconocen el costo acumulado de no tener el SG-SST: multas, demandas y pérdida de contratos",
        palabras_clave=["SG-SST", "PYME", "multas", "Ministerio del Trabajo", "Colombia"],
        angulo_narrativo="problema_consecuencia",
    ),
    TemaSSTInfo(
        categoria="DOLOR_CLIENTE",
        titulo_base="Accidente de trabajo: la cronología de una demanda que pudo evitarse",
        descripcion_brief="Caso ilustrativo de cómo un accidente sin SG-SST activo lleva a demandas civiles y penales",
        palabras_clave=["accidente de trabajo", "responsabilidad laboral", "ARL", "demanda"],
        angulo_narrativo="caso_practico",
    ),
    TemaSSTInfo(
        categoria="DOLOR_CLIENTE",
        titulo_base="Tu empresa perdió un contrato por no tener SG-SST vigente. ¿Sabías que esto es posible?",
        descripcion_brief="Muchas licitaciones públicas y privadas exigen el SG-SST como requisito de habilitación",
        palabras_clave=["licitación", "SG-SST obligatorio", "contratación pública", "requisito"],
        angulo_narrativo="oportunidad_perdida",
    ),
    TemaSSTInfo(
        categoria="DOLOR_CLIENTE",
        titulo_base="Estrés laboral y ausentismo: los costos ocultos que destruyen tu rentabilidad",
        descripcion_brief="El riesgo psicosocial no controlado genera ausentismo crónico y alta rotación de personal",
        palabras_clave=["riesgo psicosocial", "ausentismo", "rotación", "batería MinTrabajo"],
        angulo_narrativo="impacto_financiero",
    ),
    TemaSSTInfo(
        categoria="DOLOR_CLIENTE",
        titulo_base="¿Cuánto tiempo tiene tu empresa para implementar el SG-SST antes de la siguiente visita?",
        descripcion_brief="Los inspectores del MinTrabajo tienen un plan de visitas por sector. ¿Tu empresa está preparada?",
        palabras_clave=["inspección MinTrabajo", "visita SENA", "SG-SST urgente", "plazo"],
        angulo_narrativo="urgencia_temporal",
    ),
    TemaSSTInfo(
        categoria="DOLOR_CLIENTE",
        titulo_base="El mito de 'mi empresa es pequeña y no me van a multar': desmontado con cifras",
        descripcion_brief="Las microempresas son inspeccionadas con la misma frecuencia que las grandes. Los datos lo prueban.",
        palabras_clave=["microempresa", "inspección laboral", "multa SST", "Decreto 472"],
        angulo_narrativo="mito_vs_realidad",
    ),
    TemaSSTInfo(
        categoria="DOLOR_CLIENTE",
        titulo_base="Trabajador enfermo, empresa en riesgo: la cadena de responsabilidad que te puede hundir",
        descripcion_brief="Cuando un empleado desarrolla una enfermedad laboral, la empresa es la primera responsable si no tiene SG-SST",
        palabras_clave=["enfermedad laboral", "enfermedad profesional", "responsabilidad empresa", "ARL"],
        angulo_narrativo="cadena_responsabilidad",
    ),

    # ── NORMATIVA RESOLUCIÓN 0312 (6 temas) ─────────────────────────────────
    TemaSSTInfo(
        categoria="NORMATIVA_0312",
        titulo_base="Resolución 0312 de 2019: la guía completa que toda empresa colombiana necesita leer",
        descripcion_brief="Explicación clara de los tres niveles de estándares mínimos y a cuál le aplica cada empresa",
        palabras_clave=["Resolución 0312", "estándares mínimos", "SG-SST", "MinTrabajo 2019"],
        angulo_narrativo="guia_educativa",
    ),
    TemaSSTInfo(
        categoria="NORMATIVA_0312",
        titulo_base="7 estándares del SG-SST: lo que debe tener una empresa de menos de 10 trabajadores",
        descripcion_brief="Desglose práctico del Artículo 3 de la Res. 0312 para microempresas con riesgo I, II y III",
        palabras_clave=["7 estándares", "microempresa", "riesgo I II III", "Artículo 3"],
        angulo_narrativo="desglose_practico",
    ),
    TemaSSTInfo(
        categoria="NORMATIVA_0312",
        titulo_base="21 estándares del SG-SST: la hoja de ruta para empresas de 11 a 50 trabajadores",
        descripcion_brief="Cómo implementar los 21 estándares del Artículo 16 paso a paso sin contratar un equipo enorme",
        palabras_clave=["21 estándares", "Artículo 16", "mediana empresa", "implementación"],
        angulo_narrativo="hoja_de_ruta",
    ),
    TemaSSTInfo(
        categoria="NORMATIVA_0312",
        titulo_base="60 estándares del SG-SST: lo que las empresas grandes y de alto riesgo deben cumplir sí o sí",
        descripcion_brief="El Artículo 27 aplica a más de 50 trabajadores o riesgo IV/V. Aquí lo explicamos todo.",
        palabras_clave=["60 estándares", "Artículo 27", "riesgo IV V", "empresa grande"],
        angulo_narrativo="cumplimiento_avanzado",
    ),
    TemaSSTInfo(
        categoria="NORMATIVA_0312",
        titulo_base="La autoevaluación anual del SG-SST: cómo hacerla bien y no quedarse en el papel",
        descripcion_brief="El ciclo PHVA aplicado al SG-SST: planear, hacer, verificar y actuar en la práctica real",
        palabras_clave=["autoevaluación SG-SST", "ciclo PHVA", "plan de mejoramiento", "auditoría"],
        angulo_narrativo="proceso_pratico",
    ),
    TemaSSTInfo(
        categoria="NORMATIVA_0312",
        titulo_base="Riesgo ARL: cómo saber en qué clase está tu empresa y qué cambia para el SG-SST",
        descripcion_brief="Diferencias entre riesgo I, II, III, IV y V según el Decreto 1607/2002 y su impacto en la Res. 0312",
        palabras_clave=["nivel de riesgo", "ARL", "Decreto 1607", "clasificación empresas"],
        angulo_narrativo="conceptual_practico",
    ),

    # ── AUDITORÍAS E INSPECCIONES (5 temas) ──────────────────────────────────
    TemaSSTInfo(
        categoria="AUDITORIA_INTERNA",
        titulo_base="Cómo sobrevivir una inspección del Ministerio del Trabajo sin entrar en pánico",
        descripcion_brief="Lista de verificación de los documentos que el inspector siempre pide en Colombia",
        palabras_clave=["inspección MinTrabajo", "documentos SG-SST", "inspector laboral", "visita"],
        angulo_narrativo="checklist_supervivencia",
    ),
    TemaSSTInfo(
        categoria="AUDITORIA_INTERNA",
        titulo_base="Auditoría interna del SG-SST: el proceso que evita las sorpresas con el Ministerio",
        descripcion_brief="Por qué las empresas que auditan internamente cada año nunca tienen problemas con las inspecciones externas",
        palabras_clave=["auditoría interna", "SG-SST", "mejora continua", "no conformidades"],
        angulo_narrativo="prevencion_proactiva",
    ),
    TemaSSTInfo(
        categoria="AUDITORIA_INTERNA",
        titulo_base="No conformidades del SG-SST: cómo convertir un hallazgo en una oportunidad de mejora",
        descripcion_brief="Metodología para registrar, analizar y cerrar no conformidades en el SG-SST de manera efectiva",
        palabras_clave=["no conformidades", "plan de mejoramiento", "SG-SST", "acciones correctivas"],
        angulo_narrativo="mejora_continua",
    ),
    TemaSSTInfo(
        categoria="AUDITORIA_INTERNA",
        titulo_base="La revisión por la alta dirección: el paso que el 80% de las empresas se salta",
        descripcion_brief="Sin la firma y revisión del gerente, el SG-SST no está completo. Qué debe contener este documento clave.",
        palabras_clave=["revisión alta dirección", "gerente SG-SST", "liderazgo SST", "documentación"],
        angulo_narrativo="requisito_critico",
    ),
    TemaSSTInfo(
        categoria="AUDITORIA_INTERNA",
        titulo_base="Indicadores del SG-SST que todo gerente colombiano debería monitorear mensualmente",
        descripcion_brief="Los indicadores de estructura, proceso y resultado que exige la Res. 0312 y cómo interpretarlos",
        palabras_clave=["indicadores SG-SST", "KPI SST", "tasa accidentalidad", "frecuencia", "severidad"],
        angulo_narrativo="gestion_con_datos",
    ),

    # ── HIGIENE INDUSTRIAL (5 temas) ─────────────────────────────────────────
    TemaSSTInfo(
        categoria="HIGIENE_INDUSTRIAL",
        titulo_base="Matriz de peligros GTC-45: el corazón de todo SG-SST que funciona",
        descripcion_brief="Cómo identificar, valorar y controlar los riesgos laborales usando la metodología más aceptada en Colombia",
        palabras_clave=["GTC-45", "matriz de peligros", "valoración de riesgos", "identificación peligros"],
        angulo_narrativo="metodologia_fundamental",
    ),
    TemaSSTInfo(
        categoria="HIGIENE_INDUSTRIAL",
        titulo_base="Ruido industrial en el trabajo: cuándo se convierte en un problema legal para tu empresa",
        descripcion_brief="Niveles permitidos por la normativa colombiana y cómo demostrar que tu empresa los controla",
        palabras_clave=["ruido industrial", "higiene laboral", "hipoacusia", "medición higiénica"],
        angulo_narrativo="riesgo_fisico",
    ),
    TemaSSTInfo(
        categoria="HIGIENE_INDUSTRIAL",
        titulo_base="Sustancias químicas en el trabajo: cómo elaborar el inventario de productos peligrosos",
        descripcion_brief="La hoja de datos de seguridad (HDS/MSDS) es obligatoria. Aquí te explicamos cómo gestionarlas.",
        palabras_clave=["sustancias químicas", "HDS", "MSDS", "productos peligrosos", "riesgo químico"],
        angulo_narrativo="riesgo_quimico",
    ),
    TemaSSTInfo(
        categoria="HIGIENE_INDUSTRIAL",
        titulo_base="Plan de emergencias en Colombia: por qué el 60% de las empresas tienen uno que no funciona",
        descripcion_brief="Los errores más comunes en los planes de emergencia y cómo construir uno que realmente proteja a tus trabajadores",
        palabras_clave=["plan de emergencias", "evacuación", "brigada de emergencias", "simulacro"],
        angulo_narrativo="diagnostico_problemas",
    ),
    TemaSSTInfo(
        categoria="HIGIENE_INDUSTRIAL",
        titulo_base="Medicina preventiva del trabajo: por qué los exámenes médicos ocupacionales son obligatorios",
        descripcion_brief="Ingreso, periódico y egreso: la triada de exámenes que protege a tu empresa y a tus empleados",
        palabras_clave=["exámenes médicos", "medicina preventiva", "ingreso egreso periódico", "aptitud laboral"],
        angulo_narrativo="prevencion_salud",
    ),

    # ── SANCIONES DECRETO 472 (3 temas) ─────────────────────────────────────
    TemaSSTInfo(
        categoria="SANCIONES_DECRETO_472",
        titulo_base="Decreto 472 de 2015: la tabla de multas del MinTrabajo que debes imprimir y pegar en tu oficina",
        descripcion_brief="Montos actualizados en SMMLV para cada tipo de infracción en SST. Las cifras asustan.",
        palabras_clave=["Decreto 472", "multas MinTrabajo", "SMMLV", "sanciones laborales", "infracción SST"],
        angulo_narrativo="informacion_critica",
    ),
    TemaSSTInfo(
        categoria="SANCIONES_DECRETO_472",
        titulo_base="Empresa multada por el MinTrabajo: ¿qué hacer en las primeras 48 horas?",
        descripcion_brief="El protocolo de respuesta ante una sanción del Ministerio del Trabajo y cómo apelarla con éxito",
        palabras_clave=["multa laboral", "sanción MinTrabajo", "recurso de reposición", "descargos"],
        angulo_narrativo="crisis_management",
    ),
    TemaSSTInfo(
        categoria="SANCIONES_DECRETO_472",
        titulo_base="Cierre de empresa por incumplimientos SST: los 3 casos recientes que Colombia necesita conocer",
        descripcion_brief="El MinTrabajo tiene la potestad de ordenar el cierre temporal. Estos casos reales muestran cómo ocurre.",
        palabras_clave=["cierre empresa", "MinTrabajo", "suspensión actividades", "sanción grave SST"],
        angulo_narrativo="casos_reales_advertencia",
    ),

    # ── CASOS DE ÉXITO Y CULTURA (2 temas) ───────────────────────────────────
    TemaSSTInfo(
        categoria="CASO_EXITO",
        titulo_base="Cómo una empresa de construcción en Bogotá redujo su accidentalidad en un 70% en 12 meses",
        descripcion_brief="Historia de transformación real: de 0 a SG-SST activo en 3 meses con resultados medibles",
        palabras_clave=["caso de éxito", "reducción accidentalidad", "construcción SST", "resultados"],
        angulo_narrativo="transformacion_exitosa",
    ),
    TemaSSTInfo(
        categoria="CASO_EXITO",
        titulo_base="Cultura de seguridad: el factor que diferencia a las empresas que nunca tienen accidentes",
        descripcion_brief="Por qué el SG-SST no es solo documentación: el componente humano y conductual que lo hace funcionar",
        palabras_clave=["cultura de seguridad", "liderazgo SST", "comportamiento seguro", "compromiso gerencial"],
        angulo_narrativo="cambio_cultural",
    ),

    # ── RIESGOS ESPECÍFICOS (6 temas) ────────────────────────────────────────
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Trabajo en alturas en Colombia: la certificación que su empresa no puede pasar por alto",
        descripcion_brief="Resolución 4272 de 2021: quién debe certificarse, con qué frecuencia y qué pasa si no se cumple",
        palabras_clave=["trabajo en alturas", "Resolución 4272", "certificación alturas", "riesgo de caída"],
        angulo_narrativo="requisito_critico",
    ),
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Espacios confinados: el riesgo silencioso que mata más rápido de lo que se piensa",
        descripcion_brief="Protocolos de entrada segura, monitoreo de gases y por qué la mayoría de las muertes ocurren en el rescate",
        palabras_clave=["espacios confinados", "riesgo asfixia", "monitoreo de gases", "rescate"],
        angulo_narrativo="riesgo_critico",
    ),
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Ergonomía en la oficina: por qué el dolor de espalda de su equipo también es un tema de SG-SST",
        descripcion_brief="Desórdenes músculo-esqueléticos en trabajo de oficina, la enfermedad laboral que más silenciosamente crece",
        palabras_clave=["ergonomía", "desórdenes músculo-esqueléticos", "puesto de trabajo", "oficina"],
        angulo_narrativo="riesgo_subestimado",
    ),
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Riesgo biológico en el trabajo: protocolos que toda empresa de salud y alimentos debe tener",
        descripcion_brief="Bioseguridad, manejo de residuos peligrosos y exposición a agentes biológicos en sectores de alto contacto",
        palabras_clave=["riesgo biológico", "bioseguridad", "residuos peligrosos", "sector salud"],
        angulo_narrativo="riesgo_sectorial",
    ),
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Bloqueo y etiquetado (LOTO): el paso que evita que un mantenimiento se convierta en tragedia",
        descripcion_brief="Por qué liberar energía peligrosa sin control mata operarios de mantenimiento cada año en Colombia",
        palabras_clave=["bloqueo y etiquetado", "LOTO", "mantenimiento seguro", "energía peligrosa"],
        angulo_narrativo="procedimiento_critico",
    ),
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Manejo manual de cargas: el riesgo que casi ninguna PYME controla y que más incapacidades genera",
        descripcion_brief="Límites de peso, técnicas de levantamiento y cómo un mal hábito se vuelve enfermedad laboral crónica",
        palabras_clave=["manejo de cargas", "levantamiento de peso", "lumbalgia", "incapacidad laboral"],
        angulo_narrativo="habito_riesgoso",
    ),
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Batería de Riesgo Psicosocial: el examen obligatorio que la mayoría de empresas colombianas aplica mal",
        descripcion_brief="Resolución 2646 de 2008: quién debe aplicarla, cada cuánto, y por qué no es solo una encuesta de clima laboral",
        palabras_clave=["batería de riesgo psicosocial", "Resolución 2646", "riesgo psicosocial", "clima laboral"],
        angulo_narrativo="requisito_critico",
    ),
    TemaSSTInfo(
        categoria="RIESGOS_ESPECIFICOS",
        titulo_base="Acoso laboral y riesgo psicosocial: la línea que muchas empresas colombianas no saben dónde trazar",
        descripcion_brief="Ley 1010 de 2006 y su relación con el SG-SST: cómo prevenir, documentar y actuar ante el acoso laboral",
        palabras_clave=["acoso laboral", "Ley 1010", "riesgo psicosocial", "comité de convivencia"],
        angulo_narrativo="aclaracion_legal",
    ),

    # ── SST POR SECTOR (6 temas) ─────────────────────────────────────────────
    TemaSSTInfo(
        categoria="SST_SECTOR",
        titulo_base="SG-SST en construcción: los 5 riesgos que el Ministerio del Trabajo revisa primero",
        descripcion_brief="Alturas, excavaciones, maquinaria pesada: por qué construcción es el sector más inspeccionado",
        palabras_clave=["SST construcción", "riesgo IV", "obra civil", "inspección sector construcción"],
        angulo_narrativo="riesgo_sectorial",
    ),
    TemaSSTInfo(
        categoria="SST_SECTOR",
        titulo_base="Transporte y logística: por qué la fatiga del conductor ya es un tema de SG-SST, no solo de tránsito",
        descripcion_brief="Jornadas laborales, pausas obligatorias y la relación directa entre fatiga y accidentalidad vial laboral",
        palabras_clave=["SST transporte", "fatiga del conductor", "jornada laboral", "accidentalidad vial"],
        angulo_narrativo="riesgo_sectorial",
    ),
    TemaSSTInfo(
        categoria="SST_SECTOR",
        titulo_base="Comercio y retail: los riesgos invisibles detrás del mostrador que nadie reporta",
        descripcion_brief="Caídas, estrés por atención al público y jornadas extendidas: el SG-SST que el retail suele ignorar",
        palabras_clave=["SST retail", "SST comercio", "riesgo psicosocial retail", "caídas mismo nivel"],
        angulo_narrativo="riesgo_subestimado",
    ),
    TemaSSTInfo(
        categoria="SST_SECTOR",
        titulo_base="Sector salud: cuando quienes cuidan la salud de otros descuidan la suya propia",
        descripcion_brief="Riesgo biológico, turnos extendidos y violencia laboral en clínicas y hospitales colombianos",
        palabras_clave=["SST sector salud", "riesgo biológico", "turnos extendidos", "violencia laboral"],
        angulo_narrativo="riesgo_sectorial",
    ),
    TemaSSTInfo(
        categoria="SST_SECTOR",
        titulo_base="Manufactura e industria: cómo controlar el riesgo mecánico sin detener la producción",
        descripcion_brief="Guardas de seguridad, mantenimiento preventivo y la relación entre productividad y prevención",
        palabras_clave=["SST manufactura", "riesgo mecánico", "guardas de seguridad", "planta industrial"],
        angulo_narrativo="riesgo_sectorial",
    ),
    TemaSSTInfo(
        categoria="SST_SECTOR",
        titulo_base="Seguridad privada: el sector con más accidentalidad laboral que casi nadie menciona",
        descripcion_brief="Jornadas extensas, exposición a violencia y por qué el SG-SST en vigilancia es distinto al de otros sectores",
        palabras_clave=["SST vigilancia", "seguridad privada", "riesgo público", "jornada extensa"],
        angulo_narrativo="riesgo_sectorial",
    ),

    # ── PREGUNTAS FRECUENTES (6 temas) ───────────────────────────────────────
    TemaSSTInfo(
        categoria="PREGUNTAS_FRECUENTES",
        titulo_base="¿Necesito un profesional en SST de tiempo completo o puedo contratarlo por horas?",
        descripcion_brief="Requisitos según el número de trabajadores y nivel de riesgo — cuándo es obligatorio tiempo completo",
        palabras_clave=["profesional SST", "responsable SG-SST", "tiempo completo", "outsourcing SST"],
        angulo_narrativo="pregunta_practica",
    ),
    TemaSSTInfo(
        categoria="PREGUNTAS_FRECUENTES",
        titulo_base="¿Cuánto cuesta realmente implementar el SG-SST en una PYME colombiana?",
        descripcion_brief="Desglose honesto de costos vs. el costo de no tenerlo — comparación con multas y demandas reales",
        palabras_clave=["costo SG-SST", "inversión SST", "presupuesto PYME", "retorno de inversión"],
        angulo_narrativo="comparacion_costos",
    ),
    TemaSSTInfo(
        categoria="PREGUNTAS_FRECUENTES",
        titulo_base="¿El SG-SST aplica si tengo trabajadores por prestación de servicios y no de nómina?",
        descripcion_brief="Contratistas, independientes y la zona gris legal que muchas empresas colombianas malinterpretan",
        palabras_clave=["contratistas SST", "prestación de servicios", "afiliación ARL independientes"],
        angulo_narrativo="aclaracion_legal",
    ),
    TemaSSTInfo(
        categoria="PREGUNTAS_FRECUENTES",
        titulo_base="¿Qué pasa con el SG-SST si mi empresa trabaja 100% remoto o en modalidad híbrida?",
        descripcion_brief="Teletrabajo en Colombia: la Ley 2088 y las obligaciones de SST que igual aplican fuera de la oficina",
        palabras_clave=["teletrabajo", "trabajo remoto", "Ley 2088", "SST en casa"],
        angulo_narrativo="aclaracion_legal",
    ),
    TemaSSTInfo(
        categoria="PREGUNTAS_FRECUENTES",
        titulo_base="¿Cada cuánto se debe actualizar la matriz de peligros de mi empresa?",
        descripcion_brief="No es un documento único: cuándo la ley exige revisarla y qué eventos obligan a actualizarla antes",
        palabras_clave=["actualización matriz de peligros", "GTC-45", "revisión periódica", "cambios en el proceso"],
        angulo_narrativo="pregunta_practica",
    ),
    TemaSSTInfo(
        categoria="PREGUNTAS_FRECUENTES",
        titulo_base="¿Puede el COPASST reemplazar al profesional de SST de mi empresa?",
        descripcion_brief="Roles distintos que se confunden seguido: qué hace el comité y qué exige la ley que haga un profesional",
        palabras_clave=["COPASST", "comité paritario", "vigía SST", "roles SG-SST"],
        angulo_narrativo="aclaracion_legal",
    ),

    # ── SERVICIOS COMPLEMENTARIOS (10 temas) ─────────────────────────────────
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Mediciones ambientales ocupacionales: la evidencia técnica que su matriz de peligros necesita",
        descripcion_brief="Luxometría, sonometría, dosimetría y material particulado: cómo estas mediciones respaldan legalmente su SG-SST",
        palabras_clave=["mediciones ambientales", "luxometría", "sonometría", "dosimetría", "higiene ocupacional"],
        angulo_narrativo="requisito_tecnico",
    ),
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Estrés térmico en el trabajo: el riesgo que ninguna empresa mide hasta que alguien se desmaya",
        descripcion_brief="Exposición a calor o frío extremo en planta y campo, cómo medirla y los límites que exige la normativa",
        palabras_clave=["estrés térmico", "medición higiénica", "riesgo físico", "exposición a calor"],
        angulo_narrativo="riesgo_subestimado",
    ),
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Investigación de accidentes de trabajo: por qué hacerla mal cuesta más que el accidente mismo",
        descripcion_brief="Metodología del árbol de causas y por qué el Ministerio del Trabajo exige un informe técnico, no una versión informal",
        palabras_clave=["investigación de accidentes", "árbol de causas", "informe accidente laboral", "FURAT"],
        angulo_narrativo="metodologia_fundamental",
    ),
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Profesiograma ocupacional: el documento que conecta cada cargo con sus exámenes médicos exactos",
        descripcion_brief="Por qué un examen médico genérico no cumple la ley y cómo el profesiograma define qué evaluar por cargo",
        palabras_clave=["profesiograma", "exámenes médicos ocupacionales", "perfil de cargo", "medicina laboral"],
        angulo_narrativo="requisito_tecnico",
    ),
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Planos de emergencia y señalización: el documento que su empresa necesita antes de cualquier inspección",
        descripcion_brief="Rutas de evacuación, puntos de encuentro y señalización normativa: los errores más comunes en las PYMEs",
        palabras_clave=["planos de emergencia", "señalización industrial", "rutas de evacuación", "punto de encuentro"],
        angulo_narrativo="requisito_tecnico",
    ),
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Red contra incendios: lo que la ley exige más allá de tener un extintor colgado en la pared",
        descripcion_brief="Diseño, mantenimiento e inspección de sistemas contra incendios según el riesgo real de su instalación",
        palabras_clave=["red contra incendios", "extintores", "sistema contra incendios", "mantenimiento preventivo"],
        angulo_narrativo="requisito_tecnico",
    ),
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Inspecciones de puesto de trabajo: la rutina de 15 minutos que previene la mayoría de accidentes",
        descripcion_brief="Checklist práctico de inspección y por qué las empresas que las hacen mensualmente reducen su accidentalidad",
        palabras_clave=["inspecciones de puesto de trabajo", "checklist SST", "prevención de accidentes", "rutina de seguridad"],
        angulo_narrativo="habito_preventivo",
    ),
    TemaSSTInfo(
        categoria="SERVICIOS_COMPLEMENTARIOS",
        titulo_base="Bienestar laboral: la estrategia que reduce el ausentismo más que cualquier sanción lo previene",
        descripcion_brief="Programas de bienestar, pausas activas y por qué invertir en el bienestar del equipo baja los indicadores de accidentalidad",
        palabras_clave=["bienestar laboral", "pausas activas", "calidad de vida laboral", "clima organizacional"],
        angulo_narrativo="valor_agregado",
    ),
]


def obtener_tema_del_dia(dia: date | None = None) -> TemaSSTInfo:
    """Selecciona el tema del día en orden secuencial desde el primero del
    catálogo, avanzando un tema por día calendario (llamar varias veces el
    mismo día devuelve siempre el mismo tema). Al llegar al final, reinicia
    desde el primero."""
    target = dia or date.today()
    try:
        estado = json.loads(_ESTADO_PATH.read_text(encoding="utf-8"))
    except Exception:
        estado = {"fecha": None, "indice": 0}

    if estado.get("fecha") != target.isoformat():
        if estado.get("fecha") is not None:
            estado["indice"] = (estado.get("indice", 0) + 1) % len(CATALOGO_TEMAS)
        estado["fecha"] = target.isoformat()
        _ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ESTADO_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")

    return CATALOGO_TEMAS[estado["indice"] % len(CATALOGO_TEMAS)]


def obtener_tema_por_categoria(categoria: str) -> list[TemaSSTInfo]:
    return [t for t in CATALOGO_TEMAS if t.categoria == categoria]
