"""Los gráficos del Informe de Trámites, que replican las vistas del informe interactivo: barras por mes con la línea
del promedio mensual, treemap de participación, Pareto de los tipos y cada tipo frente al año anterior. Las barras
apiladas por tipo, la mezcla al 100 % y las barras por tipo se toman de graficos_canales; las vistas de dos años,
variación y media móvil, de graficos_tablero. Misma identidad: Inter, la paleta de la plataforma, sin guías."""

from __future__ import annotations

import matplotlib.pyplot as plt

from men_platform.publicaciones.datos_tramites import Tramite
from men_platform.publicaciones.graficos_pqrsdf import (
    AMARILLO,
    AZUL,
    AZUL_CLARO,
    FILETE,
    GRIS,
    GRIS_TENUE,
    NOCHE,
    ROJO,
    TINTA,
    _ejes_sin_y,
    _miles,
    _png,
    preparar,
)
from men_platform.publicaciones.texto_es import decimal, entero, porcentaje

# Un color por tipo de trámite, el mismo que usa el informe interactivo (COLORES_TRAMITE en graficos-tramites.tsx).
PALETA_TRAMITES: dict[str, str] = {
    "legalizaciones": AZUL,
    "pqrs": ROJO,
    "numeracion resoluciones": AMARILLO,
    "notificacion": AZUL_CLARO,
    "atencion personalizada": NOCHE,
    "certificados de existencia": "#840c20",
    "certificados de programa": "#0a2a66",
    "certificados de idoneidad": "#f0485c",
    "convalidaciones de basica": GRIS_TENUE,
    "citas virtuales": "#600816",
}
RESERVA = [AMARILLO, AZUL_CLARO, NOCHE, "#840c20", "#0a2a66", "#f0485c", GRIS_TENUE, "#600816"]
CLAROS = {AZUL_CLARO, AMARILLO, GRIS_TENUE, "#f0485c"}  # sobre estos el texto va en tinta


def color_de(tramite: Tramite, posicion: int = 0) -> str:
    return PALETA_TRAMITES.get(tramite.fuente, RESERVA[posicion % len(RESERVA)])


