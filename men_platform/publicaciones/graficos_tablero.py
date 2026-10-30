"""Los gráficos que replican las vistas del tablero de control de PQRSDF: mes a mes con el índice, variaciones frente
al mes anterior, mapa de calor mes × año, series con su media móvil, dos años, brechas, burbujas y flujos de
requerimientos, Pareto de ejes y mezcla de canales. Misma identidad que graficos_pqrsdf."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib import colors as mcolors

from men_platform.publicaciones.datos_pqrsdf import Totales
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
from men_platform.publicaciones.texto_es import (
    MESES_CORTOS,
    decimal,
    entero,
    mes_corto,
    mes_corto_2,
    nombre_propio,
    porcentaje,
)

PALETA_CANALES = {
    "correo electronico": AZUL,
    "web": AZUL_CLARO,
    "correspondencia": NOCHE,
    "sin informacion": GRIS_TENUE,
}


def _etiquetas(serie: list[tuple[str, object]]) -> list[str]:
    return [mes_corto_2(p) if len(serie) > 9 else mes_corto(p) for p, _ in serie]


def mes_a_mes(serie: list[tuple[str, Totales]], resaltar: str) -> bytes:
    """Como el Resumen del tablero: columnas a tiempo y extemporáneas por mes y, sobre ellas, la línea del % de oportunidad."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    x = list(range(len(serie)))
    at = [t.a_tiempo for _, t in serie]
    ex = [t.extemporaneas for _, t in serie]
    ax.bar(x, at, color=AZUL, width=0.62, label="A tiempo", zorder=3)
    ax.bar(x, ex, bottom=at, color=ROJO, width=0.62, label="Extemporáneas", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(_etiquetas(serie))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, max(a + e for a, e in zip(at, ex, strict=True)) * 1.45)
    _ejes_sin_y(ax)
    eje2 = ax.twinx()
    y = [(t.oportunidad or 0) * 100 for _, t in serie]
    eje2.plot(
        x,
        y,
        color=NOCHE,
        linewidth=2,
        marker="o",
        markersize=4.5,
        markerfacecolor="white",
        markeredgewidth=1.6,
        label="% de oportunidad",
        zorder=4,
    )
    for xi, (yi, (p, _)) in enumerate(zip(y, serie, strict=True)):
        eje2.annotate(
            f"{decimal(yi, 1)} %",
            (xi, yi),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=7,
            color=NOCHE,
            fontweight="bold" if p == resaltar else "normal",
        )
    eje2.set_ylim(0, 100 * 1.3)
    eje2.set_yticks([0, 20, 40, 60, 80, 100])
    eje2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    eje2.spines["top"].set_visible(False)
    eje2.spines["right"].set_visible(False)
    eje2.tick_params(axis="y", length=0)
    lineas = ax.get_legend_handles_labels()
    lineas2 = eje2.get_legend_handles_labels()
    ax.legend(lineas[0] + lineas2[0], lineas[1] + lineas2[1], loc="upper left", ncol=3, bbox_to_anchor=(0, 1.1))
    return _png(fig)


