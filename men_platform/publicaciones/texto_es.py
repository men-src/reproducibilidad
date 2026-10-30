"""Formato de cifras, fechas y nombres en español de Colombia para las publicaciones: miles con punto, decimales con
coma, porcentajes con espacio antes del signo («81,77 %»), meses en minúscula y nombres propios con tildes y siglas,
igual que el informe web (apps/web/src/lib/formato.ts)."""

from __future__ import annotations

import re
from datetime import date

from men_platform.publicaciones.tildes_siglas import SIGLAS, TILDES

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# palabras que en un nombre propio van en minúscula salvo al comienzo
_MENORES = {
    "a",
    "al",
    "ante",
    "con",
    "de",
    "del",
    "e",
    "el",
    "en",
    "la",
    "las",
    "los",
    "o",
    "para",
    "por",
    "sin",
    "u",
    "y",
}
# etiquetas del catálogo que no son nombres propios: solo mayúscula inicial
_ETIQUETAS = {
    "directamente en la dependencia",
    "sin dependencia",
    "sin grupo",
    "sin viceministerio",
    "sin informacion",
    "sin homologar",
    "sin eje tematico",
}


def entero(valor: float | int | None) -> str:
    """150994 → «150.994»; None → «–»."""
    if valor is None:
        return "–"
    return f"{int(round(valor)):,}".replace(",", ".")


def decimal(valor: float | None, decimales: int = 1) -> str:
    """11.53 → «11,5»."""
    if valor is None:
        return "–"
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")


def porcentaje(valor: float | None, decimales: int = 2) -> str:
    """0.8177 → «81,77 %»."""
    if valor is None:
        return "–"
    return f"{decimal(valor * 100, decimales)} %"


def puntos(valor: float | None, decimales: int = 2) -> str:
    """Diferencia entre dos porcentajes, en puntos porcentuales con signo: 0.0123 → «+1,23 pp»."""
    if valor is None:
        return "–"
    signo = "+" if valor > 0 else ("−" if valor < 0 else "")
    return f"{signo}{decimal(abs(valor) * 100, decimales)} pp"


def variacion(actual: float | None, anterior: float | None, decimales: int = 2) -> str:
    """Variación relativa con signo: (150, 100) → «+50,00 %»."""
    if actual is None or anterior in (None, 0):
        return "–"
    delta = (actual - anterior) / anterior  # type: ignore[operator]
    signo = "+" if delta > 0 else ("−" if delta < 0 else "")
    return f"{signo}{decimal(abs(delta) * 100, decimales)} %"


def variacion_relativa(actual: float | None, anterior: float | None) -> float | None:
    if actual is None or anterior in (None, 0):
        return None
    return (actual - anterior) / anterior  # type: ignore[operator]


def nombre_mes(periodo: str) -> str:
    """'2026-09-01' → «septiembre»."""
    return MESES[int(periodo[5:7]) - 1]


def mes_y_anio(periodo: str) -> str:
    """'2026-09-01' → «septiembre de 2026»."""
    return f"{nombre_mes(periodo)} de {periodo[:4]}"


def mes_y_anio_siguiente(periodo: str) -> str:
    """«octubre de 2026» para el periodo 2026-09-01: el mes que sigue al del informe."""
    anio, mes = int(periodo[:4]), int(periodo[5:7])
    return mes_y_anio(f"{anio + 1}-01-01" if mes == 12 else f"{anio}-{mes + 1:02d}-01")


def tramo_del_anio(periodo: str, mayuscula: bool = False) -> str:
    """«enero a septiembre» para el mes del informe; en enero, solo «enero»."""
    mes = nombre_mes(periodo)
    texto = mes if periodo[5:7] == "01" else f"enero a {mes}"
    return texto[0].upper() + texto[1:] if mayuscula else texto


def entre_tramo(periodo: str) -> str:
    """«Entre enero y septiembre» o, en enero, «En enero»."""
    return f"En {nombre_mes(periodo)}" if periodo[5:7] == "01" else f"Entre enero y {nombre_mes(periodo)}"


