"""Los datos del Informe de Trámites en PDF: se leen de los agregados exportados en api/v1 (el cubo de trámites y la
dimensión de tipos), los mismos que lee el informe interactivo (D-56), y se suman con sus mismas reglas: la fuente trae
un total por mes y tipo de trámite, sin oportunidad ni estados, así que todo es volumen. El total general de un mes es
la suma de sus tipos; el promedio mensual es el total sobre los meses con datos; cada tipo se mira en sus meses con
datos, porque no todos existen todo el tiempo (los certificados van hasta noviembre de 2025, las convalidaciones de
básica hasta julio de 2024 y las citas virtuales desde septiembre de 2024); un tipo sin datos en el año del informe no entra en
él (pedido del patrocinador, 2026-10-29)."""

from __future__ import annotations

import calendar
import json
from dataclasses import dataclass, field
from pathlib import Path

from men_platform.publicaciones.datos_pqrsdf import mismo_mes_anio_anterior, periodo_anterior
from men_platform.publicaciones.texto_es import capitalizar

# Los nombres de pantalla de los tipos de trámite (los mismos de NOMBRES_TRAMITES en apps/web/src/lib/informe.ts) y
# una forma corta para los ejes de los gráficos.
NOMBRES: dict[str, str] = {
    "legalizaciones": "Legalizaciones",
    "pqrs": "PQRSDF",
    "numeracion resoluciones": "Numeración de resoluciones",
    "notificacion": "Notificación",
    "atencion personalizada": "Atención personalizada",
    "certificados de existencia": "Certificados de existencia",
    "certificados de programa": "Certificados de programa",
    "certificados de idoneidad": "Certificados de idoneidad",
    "convalidaciones de basica": "Convalidaciones de básica",
    "citas virtuales": "Citas virtuales",
    "sin homologar": "Sin homologar",
}
CORTOS: dict[str, str] = {
    "legalizaciones": "Legalizaciones",
    "pqrs": "PQRSDF",
    "numeracion resoluciones": "Numeración",
    "notificacion": "Notificación",
    "atencion personalizada": "Personalizada",
    "certificados de existencia": "Cert. existencia",
    "certificados de programa": "Cert. programa",
    "certificados de idoneidad": "Cert. idoneidad",
    "convalidaciones de basica": "Convalidaciones",
    "citas virtuales": "Citas virtuales",
    "sin homologar": "Sin homologar",
}
# Qué es cada trámite, para el glosario y la metodología.
DEFINICIONES: dict[str, str] = {
    "legalizaciones": "Legalización de documentos de educación superior expedidos en Colombia para que surtan efecto en el exterior.",
    "pqrs": "Peticiones, quejas, reclamos, sugerencias, denuncias y felicitaciones de la ciudadanía gestionadas por la Subdirección.",
    "numeracion resoluciones": "Asignación de número y fecha a las resoluciones que expide el Ministerio.",
    "notificacion": "Notificación a los interesados de los actos administrativos expedidos por el Ministerio.",
    "atencion personalizada": "Atención presencial en ventanilla a la ciudadanía en la sede del Ministerio.",
    "certificados de existencia": "Certificados de existencia y representación legal de instituciones de educación superior.",
    "certificados de programa": "Certificados sobre programas académicos de educación superior.",
    "certificados de idoneidad": "Certificados de idoneidad de instituciones o programas, para trámites en el exterior.",
    "convalidaciones de basica": "Convalidación de estudios de educación básica y media cursados en el exterior.",
    "citas virtuales": "Citas de atención virtual agendadas por la ciudadanía con la Subdirección.",
}
PARETO = 0.8  # la guía del Pareto: cuántos tipos explican el 80 % del volumen


@dataclass(frozen=True)
class Tramite:
    id: int
    fuente: str  # el nombre tal como viene en la fuente (minúscula, sin tildes)

    @property
    def nombre(self) -> str:
        return NOMBRES.get(self.fuente, capitalizar(self.fuente))

    @property
    def corto(self) -> str:
        return CORTOS.get(self.fuente, self.nombre)


@dataclass
class Fuente:
    periodo_maximo: str
    periodo_minimo: str
    fecha_corte: str
    publicado_en: str
    actualizacion_id: int
    version_pipeline: str
    tramites: list[Tramite]  # el catálogo, en el orden de sus ids
    # periodo (AAAA-MM-01) → tipo id → trámites del mes (solo cantidades > 0)
    por_periodo: dict[str, dict[int, int]]
    periodos: list[str]


