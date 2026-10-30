"""Los datos del Informe de Legalizaciones en PDF: se leen de los agregados exportados en api/v1 (el cubo de
legalizaciones, las dimensiones y el plazo de oportunidad), los mismos que lee el informe interactivo, y se suman con
sus mismas reglas. La unidad es el documento radicado para legalizar, contado en su mes de radicación; el resultado
sale solo del estado de la fuente (legalizado, cancelado o en curso al corte); la tasa de legalización es legalizadas
sobre legalizadas más canceladas (lo en curso no cuenta); la oportunidad se mide solo sobre lo efectivamente
legalizado, con el plazo de días hábiles de ref.parametro (a tiempo hasta el plazo, extemporánea después); y los días
van de la radicación a la fecha del resultado, en calendario y en hábiles. «Finalizadas» nunca se muestra aparte de
«legalizadas»: para el negocio son lo mismo."""

from __future__ import annotations

import calendar
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from men_platform.publicaciones.datos_pqrsdf import mismo_mes_anio_anterior, periodo_anterior
from men_platform.publicaciones.datos_tramites import cuantos_para
from men_platform.publicaciones.texto_es import capitalizar

PLAZO_POR_DEFECTO = 3
PARETO = 0.8
LEGALIZADO, CANCELADO, EN_CURSO = 1, 2, 3
COLUMNAS_HABILES = [f"habiles_{i}" for i in range(16)] + ["habiles_mas_15"]
ETIQUETAS_HABILES = [str(i) for i in range(16)] + ["más de 15"]
COLUMNAS_RANGOS = ["dias_0_1", "dias_2_3", "dias_4_5", "dias_6_10", "dias_11_15", "dias_16_30", "dias_mas_30"]
NOMBRES_RANGOS = [
    "0 a 1 días",
    "2 a 3 días",
    "4 a 5 días",
    "6 a 10 días",
    "11 a 15 días",
    "16 a 30 días",
    "Más de 30 días",
]
NOMBRES_RESULTADO = {LEGALIZADO: "Legalizadas", CANCELADO: "Canceladas", EN_CURSO: "En curso"}

# Los nombres de pantalla de las metodologías (el nivel académico o tipo de trámite con que el sistema clasifica cada
# documento), con sus tildes y siglas.
NOMBRES_METODOLOGIA: dict[str, str] = {
    "pregrado": "Pregrado",
    "maestria": "Maestría",
    "especializacion": "Especialización",
    "tecnologo": "Tecnólogo",
    "tecnico profesional": "Técnico profesional",
    "certificacion": "Certificación",
    "doctorado": "Doctorado",
    "documento men": "Documento MEN",
    "resolucion": "Resolución",
    "distincion": "Distinción",
    "normalista": "Normalista",
    "sin homologar": "Sin homologar",
}
# Las palabras de los tipos de documento que la fuente trae sin tilde.
_TILDES_DOCUMENTO: dict[str, str] = {
    "programatico": "programático",
    "practicas": "prácticas",
    "convalidacion": "convalidación",
    "culminacion": "culminación",
    "aprobacion": "aprobación",
    "enfasis": "énfasis",
    "mencion": "mención",
    "certificacion": "certificación",
    "resolucion": "resolución",
    "esta": "está",
    "academico": "académico",
    "tecnico": "técnico",
    "tecnologo": "tecnólogo",
    "titulo": "título",
    "ies": "IES",
    "men": "MEN",
}


def nombre_documento(fuente: str) -> str:
    """«certificado de rotatorio y/o practicas» → «Certificado de rotatorio y/o prácticas»."""
    con_tildes = re.sub(r"[a-z]+", lambda m: _TILDES_DOCUMENTO.get(m.group(0), m.group(0)), fuente)
    return capitalizar(con_tildes)


@dataclass(frozen=True)
class Categoria:
    """Una metodología o un tipo de documento del catálogo."""

    id: int
    fuente: str  # el nombre tal como viene en el catálogo (minúscula, sin tildes)
    clase: str  # «metodologia» o «documento»

    @property
    def nombre(self) -> str:
        if self.clase == "metodologia":
            return NOMBRES_METODOLOGIA.get(self.fuente) or capitalizar(self.fuente)
        return nombre_documento(self.fuente)

    @property
    def bajo(self) -> str:
        """El nombre dentro de una frase: en minúscula salvo las siglas."""
        nombre = self.nombre
        return nombre if nombre[:1].isupper() and nombre[1:2].isupper() else nombre[:1].lower() + nombre[1:]


