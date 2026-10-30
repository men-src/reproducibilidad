"""Los números del Informe General de PQRSDF de un mes, calculados desde los cubos exportados en api/v1 (vencimiento,
radicación y ejes temáticos) con las mismas reglas del informe web: oportunidad = a tiempo sobre total (BR-007); las
extemporáneas incluyen las abiertas ya vencidas (BR-010); promedio de días hábiles de gestión sobre radicados y de
retraso sobre extemporáneas; y por radicación lo «a gestionar» que no está extemporáneo cuenta como a tiempo (D-61)."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

ESTADO_A_TIEMPO = 1
ESTADO_EXTEMPORANEA = 2
ESTADO_ABIERTA_EN_TERMINO = 3
ESTADO_ABIERTA_VENCIDA = 4
PRIMER_PERIODO_CON_CANAL = "2024-01-01"


def _razon(numerador: float, denominador: float) -> float | None:
    return numerador / denominador if denominador else None


@dataclass
class Totales:
    """Sumas de un conjunto de filas del cubo y las razones que salen de ellas."""

    radicados: int = 0
    cerradas: int = 0
    a_tiempo: int = 0
    extemporaneas: int = 0
    abiertas_en_termino: int = 0
    abiertas_vencidas: int = 0
    dias_gestion: int = 0
    dias_retraso: int = 0
    con_respuesta: int = 0
    a_gestionar_mes: int = 0
    a_gestionar_mes_extemporaneas: int = 0
    a_gestionar_trimestre: int = 0
    a_gestionar_trimestre_extemporaneas: int = 0

    @property
    def oportunidad(self) -> float | None:
        return _razon(self.a_tiempo, self.radicados)

    @property
    def tasa_extemporaneas(self) -> float | None:
        return _razon(self.extemporaneas, self.radicados)

    @property
    def abiertas(self) -> int:
        return self.abiertas_en_termino + self.abiertas_vencidas

    @property
    def promedio_dias_gestion(self) -> float | None:
        return _razon(self.dias_gestion, self.radicados)

    @property
    def promedio_dias_retraso(self) -> float | None:
        return _razon(self.dias_retraso, self.extemporaneas)

    @property
    def a_gestionar_mes_a_tiempo(self) -> int:
        return self.a_gestionar_mes - self.a_gestionar_mes_extemporaneas

    @property
    def a_gestionar_trimestre_a_tiempo(self) -> int:
        return self.a_gestionar_trimestre - self.a_gestionar_trimestre_extemporaneas

    @property
    def oportunidad_gestion_mes(self) -> float | None:
        return _razon(self.a_gestionar_mes_a_tiempo, self.a_gestionar_mes)

    @property
    def oportunidad_gestion_trimestre(self) -> float | None:
        return _razon(self.a_gestionar_trimestre_a_tiempo, self.a_gestionar_trimestre)

    @property
    def participacion_gestion_mes(self) -> float | None:
        return _razon(self.a_gestionar_mes, self.radicados)

    @property
    def participacion_gestion_trimestre(self) -> float | None:
        return _razon(self.a_gestionar_trimestre, self.radicados)


@dataclass(frozen=True)
class Dependencia:
    sk: int
    unidad: str
    es_grupo: bool
    grupo: str
    dependencia: str
    viceministerio: str


@dataclass
class Dimensiones:
    dependencias: dict[int, Dependencia]
    tipos: dict[int, str]
    canales: dict[int, str]
    ejes: dict[int, str]
    periodos: list[str]


@dataclass
class Cubo:
    """Un cubo exportado: las columnas, las filas como tuplas y un índice por periodo."""

    base: str
    columnas: dict[str, int]
    filas: list[tuple]
    por_periodo: dict[str, list[tuple]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        i = self.columnas["periodo"]
        agrupado: dict[str, list[tuple]] = defaultdict(list)
        for fila in self.filas:
            agrupado[fila[i]].append(fila)
        self.por_periodo = dict(agrupado)

    def columna(self, nombre: str) -> int | None:
        return self.columnas.get(nombre)

    def entre(self, desde: str, hasta: str) -> list[tuple]:
        return [f for p, filas in self.por_periodo.items() if desde <= p <= hasta for f in filas]


@dataclass
class Fuente:
    """Todo lo exportado que necesita el informe de PQRSDF."""

    dimensiones: Dimensiones
    vencimiento: Cubo
    radicacion: Cubo
    ejes: Cubo
    pronostico: dict[str, float]
    modelo_pronostico: str
    actualizacion_id: int
    publicado_en: str
    fecha_corte: str
    periodo_maximo: str
    version_pipeline: str


def _leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def _cubo(ruta: Path) -> Cubo:
    j = _leer_json(ruta)
    return Cubo(
        base=j["base"], columnas={c: i for i, c in enumerate(j["columnas"])}, filas=[tuple(f) for f in j["filas"]]
    )


def cargar(ruta_api: Path) -> Fuente:
    """Lee api/v1: dimensiones, los cubos de PQRSDF, el pronóstico y el manifiesto."""
    d = _leer_json(ruta_api / "dimensiones.json")
    dependencias = {
        int(x["sk"]): Dependencia(
            int(x["sk"]), x["unidad"], bool(x["es_grupo"]), x["grupo"], x["dependencia"], x["viceministerio"]
        )
        for x in d["dependencias"]
    }
    dimensiones = Dimensiones(
        dependencias=dependencias,
        tipos={int(x["id"]): x["nombre"] for x in d["tipos_requerimiento"]},
        canales={int(x["id"]): x["nombre"] for x in d["canales"]},
        ejes={int(x["id"]): x["nombre"] for x in d["ejes_tematicos"]},
        periodos=sorted(x["periodo"] for x in d["periodos"]),
    )
    pron = _leer_json(ruta_api / "vencimiento" / "pronostico.json")
    resumen = _leer_json(ruta_api / "vencimiento" / "resumen.json")
    return Fuente(
        dimensiones=dimensiones,
        vencimiento=_cubo(ruta_api / "vencimiento" / "cubo.json"),
        radicacion=_cubo(ruta_api / "radicacion" / "cubo.json"),
        ejes=_cubo(ruta_api / "vencimiento" / "cubo-ejes.json"),
        pronostico={p["periodo"][:10]: float(p["pronostico"]) for p in pron.get("puntos", [])},
        modelo_pronostico=str(pron.get("modelo", "sarima")),
        actualizacion_id=int(resumen["actualizacion_id"]),
        publicado_en=str(resumen["publicado_en"]),
        fecha_corte=str(resumen["fecha_corte_maxima"]),
        periodo_maximo=str(resumen["periodo_maximo"]),
        version_pipeline=str(resumen.get("version_pipeline", "")),
    )


def sumar(cubo: Cubo, filas: Iterable[tuple]) -> Totales:
    """Suma las filas de un cubo en un Totales; cada columna opcional se toma si existe."""
    c = cubo.columnas
    i_estado = c["estado_oportunidad_id"]
    i_rad, i_cer, i_ext = c["radicados"], c["cerradas"], c["extemporaneas"]
    i_dg, i_dr, i_cr = c.get("dias_habiles_gestion"), c.get("dias_habiles_retraso"), c.get("con_respuesta")
    i_gm, i_gt = c.get("a_gestionar_en_mes"), c.get("a_gestionar_en_trimestre")
    t = Totales()
    for f in filas:
        estado = f[i_estado]
        t.radicados += f[i_rad]
        t.cerradas += f[i_cer]
        t.extemporaneas += f[i_ext]
        if estado == ESTADO_ABIERTA_EN_TERMINO:
            t.abiertas_en_termino += f[i_rad]
        elif estado == ESTADO_ABIERTA_VENCIDA:
            t.abiertas_vencidas += f[i_rad]
        if i_dg is not None:
            t.dias_gestion += f[i_dg] or 0
        if i_dr is not None:
            t.dias_retraso += f[i_dr] or 0
        if i_cr is not None:
            t.con_respuesta += f[i_cr] or 0
        if i_gm is not None:
            t.a_gestionar_mes += f[i_gm] or 0
            if estado in (ESTADO_EXTEMPORANEA, ESTADO_ABIERTA_VENCIDA):
                t.a_gestionar_mes_extemporaneas += f[i_gm] or 0
        if i_gt is not None:
            t.a_gestionar_trimestre += f[i_gt] or 0
            if estado in (ESTADO_EXTEMPORANEA, ESTADO_ABIERTA_VENCIDA):
                t.a_gestionar_trimestre_extemporaneas += f[i_gt] or 0
    # D-40: el informe distingue dos estados; lo que no está tarde, incluidas las abiertas en término, cuenta como a
    # tiempo. Es la misma regla del informe interactivo (totalizar) y de la portada de la API, y no la columna a_tiempo
    # del cubo, que en la base por vencimiento deja fuera las abiertas en término (casos dorados PQ-02).
    t.a_tiempo = t.radicados - t.extemporaneas
    return t


def por_clave(cubo: Cubo, filas: Iterable[tuple], clave: Callable[[tuple], str]) -> list[tuple[str, Totales]]:
    """Agrupa filas por una clave y devuelve (clave, totales) de mayor a menor volumen."""
    grupos: dict[str, list[tuple]] = defaultdict(list)
    for f in filas:
        grupos[clave(f)].append(f)
    resultado = [(k, sumar(cubo, v)) for k, v in grupos.items()]
    resultado.sort(key=lambda kv: (-kv[1].radicados, kv[0]))
    return resultado


def periodo_anterior(periodo: str) -> str:
    anio, mes = int(periodo[:4]), int(periodo[5:7])
    return f"{anio - 1}-12-01" if mes == 1 else f"{anio}-{mes - 1:02d}-01"


def mismo_mes_anio_anterior(periodo: str) -> str:
    return f"{int(periodo[:4]) - 1}-{periodo[5:7]}-01"


def periodos_del_anio(periodo: str) -> tuple[str, str]:
    return f"{periodo[:4]}-01-01", periodo


@dataclass
class Calculo:
    """Todo lo que el informe de un mes escribe y dibuja."""

    periodo: str
    fecha_corte: str
    publicado_en: str
    actualizacion_id: int
    version_pipeline: str
    primer_periodo: str
    mes: Totales
    mes_anterior: Totales | None
    mismo_mes_anterior: Totales | None
    acumulado: Totales
    acumulado_anterior: Totales | None
    serie_13: list[tuple[str, Totales]]
    serie_anio: list[tuple[str, Totales]]
    serie_anio_anterior: list[tuple[str, Totales]]
    historico_anual: list[tuple[str, Totales]]
    por_viceministerio: list[tuple[str, Totales]]
    por_dependencia: list[tuple[str, Totales]]
    por_dependencia_acumulado: list[tuple[str, Totales]]
    por_dependencia_anterior: list[tuple[str, Totales]]
    por_grupo: list[tuple[str, Totales]]
    por_tipo: list[tuple[str, Totales]]
    por_tipo_acumulado: list[tuple[str, Totales]]
    por_canal: list[tuple[str, Totales]] | None
    por_eje: list[tuple[str, Totales]]
    radicacion_mes: Totales | None
    radicacion_acumulado: Totales | None
    radicacion_serie_anio: list[tuple[str, Totales]]
    pronostico: list[tuple[str, float | None, float]]
    modelo_pronostico: str
    serie_total: list[tuple[str, Totales]]
    media_movil_oportunidad: dict[str, float | None]
    media_movil_radicados: dict[str, float | None]
    media_movil_a_tiempo: dict[str, float | None]
    media_movil_extemporaneas: dict[str, float | None]
    matriz_oportunidad: dict[int, dict[int, float | None]]
    canal_por_mes: list[tuple[str, list[tuple[str, Totales]]]]
    tipos_por_canal: list[tuple[str, dict[str, int]]]
    total_dependencias_con_radicados: int = 0

    @property
    def anio(self) -> int:
        return int(self.periodo[:4])

    @property
    def mes_numero(self) -> int:
        return int(self.periodo[5:7])

    def periodo_anterior_str(self) -> str:
        return periodo_anterior(self.periodo)


def calcular(fuente: Fuente, periodo: str) -> Calculo:
    """Arma el cálculo del mes `periodo` ('AAAA-MM-01')."""
    if periodo not in fuente.vencimiento.por_periodo:
        raise ValueError(f"no hay datos de PQRSDF para el periodo {periodo}")
    dims = fuente.dimensiones
    cv, cr, ce = fuente.vencimiento, fuente.radicacion, fuente.ejes
    filas_mes = cv.por_periodo[periodo]
    inicio_anio, _ = periodos_del_anio(periodo)
    filas_acumulado = cv.entre(inicio_anio, periodo)

    def totales_de(cubo: Cubo, p: str) -> Totales | None:
        return sumar(cubo, cubo.por_periodo[p]) if p in cubo.por_periodo else None

    def serie(cubo: Cubo, desde: str, hasta: str) -> list[tuple[str, Totales]]:
        return [
            (p, sumar(cubo, cubo.por_periodo[p]))
            for p in dims.periodos
            if desde <= p <= hasta and p in cubo.por_periodo
        ]

    anterior = periodo_anterior(periodo)
    mismo = mismo_mes_anio_anterior(periodo)
    inicio_anterior = f"{int(periodo[:4]) - 1}-01-01"
    acumulado_anterior = sumar(cv, cv.entre(inicio_anterior, mismo)) if mismo in cv.por_periodo else None

    # trece meses: del mismo mes del año anterior al mes del informe
    serie_13 = serie(cv, mismo, periodo)
    serie_anio = serie(cv, inicio_anio, periodo)
    serie_anio_anterior = serie(cv, inicio_anterior, f"{int(periodo[:4]) - 1}-12-01")
    historico = por_clave(cv, cv.entre(dims.periodos[0], periodo), lambda f: f[cv.columnas["periodo"]][:4])
    historico.sort(key=lambda kv: kv[0])

    i_dep, i_tipo, i_canal = (
        cv.columnas["dependencia_sk"],
        cv.columnas["tipo_requerimiento_id"],
        cv.columnas["canal_id"],
    )

    def dependencia(f: tuple) -> str:
        d = dims.dependencias.get(f[i_dep])
        return d.dependencia if d else "sin dependencia"

    def grupo(f: tuple) -> str:
        d = dims.dependencias.get(f[i_dep])
        if not d or not d.es_grupo:
            return ""
        return f"{d.unidad}|{d.dependencia}"

    def viceministerio(f: tuple) -> str:
        d = dims.dependencias.get(f[i_dep])
        return d.viceministerio if d else "sin viceministerio"

    por_grupo = [(k, t) for k, t in por_clave(cv, filas_mes, grupo) if k]
    i_eje = ce.columnas["eje_tematico_sk"]
    por_eje = por_clave(ce, ce.por_periodo.get(periodo, []), lambda f: dims.ejes.get(f[i_eje], "sin eje tematico"))

    por_canal = None
    if periodo >= PRIMER_PERIODO_CON_CANAL:
        por_canal = por_clave(cv, filas_mes, lambda f: dims.canales.get(f[i_canal], "sin informacion"))

    pron: list[tuple[str, float | None, float]] = []
    for p, valor in sorted(fuente.pronostico.items()):
        if p[:4] == periodo[:4] and p <= periodo:
            real = totales_de(cv, p)
            pron.append((p, real.oportunidad if real else None, valor))

    por_dependencia = por_clave(cv, filas_mes, dependencia)
    # la serie completa, las medias móviles de los tres meses anteriores (sin el mes evaluado) y la matriz mes × año
    serie_total = serie(cv, dims.periodos[0], periodo)
    mm_oportunidad: dict[str, float | None] = {}
    mm_radicados: dict[str, float | None] = {}
    mm_a_tiempo: dict[str, float | None] = {}
    mm_extemporaneas: dict[str, float | None] = {}
    for i, (p, _) in enumerate(serie_total):
        previos = [t for _, t in serie_total[max(0, i - 3) : i]]
        if len(previos) < 3:
            mm_oportunidad[p] = mm_radicados[p] = mm_a_tiempo[p] = mm_extemporaneas[p] = None
            continue
        total = sum(t.radicados for t in previos)
        mm_oportunidad[p] = sum(t.a_tiempo for t in previos) / total if total else None
        mm_radicados[p] = total / 3
        mm_a_tiempo[p] = sum(t.a_tiempo for t in previos) / 3
        mm_extemporaneas[p] = sum(t.extemporaneas for t in previos) / 3
    matriz: dict[int, dict[int, float | None]] = {}
    for p, t in serie_total:
        if int(p[5:7]) <= int(periodo[5:7]):
            matriz.setdefault(int(p[:4]), {})[int(p[5:7])] = t.oportunidad
    canal_por_mes = [
        (p, por_clave(cv, cv.por_periodo[p], lambda f: dims.canales.get(f[i_canal], "sin informacion")))
        for p, _ in serie_anio
        if p >= PRIMER_PERIODO_CON_CANAL
    ]
    tipos_por_canal: dict[str, dict[str, int]] = {}
    if periodo >= PRIMER_PERIODO_CON_CANAL:
        for f in filas_mes:
            tipo = dims.tipos.get(f[i_tipo], "sin homologar")
            canal = dims.canales.get(f[i_canal], "sin informacion")
            tipos_por_canal.setdefault(tipo, {})[canal] = (
                tipos_por_canal.setdefault(tipo, {}).get(canal, 0) + f[cv.columnas["radicados"]]
            )
    tipos_por_canal_lista = sorted(tipos_por_canal.items(), key=lambda kv: -sum(kv[1].values()))
    return Calculo(
        periodo=periodo,
        fecha_corte=fuente.fecha_corte if periodo == fuente.periodo_maximo else _fin_de_mes(periodo),
        publicado_en=fuente.publicado_en,
        actualizacion_id=fuente.actualizacion_id,
        version_pipeline=fuente.version_pipeline,
        primer_periodo=dims.periodos[0],
        mes=sumar(cv, filas_mes),
        mes_anterior=totales_de(cv, anterior),
        mismo_mes_anterior=totales_de(cv, mismo),
        acumulado=sumar(cv, filas_acumulado),
        acumulado_anterior=acumulado_anterior,
        serie_13=serie_13,
        serie_anio=serie_anio,
        serie_anio_anterior=serie_anio_anterior,
        historico_anual=historico,
        por_viceministerio=por_clave(cv, filas_mes, viceministerio),
        por_dependencia=por_dependencia,
        por_dependencia_acumulado=por_clave(cv, filas_acumulado, dependencia),
        por_dependencia_anterior=por_clave(cv, cv.por_periodo.get(anterior, []), dependencia),
        por_grupo=por_grupo,
        por_tipo=por_clave(cv, filas_mes, lambda f: dims.tipos.get(f[i_tipo], "sin homologar")),
        por_tipo_acumulado=por_clave(cv, filas_acumulado, lambda f: dims.tipos.get(f[i_tipo], "sin homologar")),
        por_canal=por_canal,
        por_eje=por_eje,
        radicacion_mes=totales_de(cr, periodo),
        radicacion_acumulado=sumar(cr, cr.entre(inicio_anio, periodo)) if periodo in cr.por_periodo else None,
        radicacion_serie_anio=serie(cr, inicio_anio, periodo),
        pronostico=pron,
        modelo_pronostico=fuente.modelo_pronostico,
        serie_total=serie_total,
        media_movil_oportunidad=mm_oportunidad,
        media_movil_radicados=mm_radicados,
        media_movil_a_tiempo=mm_a_tiempo,
        media_movil_extemporaneas=mm_extemporaneas,
        matriz_oportunidad=matriz,
        canal_por_mes=canal_por_mes,
        tipos_por_canal=tipos_por_canal_lista,
        total_dependencias_con_radicados=sum(1 for _, t in por_dependencia if t.radicados > 0),
    )


def _fin_de_mes(periodo: str) -> str:
    """Último día del mes de un periodo 'AAAA-MM-01'."""
    import calendar

    anio, mes = int(periodo[:4]), int(periodo[5:7])
    return f"{anio}-{mes:02d}-{calendar.monthrange(anio, mes)[1]:02d}"
