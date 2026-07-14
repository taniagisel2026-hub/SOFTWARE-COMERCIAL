"""
Fuente única de verdad para la cobertura geográfica y sectorial del scraper.

Tanto el panel Streamlit (src/frontend/pages/scraper.py) como el scheduler
autónomo (src/scheduler/auto_scheduler.py) deben importar estas constantes
desde aquí — nunca duplicarlas — para que la extracción manual y la
automática busquen siempre en los mismos municipios y nunca queden
desincronizadas.
"""

CIUDADES: list[str] = [
    # Principales
    "Bogotá D.C.", "Medellín", "Cali", "Barranquilla", "Bucaramanga",
    "Cartagena", "Soacha", "Tunja", "Ibagué", "Santa Marta",
    # Cundinamarca / Clúster Bogotá
    "Chía", "Cota", "Facatativá", "Fusagasugá", "Zipaquirá",
    "Villeta", "Girardot", "Mosquera", "La Vega", "Cajicá",
    "Sopó", "La Calera", "Guaduas", "Tocancipá",
    "Madrid", "Sibaté", "Funza", "Tausa", "Ricaurte",
    "Cogua", "Gachancipá", "Nemocón", "Tabio", "Tenjo",
    "Bojacá", "El Rosal", "Subachoque", "Zipacón",
    "Agua de Dios", "Nilo", "Tocaima",
    "Silvania", "Arbeláez", "Granada",
    # Otras ciudades de cobertura
    "Cúcuta", "Pereira", "Manizales", "Valledupar", "Floridablanca",
    "Barrancabermeja", "Lebrija", "Melgar", "Flandes",
]

REGIONES: dict[str, list[str]] = {
    "Bogotá + Cundinamarca": [
        "Bogotá D.C.", "Soacha", "Chía", "Cota", "Facatativá", "Fusagasugá",
        "Zipaquirá", "Villeta", "Girardot", "Mosquera", "La Vega", "Cajicá",
        "Sopó", "La Calera", "Guaduas", "Tocancipá", "Madrid", "Sibaté",
        "Funza", "Tausa", "Ricaurte", "Cogua", "Gachancipá", "Nemocón",
        "Tabio", "Tenjo", "Bojacá", "El Rosal", "Subachoque", "Zipacón",
        "Agua de Dios", "Nilo", "Tocaima", "Silvania", "Arbeláez", "Granada",
    ],
    "Antioquia": ["Medellín"],
    "Valle del Cauca": ["Cali"],
    "Costa Caribe": ["Barranquilla", "Cartagena", "Valledupar", "Santa Marta"],
    "Santander": ["Bucaramanga", "Floridablanca", "Lebrija", "Barrancabermeja"],
    "Eje Cafetero": ["Pereira", "Manizales"],
    "Boyacá / Tolima": ["Tunja", "Ibagué", "Melgar", "Flandes"],
    "Norte de Santander": ["Cúcuta"],
    "Todo el país": CIUDADES,
}

SECTORES: list[str] = [
    "Construcción", "Manufactura / Industria", "Transporte y Logística",
    "Comercio y Retail", "Servicios Empresariales", "Salud y Clínicas",
    "Minería y Energía", "Tecnología y Software", "Alimentos y Bebidas",
    "Seguridad Privada", "Hotelería y Turismo", "Petróleo y Gas",
    "Ingeniería y Consultoría", "Farmacéutico y Químico", "Telecomunicaciones",
    "Entretenimiento y Eventos",
]