@dataclass
class Medidas:
    """Las sumas de un conjunto de filas del cubo y las razones que salen de ellas."""

    radicadas: int = 0
    legalizadas: int = 0
    canceladas: int = 0
    en_curso: int = 0
    con_complementacion: int = 0
    con_validacion_ies: int = 0
    # de los documentos con resultado (legalizados y cancelados): cuántos tienen fecha y sus días
    con_dias: int = 0
    dias_suma: int = 0
    dias_habiles_suma: int = 0
    rangos: list[int] = field(default_factory=lambda: [0] * len(COLUMNAS_RANGOS))
    # solo de las legalizadas: la distribución por días hábiles de gestión y sus días
    habiles: list[int] = field(default_factory=lambda: [0] * len(COLUMNAS_HABILES))
    legalizadas_con_dias: int = 0
    legalizadas_dias_suma: int = 0
    legalizadas_dias_habiles_suma: int = 0
    a_tiempo: int = 0
    extemporaneas: int = 0

    def sumar(self, otra: Medidas) -> None:
        for campo in (
            "radicadas",
            "legalizadas",
            "canceladas",
            "en_curso",
            "con_complementacion",
            "con_validacion_ies",
            "con_dias",
            "dias_suma",
            "dias_habiles_suma",
            "legalizadas_con_dias",
            "legalizadas_dias_suma",
            "legalizadas_dias_habiles_suma",
            "a_tiempo",
            "extemporaneas",
        ):
            setattr(self, campo, getattr(self, campo) + getattr(otra, campo))
        self.rangos = [a + b for a, b in zip(self.rangos, otra.rangos, strict=True)]
        self.habiles = [a + b for a, b in zip(self.habiles, otra.habiles, strict=True)]

    @property
    def con_resultado(self) -> int:
        return self.legalizadas + self.canceladas

    @property
    def tasa_legalizacion(self) -> float | None:
        return self.legalizadas / self.con_resultado if self.con_resultado else None

    @property
    def legalizadas_con_fecha(self) -> int:
        return self.a_tiempo + self.extemporaneas

    @property
    def oportunidad(self) -> float | None:
        return self.a_tiempo / self.legalizadas_con_fecha if self.legalizadas_con_fecha else None

    @property
    def participacion_en_curso(self) -> float | None:
        return self.en_curso / self.radicadas if self.radicadas else None

    @property
    def promedio_dias(self) -> float | None:
        return self.dias_suma / self.con_dias if self.con_dias else None

    @property
    def promedio_dias_habiles(self) -> float | None:
        return self.dias_habiles_suma / self.con_dias if self.con_dias else None

    @property
    def promedio_dias_legalizadas(self) -> float | None:
        return self.legalizadas_dias_suma / self.legalizadas_con_dias if self.legalizadas_con_dias else None

    @property
    def promedio_dias_habiles_legalizadas(self) -> float | None:
        return self.legalizadas_dias_habiles_suma / self.legalizadas_con_dias if self.legalizadas_con_dias else None

    @property
    def tasa_complementacion(self) -> float | None:
        return self.con_complementacion / self.radicadas if self.radicadas else None

    @property
    def tasa_validacion_ies(self) -> float | None:
        return self.con_validacion_ies / self.radicadas if self.radicadas else None

    @property
    def hasta_cinco_dias(self) -> float | None:
        """La parte de los documentos con resultado que se resolvió en cinco días calendario o menos."""
        return sum(self.rangos[:3]) / self.con_dias if self.con_dias else None

    @property
    def mas_de_quince_dias(self) -> float | None:
        return sum(self.rangos[5:]) / self.con_dias if self.con_dias else None


@dataclass(frozen=True)
class Fila:
    periodo: str  # AAAA-MM-01
    metodologia_id: int
    tipo_documento_id: int
    resultado_id: int
    medidas: Medidas


@dataclass
class Fuente:
    periodo_maximo: str
    periodo_minimo: str
    fecha_corte: str
    publicado_en: str
    actualizacion_id: int
    version_pipeline: str
    plazo: int  # días hábiles de oportunidad (ref.parametro)
    metodologias: dict[int, Categoria]
    documentos: dict[int, Categoria]
    por_periodo: dict[str, list[Fila]]
    periodos: list[str]  # los meses con documentos radicados


