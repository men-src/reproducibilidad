"""Los gráficos propios del Informe de Legalizaciones, que replican las vistas del informe interactivo: la distribución
de las legalizadas por días hábiles de gestión con el plazo marcado, las barras horizontales apiladas por categoría
(resultado, a tiempo y extemporáneas), las líneas de valores por mes (los días promedio) y las barras dobles por
categoría (días calendario y hábiles). Las barras por mes con referencia, el treemap, el Pareto y la comparación de
dos años por categoría se toman de graficos_tramites; las apiladas por mes, la mezcla al 100 %, las barras por
categoría y las líneas de porcentaje, de graficos_canales; las vistas de dos años, variación, media móvil y mapa de
calor, de graficos_tablero. Misma identidad: Inter, la paleta de la plataforma, sin guías."""

from __future__ import annotations

import matplotlib.pyplot as plt

from men_platform.publicaciones.datos_legalizaciones import ETIQUETAS_HABILES
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

# Un color por resultado, el mismo en todas las vistas: legalizado en azul, cancelado en rojo y en curso en amarillo.
COLOR_RESULTADO: dict[str, str] = {"legalizadas": AZUL, "canceladas": ROJO, "en curso": AMARILLO}
# Un color por metodología, el mismo que usa el informe interactivo; las que no están toman uno de reserva por posición.
PALETA_METODOLOGIA: dict[str, str] = {
    "pregrado": AZUL,
    "maestria": "#0a2a66",
    "especializacion": AZUL_CLARO,
    "tecnologo": AMARILLO,
    "tecnico profesional": NOCHE,
    "certificacion": ROJO,
    "doctorado": "#840c20",
    "documento men": GRIS_TENUE,
    "resolucion": "#f0485c",
    "distincion": "#600816",
    "normalista": "#ec7a8a",
}
RESERVA = [AMARILLO, AZUL_CLARO, NOCHE, "#840c20", "#0a2a66", "#f0485c", GRIS_TENUE, "#600816"]
# Los tipos de documento no tienen color fijo: toman uno de la serie por posición, de mayor a menor volumen.
SERIE = [
    AZUL,
    AMARILLO,
    NOCHE,
    AZUL_CLARO,
    ROJO,
    "#0a2a66",
    "#840c20",
    GRIS_TENUE,
    "#f0485c",
    "#600816",
    "#4a80d2",
    "#ec7a8a",
]
# Del rango más rápido al más lento: azules que se aclaran y luego rojos que se oscurecen.
COLORES_RANGOS = ["#0a2a66", AZUL, AZUL_CLARO, "#a9c3ee", "#ec7a8a", ROJO, "#840c20"]
CLAROS = {AZUL_CLARO, AMARILLO, GRIS_TENUE, "#f0485c", "#ec7a8a", "#a9c3ee"}  # sobre estos el texto va en tinta


def color_metodologia(fuente: str, posicion: int = 0) -> str:
    return PALETA_METODOLOGIA.get(fuente, RESERVA[posicion % len(RESERVA)])


def color_documento(posicion: int) -> str:
    return SERIE[posicion % len(SERIE)]


def _recortar(nombre: str, largo: int = 44) -> str:
    return nombre if len(nombre) <= largo else nombre[: largo - 1].rstrip() + "…"


