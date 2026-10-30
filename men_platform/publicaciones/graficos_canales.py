"""Los gráficos del Informe de Canales de Atención, que replican las vistas del informe interactivo: barras por mes
(lado a lado o apiladas) con una línea de porcentaje encima, líneas de niveles, barras por canal y mezcla de canales
al 100 %. Las vistas de dos años, variación y media móvil se toman de graficos_tablero. Misma identidad que
graficos_pqrsdf: Inter, azul para lo atendido, rojo para lo abandonado, amarillo de referencia, sin guías."""

from __future__ import annotations

import matplotlib.pyplot as plt

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
from men_platform.publicaciones.texto_es import decimal, entero

# un color por canal, en el orden del catálogo
PALETA_CANALES = {
    1: AZUL,  # Atención Telefónica
    2: AZUL_CLARO,  # Chat
    3: NOCHE,  # Llamada Virtual
    4: "#4a80d2",  # Video Llamada Virtual
    5: AMARILLO,  # Chatbot
    6: GRIS_TENUE,  # Devolución de Llamadas
    7: "#a9c3ee",  # Atención Presencial
    8: ROJO,  # Buzón de Voz
}
NEUTRO = "#c2cde0"  # lo recibido, al lado de lo atendido
CLAROS = (AZUL_CLARO, AMARILLO, "#a9c3ee", NEUTRO)


def _leyenda(ax: plt.Axes, manijas: list, nombres: list[str]) -> None:
    """Hasta tres entradas, arriba del gráfico; con más, debajo del eje para que no tapen el dibujo."""
    if len(nombres) <= 3:
        ax.legend(manijas, nombres, loc="upper left", ncol=len(nombres), bbox_to_anchor=(0, 1.1))
    else:
        ax.legend(manijas, nombres, loc="upper center", ncol=4, bbox_to_anchor=(0.5, -0.12), fontsize=7.5)


def barras_con_linea(
    etiquetas: list[str],
    partes: list[tuple[str, str, list[int]]],
    linea: tuple[str, list[float | None]] | None,
    apiladas: bool = False,
    resaltar: int | None = None,
) -> bytes:
    """Barras por mes, lado a lado o apiladas, de las `partes` (nombre, color, valores) y encima la `linea` de porcentaje
    (nombre, valores entre 0 y 1) en su propio eje, en la franja alta del gráfico para no cruzar las barras. `resaltar`
    es la posición del mes del informe (su rótulo va en negrita)."""
    preparar()
    muchas = len(partes) + (1 if linea else 0) > 3
    fig, ax = plt.subplots(figsize=(8, 4.3 if muchas else 3.8))
    x = list(range(len(etiquetas)))
    n = len(partes)
    ancho = 0.62 if apiladas or n == 1 else 0.72 / n
    base = [0.0] * len(x)
    tope = 0.0
    for k, (nombre, color, valores) in enumerate(partes):
        if apiladas:
            ax.bar(x, valores, bottom=base, color=color, width=ancho, label=nombre, zorder=3)
            base = [b + v for b, v in zip(base, valores, strict=True)]
            tope = max(tope, max(base) if base else 0)
        else:
            desplaz = [xi - 0.36 + ancho * (k + 0.5) for xi in x]
            ax.bar(desplaz, valores, color=color, width=ancho * 0.95, label=nombre, zorder=3)
            tope = max(tope, max(valores) if valores else 0)
    if len(etiquetas) <= 13 and (apiladas or n == 1):
        for xi, v in enumerate(base if apiladas else partes[0][2]):
            if v:
                ax.annotate(
                    entero(v), (xi, v), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=6.5, color=GRIS
                )
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    if resaltar is not None and 0 <= resaltar < len(etiquetas):
        ax.get_xticklabels()[resaltar].set_fontweight("bold")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    # con línea, las barras ocupan la mitad baja y la línea la franja alta
    ax.set_ylim(0, (tope or 1) * (2.05 if linea else 1.3))
    _ejes_sin_y(ax)
    manijas, nombres = ax.get_legend_handles_labels()
    if linea is not None:
        nombre_linea, valores_linea = linea
        eje2 = ax.twinx()
        y = [(v * 100) if v is not None else float("nan") for v in valores_linea]
        color_linea = NOCHE if not any(c == NOCHE for _, c, _ in partes) else AMARILLO
        eje2.plot(
            x,
            y,
            color=color_linea,
            linewidth=2,
            marker="o",
            markersize=4.5,
            markerfacecolor="white",
            markeredgewidth=1.6,
            label=nombre_linea,
            zorder=4,
        )
        if len(etiquetas) <= 13:
            for xi, v in enumerate(y):
                if v == v:
                    eje2.annotate(
                        f"{decimal(v, 1)} %",
                        (xi, v),
                        textcoords="offset points",
                        xytext=(0, 7),
                        ha="center",
                        fontsize=7,
                        color=TINTA,
                        fontweight="bold" if xi == resaltar else "normal",
                    )
        validos = [v for v in y if v == v]
        if validos:
            alto, bajo = max(validos), min(validos)
            tramo = max(alto - bajo, 5.0)
            eje2.set_ylim(bajo - tramo * 1.7, alto + tramo * 0.35)
        # la franja alta de la línea puede empezar bajo cero cuando el índice se mueve mucho (la oportunidad de las
        # legalizaciones va del 21 % al 82 % en un año): esos valores negativos no se rotulan
        eje2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %" if v >= 0 else ""))
        eje2.spines["top"].set_visible(False)
        eje2.spines["right"].set_visible(False)
        eje2.tick_params(axis="y", length=0)
        m2, n2 = eje2.get_legend_handles_labels()
        manijas += m2
        nombres += n2
    _leyenda(ax, manijas, nombres)
    return _png(fig)