def sumar(filas: Iterable[Fila]) -> Medidas:
    total = Medidas()
    for f in filas:
        total.sumar(f.medidas)
    return total


def _medidas_de(fila: list, col: dict[str, int], plazo: int) -> Medidas:
    """Las medidas de una fila del cubo: el resultado repartido en medidas, los días de los documentos con resultado y,
    solo si la fila es de legalizadas, la distribución por días hábiles con lo a tiempo (hasta el plazo) y lo
    extemporáneo (después)."""
    cantidad = int(fila[col["cantidad"]] or 0)
    resultado = int(fila[col["resultado_id"]])
    legalizada = resultado == LEGALIZADO

    def n(columna: str) -> int:
        return int(fila[col[columna]] or 0) if columna in col else 0

    habiles = [n(c) for c in COLUMNAS_HABILES] if legalizada else [0] * len(COLUMNAS_HABILES)
    # hasta el plazo cuenta como a tiempo; «más de 15» entra solo si el plazo pasa de quince días hábiles
    hasta_plazo = min(max(0, plazo), 15) + 1 + (1 if plazo > 15 else 0)
    a_tiempo = sum(habiles[:hasta_plazo])
    con_dias = n("con_dias")
    return Medidas(
        radicadas=cantidad,
        legalizadas=cantidad if legalizada else 0,
        canceladas=cantidad if resultado == CANCELADO else 0,
        en_curso=cantidad if resultado == EN_CURSO else 0,
        con_complementacion=n("con_complementacion"),
        con_validacion_ies=n("con_validacion_ies"),
        con_dias=con_dias,
        dias_suma=n("dias_suma"),
        dias_habiles_suma=n("dias_habiles_suma"),
        rangos=[n(c) for c in COLUMNAS_RANGOS],
        habiles=habiles,
        legalizadas_con_dias=con_dias if legalizada else 0,
        legalizadas_dias_suma=n("dias_suma") if legalizada else 0,
        legalizadas_dias_habiles_suma=n("dias_habiles_suma") if legalizada else 0,
        a_tiempo=a_tiempo,
        extemporaneas=sum(habiles) - a_tiempo,
    )


def cargar(ruta_api: Path) -> Fuente:
    resumen = json.loads((ruta_api / "legalizaciones" / "resumen.json").read_text(encoding="utf-8"))
    cubo = json.loads((ruta_api / "legalizaciones" / "cubo.json").read_text(encoding="utf-8"))
    dimensiones = json.loads((ruta_api / "dimensiones.json").read_text(encoding="utf-8"))
    parametros = dimensiones.get("parametros") or {}
    try:
        plazo = int(float(parametros.get("legalizacion_dias_habiles_oportunidad", PLAZO_POR_DEFECTO)))
    except (TypeError, ValueError):
        plazo = PLAZO_POR_DEFECTO
    metodologias = {
        int(d["id"]): Categoria(int(d["id"]), str(d["nombre"]), "metodologia")
        for d in dimensiones.get("legalizaciones_metodologias", [])
    }
    documentos = {
        int(d["id"]): Categoria(int(d["id"]), str(d["nombre"]), "documento")
        for d in dimensiones.get("legalizaciones_tipos_documento", [])
    }
    col = {c: i for i, c in enumerate(cubo["columnas"])}
    por_periodo: dict[str, list[Fila]] = {}
    for f in cubo["filas"]:
        medidas = _medidas_de(f, col, plazo)
        if medidas.radicadas <= 0:
            continue
        periodo = str(f[col["periodo"]])[:10]
        por_periodo.setdefault(periodo, []).append(
            Fila(
                periodo,
                int(f[col["metodologia_id"]]),
                int(f[col["tipo_documento_id"]]),
                int(f[col["resultado_id"]]),
                medidas,
            )
        )
    return Fuente(
        periodo_maximo=resumen["periodo_maximo"][:10],
        periodo_minimo=resumen["periodo_minimo"][:10],
        fecha_corte=resumen["fecha_corte_maxima"][:10],
        publicado_en=resumen["publicado_en"],
        actualizacion_id=int(resumen["actualizacion_id"]),
        version_pipeline=resumen.get("version_pipeline", ""),
        plazo=plazo,
        metodologias=metodologias,
        documentos=documentos,
        por_periodo=por_periodo,
        periodos=sorted(por_periodo),
    )


