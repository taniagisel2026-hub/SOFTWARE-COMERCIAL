from dataclasses import dataclass
from enum import Enum
from typing import Dict


class ZonaViaticos(str, Enum):
    MISMA_CIUDAD = "MISMA_CIUDAD"
    MISMO_DEPARTAMENTO = "MISMO_DEPARTAMENTO"
    DIFERENTE_DEPARTAMENTO = "DIFERENTE_DEPARTAMENTO"
    ZONA_REMOTA = "ZONA_REMOTA"


@dataclass(frozen=True)
class Ciudad:
    nombre: str
    departamento: str
    es_capital: bool = False
    zona_remota: bool = False


# Normalización: claves en minúsculas sin tilde para lookup tolerante a errores de escritura.
CIUDADES: Dict[str, Ciudad] = {
    # ── Costa Caribe ──────────────────────────────────────────────────────
    "barranquilla": Ciudad("Barranquilla", "Atlántico", es_capital=True),
    "soledad": Ciudad("Soledad", "Atlántico"),
    "malambo": Ciudad("Malambo", "Atlántico"),
    "cartagena": Ciudad("Cartagena", "Bolívar", es_capital=True),
    "magangué": Ciudad("Magangué", "Bolívar"),
    "magangue": Ciudad("Magangué", "Bolívar"),
    "santa marta": Ciudad("Santa Marta", "Magdalena", es_capital=True),
    "ciénaga": Ciudad("Ciénaga", "Magdalena"),
    "cienaga": Ciudad("Ciénaga", "Magdalena"),
    "valledupar": Ciudad("Valledupar", "Cesar", es_capital=True),
    "aguachica": Ciudad("Aguachica", "Cesar"),
    "montería": Ciudad("Montería", "Córdoba", es_capital=True),
    "monteria": Ciudad("Montería", "Córdoba", es_capital=True),
    "lorica": Ciudad("Lorica", "Córdoba"),
    "cereté": Ciudad("Cereté", "Córdoba"),
    "cerete": Ciudad("Cereté", "Córdoba"),
    "sincelejo": Ciudad("Sincelejo", "Sucre", es_capital=True),
    "corozal": Ciudad("Corozal", "Sucre"),
    "riohacha": Ciudad("Riohacha", "La Guajira", es_capital=True),
    "maicao": Ciudad("Maicao", "La Guajira"),
    # ── Región Andina ─────────────────────────────────────────────────────
    "bogotá d.c.": Ciudad("Bogotá D.C.", "Cundinamarca", es_capital=True),
    "bogota d.c.": Ciudad("Bogotá D.C.", "Cundinamarca", es_capital=True),
    "bogotá": Ciudad("Bogotá D.C.", "Cundinamarca", es_capital=True),
    "bogota": Ciudad("Bogotá D.C.", "Cundinamarca", es_capital=True),
    "soacha": Ciudad("Soacha", "Cundinamarca"),
    "zipaquirá": Ciudad("Zipaquirá", "Cundinamarca"),
    "zipaquira": Ciudad("Zipaquirá", "Cundinamarca"),
    "facatativá": Ciudad("Facatativá", "Cundinamarca"),
    "facatativa": Ciudad("Facatativá", "Cundinamarca"),
    "chía": Ciudad("Chía", "Cundinamarca"),
    "chia": Ciudad("Chía", "Cundinamarca"),
    "mosquera": Ciudad("Mosquera", "Cundinamarca"),
    "girardot": Ciudad("Girardot", "Cundinamarca"),
    "fusagasugá": Ciudad("Fusagasugá", "Cundinamarca"),
    "fusagasuga": Ciudad("Fusagasugá", "Cundinamarca"),
    "medellín": Ciudad("Medellín", "Antioquia", es_capital=True),
    "medellin": Ciudad("Medellín", "Antioquia", es_capital=True),
    "bello": Ciudad("Bello", "Antioquia"),
    "itagüí": Ciudad("Itagüí", "Antioquia"),
    "itagui": Ciudad("Itagüí", "Antioquia"),
    "envigado": Ciudad("Envigado", "Antioquia"),
    "sabaneta": Ciudad("Sabaneta", "Antioquia"),
    "rionegro": Ciudad("Rionegro", "Antioquia"),
    "apartadó": Ciudad("Apartadó", "Antioquia"),
    "apartado": Ciudad("Apartadó", "Antioquia"),
    "turbo": Ciudad("Turbo", "Antioquia"),
    "caucasia": Ciudad("Caucasia", "Antioquia"),
    "cali": Ciudad("Cali", "Valle del Cauca", es_capital=True),
    "palmira": Ciudad("Palmira", "Valle del Cauca"),
    "buenaventura": Ciudad("Buenaventura", "Valle del Cauca"),
    "tulúa": Ciudad("Tulúa", "Valle del Cauca"),
    "tulua": Ciudad("Tulúa", "Valle del Cauca"),
    "buga": Ciudad("Buga", "Valle del Cauca"),
    "bucaramanga": Ciudad("Bucaramanga", "Santander", es_capital=True),
    "floridablanca": Ciudad("Floridablanca", "Santander"),
    "girón": Ciudad("Girón", "Santander"),
    "giron": Ciudad("Girón", "Santander"),
    "piedecuesta": Ciudad("Piedecuesta", "Santander"),
    "barrancabermeja": Ciudad("Barrancabermeja", "Santander"),
    "socorro": Ciudad("Socorro", "Santander"),
    "pereira": Ciudad("Pereira", "Risaralda", es_capital=True),
    "dosquebradas": Ciudad("Dosquebradas", "Risaralda"),
    "la virginia": Ciudad("La Virginia", "Risaralda"),
    "manizales": Ciudad("Manizales", "Caldas", es_capital=True),
    "armenia": Ciudad("Armenia", "Quindío", es_capital=True),
    "ibagué": Ciudad("Ibagué", "Tolima", es_capital=True),
    "ibague": Ciudad("Ibagué", "Tolima", es_capital=True),
    "espinal": Ciudad("Espinal", "Tolima"),
    "neiva": Ciudad("Neiva", "Huila", es_capital=True),
    "pitalito": Ciudad("Pitalito", "Huila"),
    "popayán": Ciudad("Popayán", "Cauca", es_capital=True),
    "popayan": Ciudad("Popayán", "Cauca", es_capital=True),
    "pasto": Ciudad("Pasto", "Nariño", es_capital=True),
    "tumaco": Ciudad("Tumaco", "Nariño"),
    "ipiales": Ciudad("Ipiales", "Nariño"),
    "tunja": Ciudad("Tunja", "Boyacá", es_capital=True),
    "duitama": Ciudad("Duitama", "Boyacá"),
    "sogamoso": Ciudad("Sogamoso", "Boyacá"),
    "chiquinquirá": Ciudad("Chiquinquirá", "Boyacá"),
    "chiquinquira": Ciudad("Chiquinquirá", "Boyacá"),
    "cúcuta": Ciudad("Cúcuta", "Norte de Santander", es_capital=True),
    "cucuta": Ciudad("Cúcuta", "Norte de Santander", es_capital=True),
    "ocaña": Ciudad("Ocaña", "Norte de Santander"),
    "ocana": Ciudad("Ocaña", "Norte de Santander"),
    # ── Llanos Orientales ─────────────────────────────────────────────────
    "villavicencio": Ciudad("Villavicencio", "Meta", es_capital=True),
    "yopal": Ciudad("Yopal", "Casanare", es_capital=True),
    # ── Amazonía y zonas remotas ──────────────────────────────────────────
    "florencia": Ciudad("Florencia", "Caquetá", es_capital=True),
    "mocoa": Ciudad("Mocoa", "Putumayo", es_capital=True, zona_remota=True),
    "leticia": Ciudad("Leticia", "Amazonas", es_capital=True, zona_remota=True),
    "mitú": Ciudad("Mitú", "Vaupés", es_capital=True, zona_remota=True),
    "mitu": Ciudad("Mitú", "Vaupés", es_capital=True, zona_remota=True),
    "puerto inírida": Ciudad("Puerto Inírida", "Guainía", es_capital=True, zona_remota=True),
    "puerto inirida": Ciudad("Puerto Inírida", "Guainía", es_capital=True, zona_remota=True),
    "san josé del guaviare": Ciudad("San José del Guaviare", "Guaviare", es_capital=True, zona_remota=True),
    "san jose del guaviare": Ciudad("San José del Guaviare", "Guaviare", es_capital=True, zona_remota=True),
    "puerto carreño": Ciudad("Puerto Carreño", "Vichada", es_capital=True, zona_remota=True),
    "puerto carreno": Ciudad("Puerto Carreño", "Vichada", es_capital=True, zona_remota=True),
    "quibdó": Ciudad("Quibdó", "Chocó", es_capital=True, zona_remota=True),
    "quibdo": Ciudad("Quibdó", "Chocó", es_capital=True, zona_remota=True),
}
