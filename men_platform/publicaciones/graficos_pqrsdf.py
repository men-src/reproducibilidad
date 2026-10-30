"""Los gráficos del Informe General de PQRSDF, con matplotlib y la identidad de la plataforma: Inter, el azul
institucional para lo a tiempo, el rojo bandera solo para lo extemporáneo, el amarillo de referencia para pronósticos
y comparaciones, sin líneas de guía (D-71) ni línea del eje Y. Cada función devuelve el PNG en bytes."""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from men_platform.publicaciones.datos_pqrsdf import Totales  # noqa: E402
from men_platform.publicaciones.texto_es import (  # noqa: E402
    decimal,
    entero,
    mes_corto,
    mes_corto_2,
    nombre_propio,
    porcentaje,
)

AZUL = "#1e5bbd"
AZUL_CLARO = "#7aa3e2"
NOCHE = "#0c2543"
ROJO = "#cf1433"
AMARILLO = "#e0b400"
TINTA = "#0f1d35"
GRIS = "#4a5a78"
GRIS_TENUE = "#7b89a6"
FILETE = "#c2cde0"

_FUENTES = Path(__file__).parent / "recursos" / "fuentes"
_preparado = False


def preparar() -> None:
    """Registra Inter en matplotlib y fija el estilo plano de la plataforma (una sola vez)."""
    global _preparado  # noqa: PLW0603
    if _preparado:
        return
    for archivo in _FUENTES.glob("Inter-*.ttf"):
        font_manager.fontManager.addfont(str(archivo))
    plt.rcParams.update(
        {
            "font.family": "Inter",
            "font.size": 9,
            "axes.edgecolor": FILETE,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": False,
            "xtick.color": GRIS,
            "ytick.color": GRIS,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.labelcolor": GRIS,
            "text.color": TINTA,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "figure.dpi": 200,
            "savefig.dpi": 200,
        }
    )
    _preparado = True


def _png(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _miles(valor: float, _pos: int | None = None) -> str:
    if abs(valor) >= 1_000_000:
        return f"{decimal(valor / 1_000_000, 1).replace(',0', '')} M"
    if abs(valor) >= 1_000:
        return f"{decimal(valor / 1_000, 1).replace(',0', '')} mil"
    return entero(valor)


def _ejes_sin_y(ax: plt.Axes) -> None:
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)


def oportunidad_mensual(serie: list[tuple[str, Totales]], resaltar: str) -> bytes:
    """Línea del % de oportunidad en los últimos trece meses, con el valor sobre cada punto."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    x = list(range(len(serie)))
    y = [(t.oportunidad or 0) * 100 for _, t in serie]
    ax.plot(
        x,
        y,
        color=AZUL,
        linewidth=2.2,
        marker="o",
        markersize=5,
        markerfacecolor="white",
        markeredgewidth=1.8,
        zorder=3,
    )
    for xi, yi, (p, _) in zip(x, y, serie, strict=True):
        peso = "bold" if p == resaltar else "normal"
        ax.annotate(
            f"{decimal(yi, 2)} %",
            (xi, yi),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=7.5,
            color=TINTA,
            fontweight=peso,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([mes_corto_2(p) if len(serie) > 9 else mes_corto(p) for p, _ in serie])
    minimo = max(0, min(y) - 8)
    ax.set_ylim(minimo, 100 if max(y) > 90 else max(y) + 8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    _ejes_sin_y(ax)
    return _png(fig)


def volumen_mensual(serie: list[tuple[str, Totales]], resaltar: str) -> bytes:
    """Columnas apiladas: a tiempo (azul) y extemporáneas (rojo) por mes, con el total encima."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    x = list(range(len(serie)))
    at = [t.a_tiempo for _, t in serie]
    ex = [t.extemporaneas for _, t in serie]
    ax.bar(x, at, color=AZUL, width=0.62, label="A tiempo", zorder=3)
    ax.bar(x, ex, bottom=at, color=ROJO, width=0.62, label="Extemporáneas", zorder=3)
    for xi, (a, e, (p, _)) in enumerate(zip(at, ex, serie, strict=True)):
        ax.annotate(
            entero(a + e),
            (xi, a + e),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7.5,
            color=TINTA,
            fontweight="bold" if p == resaltar else "normal",
        )
    ax.set_xticks(x)
    ax.set_xticklabels([mes_corto(p) for p, _ in serie])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, max(a + e for a, e in zip(at, ex, strict=True)) * 1.15)
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.08))
    _ejes_sin_y(ax)
    return _png(fig)