def histograma_habiles(conteos: list[int], plazo: int) -> bytes:
    """Las legalizadas por días hábiles de gestión: azules hasta el plazo (a tiempo), rojas después (extemporáneas),
    con la línea punteada del plazo y el acumulado en porcentaje en su propio eje."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    valores = [conteos[i] if i < len(conteos) else 0 for i in range(len(ETIQUETAS_HABILES))]
    total = sum(valores) or 1
    limite = min(max(0, plazo), 15) + (1 if plazo > 15 else 0)
    x = list(range(len(valores)))
    colores = [AZUL if i <= limite else ROJO for i in x]
    ax.bar(x, valores, color=colores, width=0.68, zorder=3)
    for xi, v in zip(x, valores, strict=True):
        if v:
            ax.annotate(
                _miles(v), (xi, v), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=6.3, color=TINTA
            )
    ax.axvline(limite + 0.5, color=AMARILLO, linestyle="--", linewidth=1.6, zorder=4)
    ax.annotate(
        f"Plazo: hasta {plazo} {'día hábil' if plazo == 1 else 'días hábiles'}",
        (limite + 0.5, max(valores) * 1.3),
        textcoords="offset points",
        xytext=(5, 0),
        ha="left",
        va="center",
        fontsize=7.5,
        color=GRIS,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(ETIQUETAS_HABILES, fontsize=7.5)
    ax.set_xlabel("Días hábiles de gestión", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, max(valores) * 1.45 if valores else 1)
    _ejes_sin_y(ax)
    eje2 = ax.twinx()
    acumulado = []
    suma = 0
    for v in valores:
        suma += v
        acumulado.append(suma / total * 100)
    eje2.plot(x, acumulado, color=NOCHE, linewidth=1.8, marker="o", markersize=3.2, markerfacecolor="white", zorder=5)
    for xi in (limite, len(x) - 1):
        eje2.annotate(
            f"{decimal(acumulado[xi], 1)} %",
            (xi, acumulado[xi]),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=7,
            color=NOCHE,
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.85},
        )
    eje2.set_ylim(0, 118)
    eje2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    eje2.spines["top"].set_visible(False)
    eje2.spines["right"].set_visible(False)
    eje2.tick_params(axis="y", length=0)
    manijas = [
        plt.Rectangle((0, 0), 1, 1, color=AZUL),
        plt.Rectangle((0, 0), 1, 1, color=ROJO),
        plt.Line2D([0], [0], color=NOCHE, marker="o", markersize=3.2, markerfacecolor="white"),
    ]
    ax.legend(manijas, ["A tiempo", "Extemporáneas", "Acumulado"], loc="upper right", ncol=3, bbox_to_anchor=(1, 1.12))
    return _png(fig)


def barras_apiladas_horizontales(
    nombres: list[str], partes: list[tuple[str, str, list[int]]], etiquetas_finales: list[str]
) -> bytes:
    """Barras horizontales apiladas por categoría, de arriba abajo en el orden dado: las `partes` (nombre, color,
    valores) y, al final de cada barra, su etiqueta (el total con su razón)."""
    preparar()
    n = len(nombres)
    fig, ax = plt.subplots(figsize=(8, max(1.9, 0.7 + 0.36 * n)))
    y = list(range(n))[::-1]
    base = [0.0] * n
    for nombre, color, valores in partes:
        ax.barh(y, valores, left=base, color=color, height=0.62, label=nombre, zorder=3)
        base = [b + v for b, v in zip(base, valores, strict=True)]
    for yi, total, etiqueta in zip(y, base, etiquetas_finales, strict=True):
        ax.annotate(
            etiqueta, (total, yi), textcoords="offset points", xytext=(4, 0), va="center", fontsize=7.3, color=TINTA
        )
    ax.set_yticks(y)
    ax.set_yticklabels([_recortar(x) for x in nombres], fontsize=7.8)
    ax.set_xlim(0, (max(base) if base else 1) * 1.5)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.legend(loc="lower right", ncol=len(partes))
    _ejes_sin_y(ax)
    return _png(fig)


def lineas_valores(
    etiquetas: list[str],
    lineas: list[tuple[str, str, list[float | None]]],
    unidad: str,
    resaltar: int | None = None,
) -> bytes:
    """Varias líneas de valores por mes (días, cantidades) con su unidad; el eje arranca en cero y la primera línea
    lleva las cifras."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    x = list(range(len(etiquetas)))
    tope = 0.0
    for i, (nombre, color, valores) in enumerate(lineas):
        y = [v if v is not None else float("nan") for v in valores]
        tope = max([tope, *[v for v in y if v == v]])
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
                        decimal(v, 1),
                        (xi, v),
                        textcoords="offset points",
                        xytext=(0, 7 if i == 0 else -11),
                        ha="center",
                        fontsize=7,
                        color=color if color not in CLAROS else TINTA,
                        fontweight="bold" if xi == resaltar else "normal",
                    )
    ax.set_ylim(0, (tope or 1) * 1.3)
    ax.set_ylabel(unidad, fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    if resaltar is not None and 0 <= resaltar < len(etiquetas):
        ax.get_xticklabels()[resaltar].set_fontweight("bold")
    ax.legend(loc="upper left", ncol=len(lineas), bbox_to_anchor=(0, 1.1))
    _ejes_sin_y(ax)
    return _png(fig)


def barras_dobles_horizontales(
    nombres: list[str], series: list[tuple[str, str, list[float | None]]], decimales: int = 1
) -> bytes:
    """Barras horizontales lado a lado por categoría (dos series, como días calendario y días hábiles), con la cifra al
    final de cada barra."""
    preparar()
    n = len(nombres)
    k = len(series)
    fig, ax = plt.subplots(figsize=(8, max(2.0, 0.7 + 0.5 * n)))
    y = list(range(n))[::-1]
    alto = 0.72 / k
    maximo = 0.0
    for j, (nombre, color, valores) in enumerate(series):
        desplazados = [yi + 0.36 - alto * (j + 0.5) for yi in y]
        vals = [v or 0 for v in valores]
        maximo = max([maximo, *vals])
        ax.barh(desplazados, vals, color=color, height=alto * 0.95, label=nombre, zorder=3)
        for yi, v in zip(desplazados, vals, strict=True):
            ax.annotate(
                decimal(v, decimales),
                (v, yi),
                textcoords="offset points",
                xytext=(4, 0),
                va="center",
                fontsize=7,
                color=TINTA if j == 0 else GRIS,
            )
    ax.set_yticks(y)
    ax.set_yticklabels([_recortar(x) for x in nombres], fontsize=8)
    ax.set_xlim(0, (maximo or 1) * 1.18)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: decimal(v, 0)))
    ax.spines["bottom"].set_color(FILETE)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="lower right", ncol=k)
    return _png(fig)