def mes_corto(periodo: str) -> str:
    """'2026-09-01' → «sep 2026»."""
    return f"{MESES_CORTOS[int(periodo[5:7]) - 1]} {periodo[:4]}"


def mes_corto_2(periodo: str) -> str:
    """'2026-09-01' → «sep 26», para ejes con muchos meses."""
    return f"{MESES_CORTOS[int(periodo[5:7]) - 1]} {periodo[2:4]}"


def puntos_sin_signo(valor: float | None, decimales: int = 2) -> str:
    """Diferencia en puntos porcentuales sin signo, para después de «subió» o «bajó»: 0.0468 → «4,68 pp»."""
    if valor is None:
        return "–"
    return f"{decimal(abs(valor) * 100, decimales)} pp"


_NUMEROS = ["cero", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"]


def numero_en_palabras(n: int, femenino: bool = True) -> str:
    """Hasta diez, en palabras; para empezar una frase sin cifra. 4 → «cuatro»; 1 → «una» (o «un»)."""
    if 0 <= n <= 10:
        palabra = _NUMEROS[n]
        return palabra if femenino or n != 1 else "un"
    return entero(n)


_ARTICULOS = {
    "direccion": "la",
    "subdireccion": "la",
    "oficina": "la",
    "secretaria": "la",
    "unidad": "la",
    "subcomision": "la",
    "comision": "la",
    "despacho": "el",
    "grupo": "el",
    "programa": "el",
    "viceministerio": "el",
    "ministerio": "el",
    "entes": "los",
    "asesores": "los",
    "pueblos": "los",
}


def con_articulo(nombre_catalogo: str) -> str:
    """«subdireccion de acceso» → «la Subdirección de Acceso», para nombrar una dependencia dentro de una frase."""
    primera = nombre_catalogo.split(" ")[0] if nombre_catalogo else ""
    articulo = _ARTICULOS.get(primera, "la")
    return f"{articulo} {nombre_propio(nombre_catalogo)}"


def fecha_larga(valor: str | date) -> str:
    """'2026-09-30' → «30 de septiembre de 2026»."""
    if isinstance(valor, str):
        valor = date.fromisoformat(valor[:10])
    return f"{valor.day} de {MESES[valor.month - 1]} de {valor.year}"


def con_tildes(texto: str) -> str:
    """Restituye tildes y siglas a un texto del catálogo, sin cambiar mayúsculas."""
    return re.sub(r"[a-zñ]+", lambda m: SIGLAS.get(m.group(0), TILDES.get(m.group(0), m.group(0))), texto)


def capitalizar(texto: str | None) -> str:
    """Primera letra en mayúscula, con tildes y siglas: para tipos, canales y estados."""
    if not texto:
        return ""
    arreglado = con_tildes(texto)
    return arreglado[0].upper() + arreglado[1:]


def nombre_propio(texto: str | None) -> str:
    """Cada palabra en mayúscula inicial salvo artículos y preposiciones, con tildes y siglas."""
    if not texto:
        return ""
    if texto in _ETIQUETAS:
        return capitalizar(texto)
    palabras = con_tildes(texto).split(" ")
    salida = []
    for i, palabra in enumerate(palabras):
        if not palabra or re.fullmatch(r"[A-Z0-9][A-Z0-9-]*", palabra) or (i > 0 and palabra in _MENORES):
            salida.append(palabra)
        else:
            salida.append(palabra[0].upper() + palabra[1:])
    return " ".join(salida)


def mayuscula_inicial(texto: str) -> str:
    return texto[0].upper() + texto[1:] if texto else texto


def lista_en_prosa(elementos: list[str]) -> str:
    """['a', 'b', 'c'] → «a, b y c»."""
    if not elementos:
        return ""
    if len(elementos) == 1:
        return elementos[0]
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]