def barras_horizontales(
    items: list[tuple[str, float]],
    formato: str = "entero",
    color: str = AZUL,
    alto_por_fila: float = 0.34,
    limite_pct: bool = False,
) -> bytes:
    """Barras horizontales de mayor a menor con el valor al final de cada barra. `formato`: 'entero' o 'porcentaje'."""
    preparar()
    n = len(items)
    fig, ax = plt.subplots(figsize=(8, max(1.6, 0.6 + alto_por_fila * n)))
    etiquetas = [nombre_propio(k) if len(k) <= 58 else nombre_propio(k[:55]).rstrip() + "…" for k, _ in items][::-1]
    valores = [v for _, v in items][::-1]
    y = list(range(n))
    ax.barh(y, valores, color=color, height=0.62, zorder=3)
    maximo = max(valores) if valores else 1
    for yi, v in zip(y, valores, strict=True):
        texto = porcentaje(v / 100, 2) if formato == "porcentaje" else entero(v)
        ax.annotate(texto, (v, yi), textcoords="offset points", xytext=(4, 0), va="center", fontsize=7.5, color=TINTA)
    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas, fontsize=8)
    ax.set_xlim(0, (100 if limite_pct else maximo) * 1.18)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    _ejes_sin_y(ax)
    return _png(fig)


def dias_gestion(serie: list[tuple[str, Totales]], resaltar: str) -> bytes:
    """Dos líneas: días hábiles promedio de gestión (azul) y de retraso de las extemporáneas (rojo)."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    x = list(range(len(serie)))
    g = [t.promedio_dias_gestion or 0 for _, t in serie]
    r = [t.promedio_dias_retraso or 0 for _, t in serie]
    ax.plot(
        x,
        g,
        color=AZUL,
        linewidth=2.2,
        marker="o",
        markersize=4.5,
        markerfacecolor="white",
        markeredgewidth=1.8,
        label="Días hábiles de gestión (promedio)",
        zorder=3,
    )
    ax.plot(
        x,
        r,
        color=ROJO,
        linewidth=1.8,
        marker="s",
        markersize=3.5,
        label="Días hábiles de retraso de las extemporáneas (promedio)",
        zorder=3,
    )
    for xi, (gi, ri, (p, _)) in enumerate(zip(g, r, serie, strict=True)):
        peso = "bold" if p == resaltar else "normal"
        ax.annotate(
            decimal(gi, 1),
            (xi, gi),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=7,
            color=AZUL,
            fontweight=peso,
        )
        ax.annotate(
            decimal(ri, 1),
            (xi, ri),
            textcoords="offset points",
            xytext=(0, -11),
            ha="center",
            fontsize=7,
            color=ROJO,
            fontweight=peso,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([mes_corto_2(p) if len(serie) > 9 else mes_corto(p) for p, _ in serie])
    ax.set_ylim(0, max(g + r) * 1.25)
    ax.legend(loc="upper left", ncol=1, bbox_to_anchor=(0, 1.12))
    _ejes_sin_y(ax)
    return _png(fig)


def real_vs_pronostico(puntos: list[tuple[str, float | None, float]]) -> bytes:
    """El índice real del año (azul) frente al pronóstico mensual del modelo (amarillo punteado), hasta el mes del informe."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    x = list(range(len(puntos)))
    real = [(r * 100) if r is not None else float("nan") for _, r, _ in puntos]
    pron = [p * 100 for _, _, p in puntos]
    ax.plot(
        x, pron, color=AMARILLO, linewidth=1.8, linestyle="--", marker="D", markersize=3.5, label="Pronóstico", zorder=2
    )
    ax.plot(
        x,
        real,
        color=AZUL,
        linewidth=2.2,
        marker="o",
        markersize=4.5,
        markerfacecolor="white",
        markeredgewidth=1.8,
        label="Real",
        zorder=3,
    )
    for xi, (rv, pv) in enumerate(zip(real, pron, strict=True)):
        if rv == rv:  # noqa: PLR0124  (no es NaN)
            ax.annotate(
                f"{decimal(rv, 1)} %",
                (xi, rv),
                textcoords="offset points",
                xytext=(0, -12),
                ha="center",
                fontsize=7,
                color=AZUL,
            )
        ax.annotate(
            f"{decimal(pv, 1)} %",
            (xi, pv),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=7,
            color=AMARILLO,
        )
    todos = [v for v in real + pron if v == v]
    ax.set_ylim(max(0, min(todos) - 10), 100 if max(todos) > 90 else max(todos) + 10)
    ax.set_xticks(x)
    ax.set_xticklabels([mes_corto(p) for p, _, _ in puntos])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    ax.legend(loc="lower left", ncol=2)
    _ejes_sin_y(ax)
    return _png(fig)