def lineas_niveles(
    etiquetas: list[str],
    lineas: list[tuple[str, str, list[float | None]]],
    resaltar: int | None = None,
    leyenda: str = "lower left",
) -> bytes:
    """Una línea por nivel (nombre, color, valores entre 0 y 1), mes a mes, con el valor de cada punto; `leyenda` es su
    posición, para que no tape los puntos bajos."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    x = list(range(len(etiquetas)))
    todos: list[float] = []
    for i, (nombre, color, valores) in enumerate(lineas):
        y = [(v * 100) if v is not None else float("nan") for v in valores]
        todos += [v for v in y if v == v]
        ax.plot(
            x,
            y,
            color=color,
            linewidth=2.2 if i == 0 else 1.8,
            linestyle="-" if i == 0 else "--",
            marker="o" if i == 0 else "D",
            markersize=4.5 if i == 0 else 3.5,
            markerfacecolor="white",
            markeredgewidth=1.6,
            label=nombre,
            zorder=3,
        )
        if len(etiquetas) <= 13:
            for xi, v in enumerate(y):
                if v == v:
                    ax.annotate(
                        f"{decimal(v, 1)} %",
                        (xi, v),
                        textcoords="offset points",
                        xytext=(0, 7 if i == 0 else -11),
                        ha="center",
                        fontsize=7,
                        color=color if color not in CLAROS else TINTA,
                        fontweight="bold" if xi == resaltar else "normal",
                    )
    if todos:
        bajo, alto = min(todos), max(todos)
        margen = max(4.0, (alto - bajo) * 0.4)
        ax.set_ylim(max(0, bajo - margen), alto + margen if alto < 96 else 103)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    if resaltar is not None and 0 <= resaltar < len(etiquetas):
        ax.get_xticklabels()[resaltar].set_fontweight("bold")
    ax.legend(loc=leyenda, ncol=len(lineas))
    _ejes_sin_y(ax)
    return _png(fig)


def mezcla(etiquetas: list[str], partes: list[tuple[str, str, list[int]]]) -> bytes:
    """Columnas al 100 % por mes con la parte de cada canal (nombre, color, valores); la leyenda va debajo."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = list(range(len(etiquetas)))
    totales = [sum(p[2][i] for p in partes) or 1 for i in x]
    base = [0.0] * len(x)
    for nombre, color, valores in partes:
        pct = [v / tot * 100 for v, tot in zip(valores, totales, strict=True)]
        ax.bar(x, pct, bottom=base, color=color, width=0.62, label=nombre, zorder=3)
        for xi, (b, v) in enumerate(zip(base, pct, strict=True)):
            if v >= 7:
                ax.text(
                    xi,
                    b + v / 2,
                    f"{decimal(v, 1)} %",
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color=TINTA if color in CLAROS else "white",
                    fontweight="bold",
                )
        base = [b + v for b, v in zip(base, pct, strict=True)]
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    ax.set_ylim(0, 104)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    manijas, nombres = ax.get_legend_handles_labels()
    _leyenda(ax, manijas, nombres)
    _ejes_sin_y(ax)
    return _png(fig)


def barras_por_canal(etiquetas: list[str], valores: list[int], colores: list[str]) -> bytes:
    """Barras horizontales de lo recibido por canal en el mes, de mayor a menor."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 0.6 + 0.42 * len(etiquetas)))
    y = list(range(len(etiquetas)))[::-1]
    ax.barh(y, valores, color=colores, height=0.62, zorder=3)
    for yi, v in zip(y, valores, strict=True):
        ax.annotate(
            entero(v), (v, yi), textcoords="offset points", xytext=(4, 0), va="center", fontsize=7.5, color=TINTA
        )
    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas)
    ax.set_xlim(0, (max(valores) if valores else 1) * 1.18)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.spines["bottom"].set_color(FILETE)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    return _png(fig)