@dataclass
class Calculo:
    periodo: str
    fecha_corte: str
    publicado_en: str
    actualizacion_id: int
    version_pipeline: str
    primer_periodo: str
    plazo: int
    mes: Medidas
    periodo_anterior: str | None
    mes_anterior: Medidas | None
    mismo_mes_anterior: Medidas | None
    acumulado: Medidas  # de enero al mes del informe
    meses_acumulado: int
    acumulado_anterior: Medidas | None  # los mismos meses del año anterior
    meses_acumulado_anterior: int
    serie_completa: list[tuple[str, Medidas]]  # todos los meses hasta el del informe
    serie_anio: list[tuple[str, Medidas]]
    serie_anio_anterior: list[tuple[str, Medidas]]  # todos los meses del año anterior
    serie_13: list[tuple[str, Medidas]]
    media_movil_radicadas: dict[str, float | None]  # simple: promedio de los tres meses anteriores
    media_movil_oportunidad: dict[str, float | None]  # ponderada: a tiempo de tres meses sobre sus legalizadas
    matriz_oportunidad: dict[int, dict[int, float | None]]  # año → mes → % de oportunidad
    metodologias_mes: list[tuple[Categoria, Medidas]]  # con radicadas en el mes, de mayor a menor
    documentos_mes: list[tuple[Categoria, Medidas]]
    metodologias_anio: list[tuple[Categoria, Medidas]]  # de enero al mes del informe, de mayor a menor
    documentos_anio: list[tuple[Categoria, Medidas]]
    metodologias_anio_anterior: dict[int, Medidas]  # los mismos meses del año anterior
    documentos_anio_anterior: dict[int, Medidas]
    metodologias_mes_anterior: dict[int, Medidas]
    metodologia_por_mes: list[tuple[str, dict[int, int]]]  # radicadas por metodología en cada mes del año

    @property
    def anio(self) -> int:
        return int(self.periodo[:4])

    @property
    def mes_numero(self) -> int:
        return int(self.periodo[5:7])

    def participacion(self, m: Medidas) -> float | None:
        return m.radicadas / self.mes.radicadas if self.mes.radicadas else None

    def participacion_anio(self, m: Medidas) -> float | None:
        return m.radicadas / self.acumulado.radicadas if self.acumulado.radicadas else None

    @property
    def promedio_mensual(self) -> float | None:
        return self.acumulado.radicadas / self.meses_acumulado if self.meses_acumulado else None

    @property
    def promedio_anterior(self) -> float | None:
        if self.acumulado_anterior is None or not self.meses_acumulado_anterior:
            return None
        return self.acumulado_anterior.radicadas / self.meses_acumulado_anterior

    @property
    def mes_mayor(self) -> tuple[str, int] | None:
        return max(((p, m.radicadas) for p, m in self.serie_anio), key=lambda pv: pv[1]) if self.serie_anio else None

    @property
    def mes_menor(self) -> tuple[str, int] | None:
        return min(((p, m.radicadas) for p, m in self.serie_anio), key=lambda pv: pv[1]) if self.serie_anio else None

    def cuantas_para_pareto(self, grupos: list[tuple[Categoria, Medidas]]) -> int:
        return cuantos_para([m.radicadas for _, m in grupos], PARETO)


def _por_categoria(
    filas: Iterable[Fila], clase: str, catalogo: dict[int, Categoria]
) -> list[tuple[Categoria, Medidas]]:
    """Las filas sumadas por metodología o por tipo de documento, de mayor a menor radicadas; solo las que tienen."""
    grupos: dict[int, Medidas] = {}
    for f in filas:
        id_ = f.metodologia_id if clase == "metodologia" else f.tipo_documento_id
        grupos.setdefault(id_, Medidas()).sumar(f.medidas)
    salida = [
        (catalogo.get(id_, Categoria(id_, "sin homologar", clase)), m) for id_, m in grupos.items() if m.radicadas > 0
    ]
    salida.sort(key=lambda cm: (-cm[1].radicadas, cm[0].id))
    return salida