def barras_variacion(
    etiquetas: list[str],
    valores: list[float | None],
    unidad: str,
    menor_mejor: bool = False,
    recorte: float | None = None,
) -> bytes:
    """Barras de la variación de un mes al siguiente: azul cuando mejora y rojo cuando empeora. `unidad`: 'pp' o '%'.
    Con `recorte`, las barras que superan ese valor absoluto se dibujan recortadas (con su cifra real) para que un mes
    atípico no aplaste a los demás."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.3))
    x = list(range(len(valores)))
    reales = [v if v is not None else 0 for v in valores]
    if recorte is not None:
        dentro = [abs(v) for v in reales if abs(v) <= recorte] or [recorte]
        limite = max(dentro) * 1.15
        vals = [max(-limite, min(limite, v)) for v in reales]
    else:
        vals = reales
    colores = [(ROJO if ((v < 0) != menor_mejor) else AZUL) if v != 0 else GRIS_TENUE for v in vals]
    ax.bar(x, vals, color=colores, width=0.62, zorder=3)
    ax.axhline(0, color=FILETE, linewidth=0.8)
    for xi, v, original, real in zip(x, vals, valores, reales, strict=True):
        if original is None:
            ax.annotate("–", (xi, 0), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=7.5, color=GRIS)
            continue
        texto = (
            f"{'+' if real > 0 else '−' if real < 0 else ''}{decimal(abs(real), 2 if unidad == 'pp' else 1)} {unidad}"
        )
        if v != real:
            texto += " ▲" if real > 0 else " ▼"
        ax.annotate(
            texto,
            (xi, v),
            textcoords="offset points",
            xytext=(0, 4 if v >= 0 else -11),
            ha="center",
            fontsize=7.5,
            color=TINTA,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    tope = max(abs(v) for v in vals) if vals else 1
    ax.set_ylim(-tope * 1.4 if min(vals) < 0 else 0, tope * 1.4 if max(vals) > 0 else 1)
    ax.yaxis.set_visible(False)
    _ejes_sin_y(ax)
    return _png(fig)


def mapa_calor(matriz: dict[int, dict[int, float | None]], resaltar: tuple[int, int], hasta: int = 12) -> bytes:
    """Mes × año del % de oportunidad, de enero a `hasta`: rojo el peor valor del periodo y azul oscuro el 100 %."""
    preparar()
    anios = sorted(matriz)
    fig, ax = plt.subplots(figsize=(8, 0.5 + 0.42 * len(anios)))
    valores = [[(matriz[a].get(m) or float("nan")) * 100 for m in range(1, hasta + 1)] for a in anios]
    minimo = min(v for fila in valores for v in fila if v == v)
    cmap = mcolors.LinearSegmentedColormap.from_list("oportunidad", [ROJO, "#f6d5d9", "#dce6f7", AZUL, "#0a2a66"])
    cmap.set_bad("#f3f6fa")
    im = ax.imshow(valores, cmap=cmap, vmin=minimo, vmax=100, aspect="auto")
    ax.set_xticks(range(hasta))
    ax.set_xticklabels(MESES_CORTOS[:hasta])
    ax.set_yticks(range(len(anios)))
    ax.set_yticklabels([str(a) for a in anios])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    for i, fila in enumerate(valores):
        for j, v in enumerate(fila):
            if v == v:
                oscuro = v > (minimo + 100) / 2
                peso = "bold" if (anios[i], j + 1) == resaltar else "normal"
                ax.text(
                    j,
                    i,
                    decimal(v, 1),
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white" if oscuro or v < minimo + (100 - minimo) * 0.25 else TINTA,
                    fontweight=peso,
                )
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, format=plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    return _png(fig)


def linea_con_media_movil(
    serie: list[tuple[str, float | None]],
    media: list[tuple[str, float | None]],
    resaltar: str,
    formato: str,
    nombre: str,
) -> bytes:
    """El valor real de cada mes (azul) y su media móvil de los tres meses anteriores (amarillo punteado). `formato`: 'porcentaje' o 'entero'."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    x = list(range(len(serie)))
    escala = 100 if formato == "porcentaje" else 1
    real = [(v * escala) if v is not None else float("nan") for _, v in serie]
    mm = [(v * escala) if v is not None else float("nan") for _, v in media]
    ax.plot(
        x,
        mm,
        color=AMARILLO,
        linewidth=1.8,
        linestyle="--",
        marker="D",
        markersize=3.5,
        label="Media móvil (3 meses anteriores)",
        zorder=2,
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
        label=nombre,
        zorder=3,
    )
    for xi, (v, (p, _)) in enumerate(zip(real, serie, strict=True)):
        if v == v:
            texto = f"{decimal(v, 1)} %" if formato == "porcentaje" else entero(v)
            ax.annotate(
                texto,
                (xi, v),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=7,
                color=TINTA,
                fontweight="bold" if p == resaltar else "normal",
            )
    todos = [v for v in real + mm if v == v]
    if formato == "porcentaje":
        ax.set_ylim(max(0, min(todos) - 8), 100 if max(todos) > 90 else max(todos) + 8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    else:
        ax.set_ylim(0, max(todos) * 1.25)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_xticks(x)
    ax.set_xticklabels(_etiquetas(serie))
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.1))
    _ejes_sin_y(ax)
    return _png(fig)


