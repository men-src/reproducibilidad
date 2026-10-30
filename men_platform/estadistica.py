"""Lectura estadística de las series mensuales (Fase 4, D-82): intervalos de Wilson para la precisión de una proporción y
cartas de comportamiento del proceso (XmR, individuos y rangos móviles) para distinguir una señal del ruido.

Por qué XmR y no límites binomiales: la oportunidad mensual de PQRSDF varía diecisiete veces más de lo que predice la
binomial con sus 15 mil radicados (desviación real 4,75 puntos frente a 0,28), así que un intervalo binomial marcaría
casi todo como señal. Los límites de individuos (media ± 2,66 veces el rango móvil medio, Wheeler) miden la variación
real del proceso. El intervalo de Wilson queda para decir cuán precisa es la cifra de un mes o de un grupo pequeño.

La misma lógica está en apps/web/src/lib/estadistica.ts; los casos dorados de tests/fixtures/casos_dorados/estadistica.json
los corren las dos implementaciones."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Z_95 = 1.959963984540054
CONSTANTE_XMR = 2.66  # 3 / d2 con n = 2 (d2 = 1,128)
MESES_BASE = 12
MINIMO_BASE = 6


def wilson(exitos: int, total: int, z: float = Z_95) -> tuple[float, float] | None:
    """Intervalo de Wilson al 95 % para una proporción; None sin observaciones."""
    if total <= 0:
        return None
    p = exitos / total
    denominador = 1 + z * z / total
    centro = (p + z * z / (2 * total)) / denominador
    medio = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominador
    inferior = 0.0 if exitos == 0 else max(0.0, centro - medio)
    superior = 1.0 if exitos == total else min(1.0, centro + medio)
    return (inferior, superior)


def semiancho_wilson(exitos: int, total: int, z: float = Z_95) -> float | None:
    """La mitad del ancho del intervalo de Wilson: la precisión de la cifra, en la misma unidad."""
    intervalo = wilson(exitos, total, z)
    return None if intervalo is None else (intervalo[1] - intervalo[0]) / 2


@dataclass(frozen=True)
class Limites:
    """La carta de individuos de una serie base: centro, límites y de cuántos puntos salió."""

    centro: float
    inferior: float
    superior: float
    puntos: int
    rango_movil_medio: float

    def contiene(self, valor: float) -> bool:
        return self.inferior <= valor <= self.superior


def limites_xmr(base: Sequence[float | None], minimo: int = MINIMO_BASE) -> Limites | None:
    """Límites de individuos de la serie base (sin el punto que se juzga): media ± 2,66 por el rango móvil medio.
    None con menos de `minimo` puntos válidos."""
    valores = [v for v in base if v is not None]
    if len(valores) < minimo:
        return None
    media = sum(valores) / len(valores)
    rangos = [abs(a - b) for a, b in zip(valores[1:], valores, strict=False)]
    rango_medio = sum(rangos) / len(rangos)
    return Limites(
        media, media - CONSTANTE_XMR * rango_medio, media + CONSTANTE_XMR * rango_medio, len(valores), rango_medio
    )


def señal(valor: float | None, limites: Limites | None) -> str | None:
    """«alta» si el valor supera el límite superior, «baja» si queda bajo el inferior, None si está dentro o no se sabe."""
    if valor is None or limites is None:
        return None
    if valor > limites.superior:
        return "alta"
    if valor < limites.inferior:
        return "baja"
    return None


def racha(serie: Sequence[float | None], centro: float, largo: int = 8) -> str | None:
    """Una racha de `largo` puntos seguidos al final de la serie, todos por encima («alta») o por debajo («baja») del
    centro: la segunda regla de Wheeler. None si no la hay."""
    ultimos = [v for v in serie if v is not None][-largo:]
    if len(ultimos) < largo:
        return None
    if all(v > centro for v in ultimos):
        return "alta"
    if all(v < centro for v in ultimos):
        return "baja"
    return None


def juzgar(serie: Sequence[float | None], meses_base: int = MESES_BASE) -> tuple[Limites | None, str | None]:
    """Juzga el último punto de la serie contra los `meses_base` anteriores: (límites, señal)."""
    valores = list(serie)
    if not valores:
        return None, None
    actual = valores[-1]
    base = [v for v in valores[:-1] if v is not None][-meses_base:]
    limites = limites_xmr(base)
    return limites, señal(actual, limites)