def cargar(ruta_api: Path) -> Fuente:
    resumen = json.loads((ruta_api / "tramites" / "resumen.json").read_text(encoding="utf-8"))
    cubo = json.loads((ruta_api / "tramites" / "cubo.json").read_text(encoding="utf-8"))
    dimensiones = json.loads((ruta_api / "dimensiones.json").read_text(encoding="utf-8"))
    tramites = sorted(
        (Tramite(int(d["id"]), str(d["nombre"])) for d in dimensiones.get("tramites", [])), key=lambda t: t.id
    )
    col = {c: i for i, c in enumerate(cubo["columnas"])}
    por_periodo: dict[str, dict[int, int]] = {}
    for f in cubo["filas"]:
        cantidad = int(f[col["cantidad"]] or 0)
        if cantidad <= 0:
            continue
        periodo = f[col["periodo"]][:10]
        tipo = int(f[col["tramite_id"]])
        por_periodo.setdefault(periodo, {})
        por_periodo[periodo][tipo] = por_periodo[periodo].get(tipo, 0) + cantidad
    return Fuente(
        periodo_maximo=resumen["periodo_maximo"][:10],
        periodo_minimo=resumen["periodo_minimo"][:10],
        fecha_corte=resumen["fecha_corte_maxima"][:10],
        publicado_en=resumen["publicado_en"],
        actualizacion_id=int(resumen["actualizacion_id"]),
        version_pipeline=resumen.get("version_pipeline", ""),
        tramites=tramites,
        por_periodo=por_periodo,
        periodos=sorted(por_periodo),
    )


@dataclass
class Serie:
    """Lo que el informe escribe y dibuja del total general o de un tipo de trámite, visto en sus meses con datos."""

    tramite: Tramite | None  # None para el total general
    nombre: str
    periodos: list[str]  # los meses con datos, hasta el mes del informe
    mes: int | None  # None si no hay datos en el mes del informe
    mes_anterior: int | None  # el mes anterior con datos
    periodo_anterior: str | None
    mismo_mes_anterior: int | None
    acumulado: int  # los meses con datos del año, hasta el mes del informe
    meses_acumulado: int
    acumulado_anterior: int | None  # los mismos meses del año anterior
    meses_acumulado_anterior: int
    serie_anio: list[tuple[str, int]]
    serie_anio_anterior: list[tuple[str, int]]  # todos los meses con datos del año anterior
    serie_13: list[tuple[str, int]]  # los últimos trece meses con datos
    serie_completa: list[tuple[str, int]]  # todos los meses con datos hasta el mes del informe
    media_movil: dict[str, float | None] = field(
        default_factory=dict
    )  # promedio de los tres meses anteriores con datos
    ultimo_periodo: str | None = None  # hasta cuándo hay datos (puede ser anterior al mes del informe)
    primer_periodo: str | None = None

    @property
    def promedio_mensual(self) -> float | None:
        return self.acumulado / self.meses_acumulado if self.meses_acumulado else None

    @property
    def promedio_anterior(self) -> float | None:
        if self.acumulado_anterior is None or not self.meses_acumulado_anterior:
            return None
        return self.acumulado_anterior / self.meses_acumulado_anterior

    @property
    def promedio_historico(self) -> float | None:
        return sum(v for _, v in self.serie_completa) / len(self.serie_completa) if self.serie_completa else None

    @property
    def mes_mayor(self) -> tuple[str, int] | None:
        return max(self.serie_anio, key=lambda pv: pv[1]) if self.serie_anio else None

    @property
    def mes_menor(self) -> tuple[str, int] | None:
        return min(self.serie_anio, key=lambda pv: pv[1]) if self.serie_anio else None

    @property
    def activo(self) -> bool:
        """Si el tipo tiene datos en el mes del informe."""
        return self.mes is not None


@dataclass
class Calculo:
    periodo: str
    fecha_corte: str
    publicado_en: str
    actualizacion_id: int
    version_pipeline: str
    primer_periodo: str
    total: Serie
    tipos: list[Serie]  # los tipos con datos en el año del informe, en el orden del catálogo (sin datos, no entran)
    # trámites por tipo y mes del año, para las barras apiladas y la mezcla: periodo → [(tipo, cantidad)]
    tipo_por_mes: list[tuple[str, list[tuple[Tramite, int]]]]

    @property
    def anio(self) -> int:
        return int(self.periodo[:4])

    @property
    def mes_numero(self) -> int:
        return int(self.periodo[5:7])

    def periodo_anterior_str(self) -> str:
        return periodo_anterior(self.periodo)

    def tipo(self, id_: int) -> Serie | None:
        return next((s for s in self.tipos if s.tramite is not None and s.tramite.id == id_), None)

    @property
    def tipos_del_mes(self) -> list[Serie]:
        """Los tipos con datos en el mes del informe, de mayor a menor volumen."""
        return sorted([s for s in self.tipos if s.mes], key=lambda s: -(s.mes or 0))

    @property
    def tipos_del_anio(self) -> list[Serie]:
        """Los tipos con datos en el año del informe, de mayor a menor acumulado."""
        return sorted([s for s in self.tipos if s.acumulado], key=lambda s: -s.acumulado)

    def participacion(self, s: Serie) -> float | None:
        if s.mes is None or not self.total.mes:
            return None
        return s.mes / self.total.mes

    def participacion_anio(self, s: Serie) -> float | None:
        return s.acumulado / self.total.acumulado if self.total.acumulado else None


