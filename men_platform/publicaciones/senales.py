"""Señales estadísticas y umbrales con fuente en la redacción de los informes en PDF (Fase 4, D-82).

La redacción compara el mes con el anterior y con su historial. Desde la Fase 4 esa comparación se juzga con la carta
de individuos de `men_platform.estadistica`: el mes solo es una señal cuando se sale de la variación habitual de los
doce meses anteriores; si no, la diferencia se nombra como lo que es, variación habitual. Los umbrales de la redacción
(«oportunidad baja», «en curso alto») salen de `ref.parametro`, que la exportación publica en dimensiones.json; sin el
parámetro, o con un parámetro que aún no es un número («sin definir»), se usa el valor interno del módulo que redacta."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from men_platform.estadistica import juzgar

PORCENTAJE = (0.0, 1.0)  # una proporción no se muestra por debajo de 0 % ni por encima de 100 %
CANTIDAD = (0.0, float("inf"))  # una cantidad no se muestra negativa


def parametro_numerico(parametros: Mapping[str, str] | None, clave: str, defecto: float) -> float:
    """El valor numérico de un parámetro publicado; el interno si no está o no es un número."""
    valor = (parametros or {}).get(clave)
    if valor is None:
        return defecto
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return defecto


def serie_hasta[T](
    serie: Sequence[tuple[str, T]], periodo: str, medida: Callable[[T], float | None]
) -> list[float | None]:
    """Los valores de la medida hasta el periodo que se juzga, inclusive; vacía si el periodo no está en la serie (un
    canal o un tipo sin datos en el mes del informe no se juzga)."""
    valores: list[float | None] = []
    for p, dato in serie:
        valores.append(medida(dato))
        if p == periodo:
            return valores
    return []


def frase_senal(
    serie: Sequence[float | None], formato: Callable[[float], str], tope: tuple[float, float] | None = None
) -> str:
    """La coda de una comparación: «, por fuera de lo habitual en los doce meses anteriores (x a y)» o «, dentro de lo
    habitual en los doce meses anteriores (x a y)». Vacía cuando no hay base suficiente para los límites. `tope` acota
    los límites que se muestran, no los que juzgan."""
    limites, senal = juzgar(serie)
    if limites is None:
        return ""

    def acotar(v: float) -> float:
        return min(tope[1], max(tope[0], v)) if tope else v

    rango = f"{formato(acotar(limites.inferior))} a {formato(acotar(limites.superior))}"
    donde = "por fuera de" if senal else "dentro de"
    return f", {donde} lo habitual en los doce meses anteriores ({rango})"