def calcular(fuente: Fuente, periodo: str) -> Calculo:
    if periodo not in fuente.por_periodo:
        raise ValueError(f"no hay legalizaciones radicadas en {periodo[:7]}")
    anio = periodo[:4]
    anio_ant = str(int(anio) - 1)
    periodos = [p for p in fuente.periodos if p <= periodo]
    serie_completa = [(p, sumar(fuente.por_periodo[p])) for p in periodos]
    serie_anio = [(p, m) for p, m in serie_completa if p[:4] == anio]
    serie_anio_anterior = [(p, sumar(fuente.por_periodo[p])) for p in fuente.periodos if p[:4] == anio_ant]
    mes = serie_completa[-1][1]
    p_ant = periodo_anterior(periodo)
    mes_anterior = sumar(fuente.por_periodo[p_ant]) if p_ant in fuente.por_periodo else None
    p_mismo = mismo_mes_anio_anterior(periodo)
    mismo = sumar(fuente.por_periodo[p_mismo]) if p_mismo in fuente.por_periodo else None
    filas_anio = [f for p, _ in serie_anio for f in fuente.por_periodo[p]]
    meses_anio = {p[5:7] for p, _ in serie_anio}
    periodos_previos = [p for p, _ in serie_anio_anterior if p[5:7] in meses_anio]
    filas_previas = [f for p in periodos_previos for f in fuente.por_periodo[p]]
    # medias móviles sobre toda la serie: la de radicadas, simple; la de oportunidad, ponderada por las legalizadas
    media_radicadas: dict[str, float | None] = {}
    media_oportunidad: dict[str, float | None] = {}
    for i, (p, _) in enumerate(serie_completa):
        anteriores = serie_completa[max(0, i - 3) : i]
        if len(anteriores) < 3:
            media_radicadas[p] = None
            media_oportunidad[p] = None
            continue
        media_radicadas[p] = sum(m.radicadas for _, m in anteriores) / 3
        con_fecha = sum(m.legalizadas_con_fecha for _, m in anteriores)
        media_oportunidad[p] = sum(m.a_tiempo for _, m in anteriores) / con_fecha if con_fecha else None
    # el mapa de calor: todos los años del histórico; el del informe, hasta su mes
    matriz: dict[int, dict[int, float | None]] = {}
    for p in fuente.periodos:
        if p > periodo:
            continue
        matriz.setdefault(int(p[:4]), {})[int(p[5:7])] = sumar(fuente.por_periodo[p]).oportunidad
    metodologia_por_mes = []
    for p, _ in serie_anio:
        por_met: dict[int, int] = {}
        for f in fuente.por_periodo[p]:
            por_met[f.metodologia_id] = por_met.get(f.metodologia_id, 0) + f.medidas.radicadas
        metodologia_por_mes.append((p, por_met))
    return Calculo(
        periodo=periodo,
        fecha_corte=periodo[:8] + str(calendar.monthrange(int(anio), int(periodo[5:7]))[1]),
        publicado_en=fuente.publicado_en,
        actualizacion_id=fuente.actualizacion_id,
        version_pipeline=fuente.version_pipeline,
        primer_periodo=fuente.periodo_minimo,
        plazo=fuente.plazo,
        mes=mes,
        periodo_anterior=p_ant if mes_anterior is not None else None,
        mes_anterior=mes_anterior,
        mismo_mes_anterior=mismo,
        acumulado=sumar(filas_anio),
        meses_acumulado=len(serie_anio),
        acumulado_anterior=sumar(filas_previas) if periodos_previos else None,
        meses_acumulado_anterior=len(periodos_previos),
        serie_completa=serie_completa,
        serie_anio=serie_anio,
        serie_anio_anterior=serie_anio_anterior,
        serie_13=serie_completa[-13:],
        media_movil_radicadas=media_radicadas,
        media_movil_oportunidad=media_oportunidad,
        matriz_oportunidad=matriz,
        metodologias_mes=_por_categoria(fuente.por_periodo[periodo], "metodologia", fuente.metodologias),
        documentos_mes=_por_categoria(fuente.por_periodo[periodo], "documento", fuente.documentos),
        metodologias_anio=_por_categoria(filas_anio, "metodologia", fuente.metodologias),
        documentos_anio=_por_categoria(filas_anio, "documento", fuente.documentos),
        metodologias_anio_anterior={
            c.id: m for c, m in _por_categoria(filas_previas, "metodologia", fuente.metodologias)
        },
        documentos_anio_anterior={c.id: m for c, m in _por_categoria(filas_previas, "documento", fuente.documentos)},
        metodologias_mes_anterior=(
            {c.id: m for c, m in _por_categoria(fuente.por_periodo[p_ant], "metodologia", fuente.metodologias)}
            if mes_anterior is not None
            else {}
        ),
        metodologia_por_mes=metodologia_por_mes,
    )