def cuantos_para(items: list[int], umbral: float = PARETO) -> int:
    """Cuántos de los valores (de mayor a menor) hacen falta para alcanzar el `umbral` del total."""
    total = sum(items)
    if not total:
        return 0
    suma = 0
    for i, v in enumerate(sorted(items, reverse=True), start=1):
        suma += v
        if suma / total >= umbral:
            return i
    return len(items)


def _serie(fuente: Fuente, periodo: str, ids: list[int], tramite: Tramite | None, nombre: str) -> Serie:
    """La serie de un tipo o del total: por mes, la suma de los tipos pedidos con datos."""

    def del_mes(p: str) -> int | None:
        partes = [fuente.por_periodo.get(p, {}).get(i) for i in ids]
        partes = [v for v in partes if v]
        return sum(partes) if partes else None

    con_datos = [p for p in fuente.periodos if del_mes(p) is not None]
    periodos = [p for p in con_datos if p <= periodo]
    anio = periodo[:4]
    anio_ant = str(int(anio) - 1)
    serie_anio = [(p, del_mes(p)) for p in periodos if p[:4] == anio]
    serie_anio_anterior = [(p, del_mes(p)) for p in con_datos if p[:4] == anio_ant]
    serie_completa = [(p, del_mes(p)) for p in periodos]
    serie_13 = serie_completa[-13:]
    mes = del_mes(periodo)
    i = periodos.index(periodo) if periodo in periodos else None
    periodo_ant = periodos[i - 1] if i else (periodos[-1] if i is None and periodos else None)
    mes_ant = del_mes(periodo_ant) if periodo_ant else None
    mismo = del_mes(mismo_mes_anio_anterior(periodo))
    acumulado = sum(v for _, v in serie_anio)
    meses_anio = {p[5:7] for p, _ in serie_anio}
    previos = [v for p, v in serie_anio_anterior if p[5:7] in meses_anio]
    media_movil: dict[str, float | None] = {}
    for j, p in enumerate(periodos):
        anteriores = periodos[max(0, j - 3) : j]
        media_movil[p] = sum(del_mes(q) for q in anteriores) / 3 if len(anteriores) == 3 else None
    return Serie(
        tramite=tramite,
        nombre=nombre,
        periodos=periodos,
        mes=mes,
        mes_anterior=mes_ant,
        periodo_anterior=periodo_ant,
        mismo_mes_anterior=mismo,
        acumulado=acumulado,
        meses_acumulado=len(serie_anio),
        acumulado_anterior=sum(previos) if previos else None,
        meses_acumulado_anterior=len(previos),
        serie_anio=serie_anio,
        serie_anio_anterior=serie_anio_anterior,
        serie_13=serie_13,
        serie_completa=serie_completa,
        media_movil=media_movil,
        ultimo_periodo=con_datos[-1] if con_datos else None,
        primer_periodo=con_datos[0] if con_datos else None,
    )


def calcular(fuente: Fuente, periodo: str) -> Calculo:
    if periodo not in fuente.por_periodo:
        raise ValueError(f"no hay datos de trámites para {periodo[:7]}")
    presentes = {t for valores in fuente.por_periodo.values() for t in valores}
    catalogo = [t for t in fuente.tramites if t.id in presentes]
    # un tipo sin datos en el año del informe no se incluye (pedido del patrocinador, 2026-10-29): cada informe trae
    # solo lo que hay mes a mes
    tipos = [s for s in (_serie(fuente, periodo, [t.id], t, t.nombre) for t in catalogo) if s.serie_anio]
    total = _serie(fuente, periodo, [t.id for t in catalogo], None, "Total general")
    anio = periodo[:4]
    tipo_por_mes = []
    for p in fuente.periodos:
        if p[:4] != anio or p > periodo:
            continue
        lista = [(t, fuente.por_periodo[p][t.id]) for t in catalogo if t.id in fuente.por_periodo[p]]
        tipo_por_mes.append((p, lista))
    return Calculo(
        periodo=periodo,
        fecha_corte=periodo[:8] + str(calendar.monthrange(int(periodo[:4]), int(periodo[5:7]))[1]),
        publicado_en=fuente.publicado_en,
        actualizacion_id=fuente.actualizacion_id,
        version_pipeline=fuente.version_pipeline,
        primer_periodo=fuente.periodo_minimo,
        total=total,
        tipos=tipos,
        tipo_por_mes=tipo_por_mes,
    )
