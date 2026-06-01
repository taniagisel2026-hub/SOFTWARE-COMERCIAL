"""
Catálogo de temas SST con rotación diaria automática.
28 temas cubren un ciclo mensual completo sin repetición.
"""
from datetime import date
from typing import NamedTuple


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
]


def obtener_tema_del_dia(dia: date | None = None) -> TemaSSTInfo:
    """Selecciona el tema del día usando rotación circular por día del año."""
    target = dia or date.today()
    indice = (target.timetuple().tm_yday - 1) % len(CATALOGO_TEMAS)
    return CATALOGO_TEMAS[indice]


def obtener_tema_por_categoria(categoria: str) -> list[TemaSSTInfo]:
    return [t for t in CATALOGO_TEMAS if t.categoria == categoria]