def dos_anios(
    actual: dict[int, float | None],
    anterior: dict[int, float | None],
    anio: int,
    formato: str,
    hasta: int = 12,
    leyenda: str = "lower left",
) -> bytes:
    """Un valor por mes, de enero a `hasta`, del año del informe (azul) y del año anterior (amarillo punteado); `formato` 'porcentaje' o 'entero'."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    escala = 100 if formato == "porcentaje" else 1
    meses = range(1, hasta + 1)
    x = list(range(hasta))
    ya = [(actual.get(m) * escala) if actual.get(m) is not None else float("nan") for m in meses]
    yb = [(anterior.get(m) * escala) if anterior.get(m) is not None else float("nan") for m in meses]
    if any(v == v for v in yb):
        ax.plot(
            x,
            yb,
            color=AMARILLO,
            linewidth=1.8,
            linestyle="--",
            marker="D",
            markersize=3.5,
            label=str(anio - 1),
            zorder=2,
        )
    ax.plot(
        x,
        ya,
        color=AZUL,
        linewidth=2.2,
        marker="o",
        markersize=4.5,
        markerfacecolor="white",
        markeredgewidth=1.8,
        label=str(anio),
        zorder=3,
    )
    for xi, v in enumerate(ya):
        if v == v:
            ax.annotate(
                f"{decimal(v, 1)} %" if formato == "porcentaje" else entero(v),
                (xi, v),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=7,
                color=TINTA,
            )
    todos = [v for v in ya + yb if v == v]
    if formato == "porcentaje":
        ax.set_ylim(max(0, min(todos) - 8), 100 if max(todos) > 90 else max(todos) + 8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    else:
        ax.set_ylim(0, max(todos) * 1.25)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_xticks(x)
    ax.set_xticklabels(MESES_CORTOS[:hasta])
    ax.legend(loc=leyenda, ncol=2)
    _ejes_sin_y(ax)
    return _png(fig)


def brecha(serie: list[tuple[str, Totales]], campo: str, nombre: str, color: str, resaltar: str) -> bytes:
    """El total general de cada mes (columna gris) y, dentro, la parte del campo (a tiempo en azul o extemporáneas en rojo)."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    x = list(range(len(serie)))
    total = [t.radicados for _, t in serie]
    parte = [getattr(t, campo) for _, t in serie]
    ax.bar(x, total, color="#dde4ef", width=0.62, label="Total general", zorder=2)
    ax.bar(x, parte, color=color, width=0.62, label=nombre, zorder=3)
    for xi, (tv, pv, (p, _)) in enumerate(zip(total, parte, serie, strict=True)):
        peso = "bold" if p == resaltar else "normal"
        ax.annotate(
            entero(tv),
            (xi, tv),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7.5,
            color=GRIS,
            fontweight=peso,
        )
        ax.annotate(
            porcentaje(pv / tv if tv else None, 1),
            (xi, pv),
            textcoords="offset points",
            xytext=(0, -10),
            ha="center",
            fontsize=7,
            color="white",
            fontweight="bold",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(_etiquetas(serie))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, max(total) * 1.18)
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.08))
    _ejes_sin_y(ax)
    return _png(fig)