def barras_con_referencia(
    etiquetas: list[str],
    valores: list[int],
    color: str,
    referencia: tuple[str, float] | None,
    resaltar: int | None = None,
) -> bytes:
    """Barras por mes con el valor encima y, si se pide, la línea punteada de una referencia (el promedio mensual),
    nombrada con su valor en la leyenda para que no tape las cifras de las barras."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.3))
    x = list(range(len(etiquetas)))
    ax.bar(x, valores, color=color, width=0.62, zorder=3)
    if len(etiquetas) <= 13:
        for xi, v in enumerate(valores):
            ax.annotate(
                entero(v),
                (xi, v),
                textcoords="offset points",
                xytext=(0, 4),
                ha="center",
                fontsize=7,
                color=TINTA,
                fontweight="bold" if xi == resaltar else "normal",
            )
    tope = max(valores) if valores else 1
    if referencia is not None:
        nombre, valor = referencia
        ax.axhline(valor, color=NOCHE, linestyle="--", linewidth=1.4, zorder=4, label=f"{nombre}: {entero(valor)}")
        ax.legend(loc="upper left", bbox_to_anchor=(0, 1.1))
        tope = max(tope, valor)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    if resaltar is not None and 0 <= resaltar < len(etiquetas):
        ax.get_xticklabels()[resaltar].set_fontweight("bold")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, tope * 1.22)
    _ejes_sin_y(ax)
    return _png(fig)


def _squarify(valores: list[float], x: float, y: float, w: float, h: float) -> list[tuple[float, float, float, float]]:
    """El algoritmo squarified (Bruls, Huizing y van Wijk): rectángulos lo más cuadrados posible, de mayor a menor."""
    rectangulos: list[tuple[float, float, float, float]] = []

    def peor(fila: list[float], lado: float) -> float:
        s = sum(fila)
        return max(lado * lado * max(fila) / (s * s), s * s / (lado * lado * min(fila)))

    def colocar(fila: list[float], x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
        s = sum(fila)
        if w >= h:
            ancho = s / h if h else 0
            yy = y
            for v in fila:
                alto = v / ancho if ancho else 0
                rectangulos.append((x, yy, ancho, alto))
                yy += alto
            return x + ancho, y, w - ancho, h
        alto = s / w if w else 0
        xx = x
        for v in fila:
            ancho = v / alto if alto else 0
            rectangulos.append((xx, y, ancho, alto))
            xx += ancho
        return x, y + alto, w, h - alto

    fila: list[float] = []
    pendientes = list(valores)
    while pendientes:
        lado = min(w, h)
        v = pendientes[0]
        if not fila or peor([*fila, v], lado) <= peor(fila, lado):
            fila.append(v)
            pendientes = pendientes[1:]
        else:
            x, y, w, h = colocar(fila, x, y, w, h)
            fila = []
    if fila:
        colocar(fila, x, y, w, h)
    return rectangulos


def treemap(items: list[tuple[str, int, str]]) -> bytes:
    """Cada tipo ocupa un área proporcional a su total (nombre, valor, color); dentro van el nombre, el total y su
    participación cuando caben."""
    preparar()
    ancho, alto = 8.0, 3.4
    fig, ax = plt.subplots(figsize=(ancho, alto))
    items = sorted([i for i in items if i[1] > 0], key=lambda i: -i[1])
    total = sum(v for _, v, _ in items) or 1
    escala = ancho * alto / total
    rect = _squarify([v * escala for _, v, _ in items], 0, 0, ancho, alto)
    for (nombre, valor, color), (x, y, w, h) in zip(items, rect, strict=True):
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="white", linewidth=2))
        texto = TINTA if color in CLAROS else "white"
        area = w * h
        if area >= 1.6:
            ax.text(
                x + w / 2,
                y + h / 2 + 0.16,
                nombre,
                ha="center",
                va="center",
                fontsize=8,
                color=texto,
                fontweight="bold",
            )
            ax.text(
                x + w / 2,
                y + h / 2 - 0.16,
                f"{entero(valor)} · {porcentaje(valor / total, 1)}",
                ha="center",
                va="center",
                fontsize=7,
                color=texto,
            )
        elif area >= 0.45:
            ax.text(
                x + w / 2, y + h / 2, porcentaje(valor / total, 1), ha="center", va="center", fontsize=6.5, color=texto
            )
    ax.set_xlim(0, ancho)
    ax.set_ylim(0, alto)
    ax.invert_yaxis()
    ax.axis("off")
    return _png(fig)


def pareto_tipos(items: list[tuple[str, int]], umbral: float = 0.8) -> bytes:
    """Los tipos de mayor a menor volumen (columnas) con la participación acumulada (línea) y la guía del 80 %."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.3))
    total = sum(v for _, v in items) or 1
    valores = [v for _, v in items]
    acumulado = []
    suma = 0
    for v in valores:
        suma += v
        acumulado.append(suma / total * 100)
    x = list(range(len(valores)))
    ax.bar(x, valores, color=AZUL, width=0.62, zorder=3)
    for xi, v in enumerate(valores):
        ax.annotate(entero(v), (xi, v), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=7, color=TINTA)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, (max(valores) if valores else 1) * 1.25)
    ax.set_xticks(x)
    ax.set_xticklabels([n for n, _ in items], fontsize=7.5, rotation=18, ha="right")
    _ejes_sin_y(ax)
    eje2 = ax.twinx()
    eje2.plot(x, acumulado, color=NOCHE, linewidth=2, marker="o", markersize=4, markerfacecolor="white", zorder=4)
    for xi, v in enumerate(acumulado):
        eje2.annotate(
            f"{decimal(v, 1)} %",
            (xi, v),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=6.5,
            color=NOCHE,
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.85},
        )
    eje2.axhline(umbral * 100, color=AMARILLO, linestyle="--", linewidth=1.2)
    eje2.annotate(
        f"{entero(umbral * 100)} % del volumen",
        (len(x) - 0.5, umbral * 100),
        textcoords="offset points",
        xytext=(0, -10),
        ha="right",
        fontsize=7.5,
        color=GRIS,
    )
    eje2.set_ylim(0, 118)
    eje2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    eje2.spines["top"].set_visible(False)
    eje2.spines["right"].set_visible(False)
    eje2.tick_params(axis="y", length=0)
    return _png(fig)


def tipos_dos_anios(
    nombres: list[str], actual: list[int], anterior: list[int | None], anio: int, anio_anterior: int | None
) -> bytes:
    """Barras horizontales por tipo: el año del informe (azul) y, al lado, el año anterior (amarillo), con la cifra."""
    preparar()
    n = len(nombres)
    fig, ax = plt.subplots(figsize=(8, max(2.2, 0.7 + 0.5 * n)))
    y = list(range(n))[::-1]
    con_anterior = anio_anterior is not None and any(v for v in anterior)
    alto = 0.36 if con_anterior else 0.62
    ax.barh(
        [yi + (alto / 2 if con_anterior else 0) for yi in y], actual, color=AZUL, height=alto, label=str(anio), zorder=3
    )
    for yi, v in zip(y, actual, strict=True):
        ax.annotate(
            entero(v),
            (v, yi + (alto / 2 if con_anterior else 0)),
            textcoords="offset points",
            xytext=(4, 0),
            va="center",
            fontsize=7,
            color=TINTA,
        )
    if con_anterior:
        previos = [v or 0 for v in anterior]
        ax.barh([yi - alto / 2 for yi in y], previos, color=AMARILLO, height=alto, label=str(anio_anterior), zorder=3)
        for yi, v in zip(y, previos, strict=True):
            ax.annotate(
                entero(v),
                (v, yi - alto / 2),
                textcoords="offset points",
                xytext=(4, 0),
                va="center",
                fontsize=7,
                color=GRIS,
            )
    ax.set_yticks(y)
    ax.set_yticklabels(nombres, fontsize=8)
    maximo = max([*actual, *[v or 0 for v in anterior]]) if nombres else 1
    ax.set_xlim(0, (maximo or 1) * 1.18)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.spines["bottom"].set_color(FILETE)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    if con_anterior:
        ax.legend(loc="lower right", ncol=2)
    return _png(fig)