def estados_del_mes(t: Totales) -> bytes:
    """Una barra apilada al 100 %: a tiempo y extemporáneas, como el tablero; el detalle de abiertas y cerradas va en la tabla."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 1.5))
    partes = [
        ("A tiempo", t.a_tiempo, AZUL),
        ("Extemporáneas", t.extemporaneas, ROJO),
    ]
    total = t.radicados or 1
    izquierda = 0.0
    for nombre, valor, color in partes:
        ancho = valor / total * 100
        ax.barh([0], [ancho], left=izquierda, color=color, height=0.6, label=nombre, zorder=3)
        if ancho >= 6:
            ax.text(
                izquierda + ancho / 2,
                0,
                f"{decimal(ancho, 1)} %",
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                fontweight="bold",
            )
        izquierda += ancho
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.05))
    return _png(fig)


def radicacion_anio(serie: list[tuple[str, Totales]], resaltar: str) -> bytes:
    """Columnas apiladas por mes de radicación: lo que vence en el mismo mes (a gestionar en el mes) y lo que vence después."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    x = list(range(len(serie)))
    en_mes = [t.a_gestionar_mes for _, t in serie]
    resto = [t.radicados - t.a_gestionar_mes for _, t in serie]
    ax.bar(x, en_mes, color=AZUL, width=0.62, label="A gestionar en el mes", zorder=3)
    ax.bar(x, resto, bottom=en_mes, color=AZUL_CLARO, width=0.62, label="Vence después del mes", zorder=3)
    for xi, (a, b, (p, _)) in enumerate(zip(en_mes, resto, serie, strict=True)):
        ax.annotate(
            entero(a + b),
            (xi, a + b),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7.5,
            color=TINTA,
            fontweight="bold" if p == resaltar else "normal",
        )
    ax.set_xticks(x)
    ax.set_xticklabels([mes_corto(p) for p, _ in serie])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, max(a + b for a, b in zip(en_mes, resto, strict=True)) * 1.15)
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.08))
    _ejes_sin_y(ax)
    return _png(fig)


def comparacion_dos_meses(anterior: Totales, actual: Totales, etiqueta_anterior: str, etiqueta_actual: str) -> bytes:
    """Barras agrupadas: gestionadas, a tiempo y extemporáneas del mes anterior (gris) y del mes del informe (azul)."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    categorias = ["Gestionadas", "A tiempo", "Extemporáneas"]
    va = [anterior.radicados, anterior.a_tiempo, anterior.extemporaneas]
    vb = [actual.radicados, actual.a_tiempo, actual.extemporaneas]
    x = list(range(len(categorias)))
    ancho = 0.36
    ax.bar([i - ancho / 2 for i in x], va, width=ancho, color=GRIS_TENUE, label=etiqueta_anterior, zorder=3)
    ax.bar([i + ancho / 2 for i in x], vb, width=ancho, color=AZUL, label=etiqueta_actual, zorder=3)
    for i in x:
        ax.annotate(
            entero(va[i]),
            (i - ancho / 2, va[i]),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7.5,
            color=GRIS,
        )
        ax.annotate(
            entero(vb[i]),
            (i + ancho / 2, vb[i]),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7.5,
            color=TINTA,
            fontweight="bold",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(categorias)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, max(va + vb) * 1.18)
    ax.legend(loc="upper right", ncol=2)
    _ejes_sin_y(ax)
    return _png(fig)