def burbujas(items: list[tuple[str, int, float | None]]) -> bytes:
    """Cada tipo de requerimiento es una burbuja: a la derecha más volumen, arriba más oportunidad; el área es su total."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    maximo = max(v for _, v, _ in items) or 1
    desplazamientos = [(8, 8), (8, -12), (-8, 10), (-8, -14)]
    for i, (nombre, volumen, oportunidad) in enumerate(sorted(items, key=lambda x: -x[1])):
        if volumen <= 0:
            continue
        y = (oportunidad or 0) * 100
        ax.scatter(
            [volumen],
            [y],
            s=60 + 1400 * volumen / maximo,
            color=AZUL,
            alpha=0.75,
            edgecolors="white",
            linewidths=1,
            zorder=3,
        )
        dx, dy = desplazamientos[i % 4]
        ax.annotate(
            f"{nombre_propio(nombre)} ({entero(volumen)})",
            (volumen, y),
            textcoords="offset points",
            xytext=(dx, dy),
            ha="left" if dx > 0 else "right",
            fontsize=7,
            color=TINTA,
        )
    ax.set_xscale("log")
    ax.set_xlabel("PQRSDF gestionadas (escala logarítmica)", fontsize=8, color=GRIS)
    ax.set_ylabel("Oportunidad", fontsize=8, color=GRIS)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: _miles(v)))
    ax.set_ylim(-5, 112)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(FILETE)
    _ejes_sin_y(ax)
    return _png(fig)


def flujos(items: list[tuple[str, int, int]]) -> bytes:
    """Barras horizontales apiladas por tipo: a tiempo (azul) y extemporáneas (rojo), con la oportunidad al final."""
    preparar()
    n = len(items)
    fig, ax = plt.subplots(figsize=(8, max(1.8, 0.6 + 0.36 * n)))
    nombres = [nombre_propio(k) for k, _, _ in items][::-1]
    at = [a for _, a, _ in items][::-1]
    ex = [e for _, _, e in items][::-1]
    y = list(range(n))
    ax.barh(y, at, color=AZUL, height=0.62, label="A tiempo", zorder=3)
    ax.barh(y, ex, left=at, color=ROJO, height=0.62, label="Extemporáneas", zorder=3)
    for yi, (a, e) in zip(y, zip(at, ex, strict=True), strict=True):
        ax.annotate(
            f"{entero(a + e)} · {porcentaje(a / (a + e) if a + e else None, 1)} a tiempo",
            (a + e, yi),
            textcoords="offset points",
            xytext=(4, 0),
            va="center",
            fontsize=7.5,
            color=TINTA,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(nombres, fontsize=8)
    ax.set_xlim(0, max(a + e for a, e in zip(at, ex, strict=True)) * 1.45)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.legend(loc="lower right", ncol=2)
    _ejes_sin_y(ax)
    return _png(fig)


def pareto(items: list[tuple[str, int]], umbral: float = 0.8, maximo: int = 60) -> bytes:
    """Los ejes de mayor a menor volumen (columnas, hasta `maximo`) con la participación acumulada sobre el total de todos (línea) y la referencia del 80 %."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    total = sum(v for _, v in items) or 1
    items = items[:maximo]
    valores = [v for _, v in items]
    acumulado = []
    suma = 0
    for v in valores:
        suma += v
        acumulado.append(suma / total * 100)
    x = list(range(len(valores)))
    ax.bar(x, valores, color=AZUL, width=0.7, zorder=3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_miles))
    ax.set_ylim(0, max(valores) * 1.2)
    marcas = [i for i in x if (i + 1) % 10 == 0 or i == 0]
    ax.set_xticks(marcas)
    ax.set_xticklabels([str(i + 1) for i in marcas], fontsize=7.5)
    ax.set_xlabel(
        f"Ejes temáticos de mayor a menor volumen (posición; se muestran los primeros {len(items)})",
        fontsize=8,
        color=GRIS,
    )
    _ejes_sin_y(ax)
    eje2 = ax.twinx()
    eje2.plot(x, acumulado, color=NOCHE, linewidth=2, marker="o", markersize=3, zorder=4)
    eje2.axhline(umbral * 100, color=AMARILLO, linestyle="--", linewidth=1.2)
    eje2.annotate(
        f"{entero(umbral * 100)} % del volumen",
        (0, umbral * 100),
        textcoords="offset points",
        xytext=(2, 4),
        fontsize=7.5,
        color=GRIS,
    )
    eje2.set_ylim(0, 110)
    eje2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    eje2.spines["top"].set_visible(False)
    eje2.spines["right"].set_visible(False)
    eje2.tick_params(axis="y", length=0)
    return _png(fig)


def mezcla_canales(canal_por_mes: list[tuple[str, list[tuple[str, Totales]]]]) -> bytes:
    """Columnas al 100 % por mes con la parte de cada canal de radicación."""
    preparar()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    canales = []
    for _, lista in canal_por_mes:
        for k, _ in lista:
            if k not in canales:
                canales.append(k)
    canales.sort(key=lambda k: -sum(t.radicados for _, lista in canal_por_mes for kk, t in lista if kk == k))
    x = list(range(len(canal_por_mes)))
    base = [0.0] * len(x)
    for canal in canales:
        partes = []
        for _, lista in canal_por_mes:
            total = sum(t.radicados for _, t in lista) or 1
            partes.append(sum(t.radicados for k, t in lista if k == canal) / total * 100)
        ax.bar(
            x,
            partes,
            bottom=base,
            color=PALETA_CANALES.get(canal, GRIS_TENUE),
            width=0.62,
            label=nombre_propio(canal) if canal != "sin informacion" else "Sin información",
            zorder=3,
        )
        for xi, (b, v) in enumerate(zip(base, partes, strict=True)):
            if v >= 8:
                ax.text(
                    xi,
                    b + v / 2,
                    f"{decimal(v, 1)} %",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                )
        base = [b + v for b, v in zip(base, partes, strict=True)]
    ax.set_xticks(x)
    ax.set_xticklabels(_etiquetas(canal_por_mes))
    ax.set_ylim(0, 118)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{entero(v)} %"))
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.legend(loc="upper left", ncol=len(canales), bbox_to_anchor=(0, 1.1))
    _ejes_sin_y(ax)
    return _png(fig)
