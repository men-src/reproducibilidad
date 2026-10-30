"""Los datos del Informe de Canales de Atención en PDF: se leen de los agregados exportados en api/v1 (el cubo de
canales y las dimensiones), los mismos que lee el informe interactivo, y se suman con sus mismas reglas (BR-012, D-52
a D-54): nivel de atención = atendidas sobre recibidas; nivel de servicio = contestadas antes del tiempo objetivo sobre
recibidas; nivel de abandono = abandonadas sobre recibidas; resolución del chatbot = resueltas sobre resueltas más no
resueltas; efectividad de la devolución de llamadas y del buzón de voz = llamadas efectivas sobre solicitudes. Cada
canal tiene datos hasta un mes distinto y pudo no existir en algunos meses, así que cada canal se mira solo en sus
meses con datos, como en el informe interactivo."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from men_platform.publicaciones.datos_pqrsdf import mismo_mes_anio_anterior, periodo_anterior


def _razon(numerador: float, denominador: float) -> float | None:
    return numerador / denominador if denominador else None


# Los canales con los nombres oficiales que fijó el patrocinador (D-52 y D-54), en el orden del informe interactivo.
# Cómo se llama lo recibido en cada tipo: en los canales de contacto son interacciones; en el chatbot, transacciones;
# en los de devolución (devolución de llamadas y buzón de voz), solicitudes; en la atención presencial, atenciones.
@dataclass(frozen=True)
class Canal:
    id: int
    nombre: str
    tipo: str  # contacto, chatbot, callback, presencial
    recibidas: str  # cómo se llama lo recibido, en plural y minúscula
    atendidas: str  # cómo se llama lo atendido


CANALES: list[Canal] = [
    Canal(1, "Atención Telefónica", "contacto", "llamadas recibidas", "llamadas atendidas"),
    Canal(2, "Chat de Atención al Ciudadano", "contacto", "chats recibidos", "chats atendidos"),
    Canal(3, "Llamada Virtual", "contacto", "llamadas virtuales recibidas", "llamadas virtuales atendidas"),
    Canal(4, "Video Llamada Virtual", "contacto", "video llamadas recibidas", "video llamadas atendidas"),
    Canal(5, "Chatbot", "chatbot", "transacciones", "transacciones"),
    Canal(6, "Devolución de Llamadas", "callback", "solicitudes de llamada", "llamadas efectivas"),
    Canal(7, "Atención Presencial", "presencial", "atenciones presenciales", "atenciones presenciales"),
    Canal(8, "Buzón de Voz", "callback", "mensajes en el buzón", "llamadas efectivas"),
]
POR_ID = {c.id: c for c in CANALES}
CONTACTO = [c for c in CANALES if c.tipo == "contacto"]


@dataclass
class Totales:
    """Sumas de un conjunto de filas del cubo de canales y las razones que salen de ellas."""

    recibidas: int = 0
    atendidas: int = 0
    en_nivel_servicio: int = 0
    abandonadas: int = 0
    preguntas: int = 0
    preguntas_resueltas: int = 0
    preguntas_no_resueltas: int = 0
    meses: int = 0  # meses con datos sumados (para promedios mensuales)

    @property
    def nivel_atencion(self) -> float | None:
        return _razon(self.atendidas, self.recibidas)

    @property
    def nivel_servicio(self) -> float | None:
        return _razon(self.en_nivel_servicio, self.recibidas)

    @property
    def nivel_abandono(self) -> float | None:
        return _razon(self.abandonadas, self.recibidas)

    @property
    def resolucion(self) -> float | None:
        return _razon(self.preguntas_resueltas, self.preguntas_resueltas + self.preguntas_no_resueltas)

    @property
    def efectividad(self) -> float | None:
        return self.nivel_atencion

    @property
    def promedio_mensual(self) -> float | None:
        return _razon(self.recibidas, self.meses)

    def mas(self, otro: Totales) -> Totales:
        return Totales(
            self.recibidas + otro.recibidas,
            self.atendidas + otro.atendidas,
            self.en_nivel_servicio + otro.en_nivel_servicio,
            self.abandonadas + otro.abandonadas,
            self.preguntas + otro.preguntas,
            self.preguntas_resueltas + otro.preguntas_resueltas,
            self.preguntas_no_resueltas + otro.preguntas_no_resueltas,
            self.meses + otro.meses,
        )


def sumar(filas: list[Totales]) -> Totales:
    total = Totales()
    for f in filas:
        total = total.mas(f)
    return total


@dataclass
class Fuente:
    periodo_maximo: str
    periodo_minimo: str
    fecha_corte: str
    publicado_en: str
    actualizacion_id: int
    version_pipeline: str
    # periodo (AAAA-MM-01) → canal id → totales del mes (solo filas con recibidas > 0)
    por_periodo: dict[str, dict[int, Totales]]
    periodos: list[str]


def cargar(ruta_api: Path) -> Fuente:
    resumen = json.loads((ruta_api / "canales" / "resumen.json").read_text(encoding="utf-8"))
    cubo = json.loads((ruta_api / "canales" / "cubo.json").read_text(encoding="utf-8"))
    col = {c: i for i, c in enumerate(cubo["columnas"])}
    por_periodo: dict[str, dict[int, Totales]] = {}
    for f in cubo["filas"]:
        canal = int(f[col["canal_atencion_id"]])
        if canal not in POR_ID:
            continue
        t = Totales(
            int(f[col["recibidas"]] or 0),
            int(f[col["atendidas"]] or 0),
            int(f[col["en_nivel_servicio"]] or 0),
            int(f[col["abandonadas"]] or 0),
            int(f[col["preguntas"]] or 0),
            int(f[col["preguntas_resueltas"]] or 0),
            int(f[col["preguntas_no_resueltas"]] or 0),
            1,
        )
        if t.recibidas <= 0:
            continue
        periodo = f[col["periodo"]][:10]
        por_periodo.setdefault(periodo, {})
        por_periodo[periodo][canal] = por_periodo[periodo][canal].mas(t) if canal in por_periodo[periodo] else t
    periodos = sorted(por_periodo)
    return Fuente(
        periodo_maximo=resumen["periodo_maximo"][:10],
        periodo_minimo=resumen["periodo_minimo"][:10],
        fecha_corte=resumen["fecha_corte_maxima"][:10],
        publicado_en=resumen["publicado_en"],
        actualizacion_id=int(resumen["actualizacion_id"]),
        version_pipeline=resumen.get("version_pipeline", ""),
        por_periodo=por_periodo,
        periodos=periodos,
    )


@dataclass
class SerieCanal:
    """Lo que el informe escribe y dibuja de un canal (o de un conjunto de canales), visto solo en sus meses con datos."""

    canal: Canal | None  # None para los conjuntos (todos los canales, canales de contacto)
    nombre: str
    tipo: str
    periodos: list[str]  # los meses con datos, hasta el mes del informe
    mes: Totales | None  # None si el canal no tiene datos en el mes del informe
    mes_anterior: Totales | None  # el mes anterior con datos
    periodo_anterior: str | None
    mismo_mes_anterior: Totales | None
    acumulado: Totales  # los meses con datos del año, hasta el mes del informe
    acumulado_anterior: Totales | None  # los mismos meses del año anterior
    serie_anio: list[tuple[str, Totales]]
    serie_anio_anterior: list[tuple[str, Totales]]
    serie_13: list[tuple[str, Totales]]  # los últimos trece meses con datos
    media_movil: dict[str, float | None] = field(
        default_factory=dict
    )  # recibidas: promedio de los tres meses anteriores con datos
    ultimo_periodo: str | None = None  # hasta cuándo hay datos del canal (puede ser anterior al mes del informe)


@dataclass
class Calculo:
    periodo: str
    fecha_corte: str
    publicado_en: str
    actualizacion_id: int
    version_pipeline: str
    primer_periodo: str
    todos: SerieCanal  # todos los canales: solo los volúmenes
    contacto: SerieCanal  # los cuatro canales de contacto: los niveles
    canales: list[SerieCanal]  # uno por canal del catálogo, en orden
    # recibidas por canal y mes del año, para las barras apiladas y la mezcla: periodo → [(canal, Totales)]
    canal_por_mes: list[tuple[str, list[tuple[Canal, Totales]]]]

    @property
    def anio(self) -> int:
        return int(self.periodo[:4])

    @property
    def mes_numero(self) -> int:
        return int(self.periodo[5:7])

    def periodo_anterior_str(self) -> str:
        return periodo_anterior(self.periodo)

    def por_tipo(self, tipo: str) -> list[SerieCanal]:
        return [s for s in self.canales if s.tipo == tipo]

    def canal(self, id_: int) -> SerieCanal:
        return next(s for s in self.canales if s.canal is not None and s.canal.id == id_)


def _serie(fuente: Fuente, periodo: str, ids: list[int], canal: Canal | None, nombre: str, tipo: str) -> SerieCanal:
    """La serie de un canal o de un conjunto de canales: por mes, la suma de los canales pedidos con datos."""

    def del_mes(p: str) -> Totales | None:
        partes = [fuente.por_periodo.get(p, {}).get(i) for i in ids]
        partes = [t for t in partes if t is not None]
        if not partes:
            return None
        t = sumar(partes)
        t.meses = 1
        return t

    con_datos = [p for p in fuente.periodos if del_mes(p) is not None]
    periodos = [p for p in con_datos if p <= periodo]
    anio = periodo[:4]
    anio_ant = str(int(anio) - 1)
    serie_anio = [(p, del_mes(p)) for p in periodos if p[:4] == anio]
    serie_anio_anterior = [(p, del_mes(p)) for p in con_datos if p[:4] == anio_ant]
    serie_13 = [(p, del_mes(p)) for p in periodos[-13:]]
    mes = del_mes(periodo)
    i = periodos.index(periodo) if periodo in periodos else None
    periodo_ant = periodos[i - 1] if i else (periodos[-1] if i is None and periodos else None)
    mes_ant = del_mes(periodo_ant) if periodo_ant else None
    mismo = del_mes(mismo_mes_anio_anterior(periodo))
    acumulado = sumar([t for _, t in serie_anio])
    meses_anio = {p[5:7] for p, _ in serie_anio}
    previos = [t for p, t in serie_anio_anterior if p[5:7] in meses_anio]
    acumulado_anterior = sumar(previos) if previos else None
    media_movil: dict[str, float | None] = {}
    for j, p in enumerate(periodos):
        anteriores = periodos[max(0, j - 3) : j]
        media_movil[p] = sum(del_mes(q).recibidas for q in anteriores) / 3 if len(anteriores) == 3 else None
    return SerieCanal(
        canal=canal,
        nombre=nombre,
        tipo=tipo,
        periodos=periodos,
        mes=mes,
        mes_anterior=mes_ant,
        periodo_anterior=periodo_ant,
        mismo_mes_anterior=mismo,
        acumulado=acumulado,
        acumulado_anterior=acumulado_anterior,
        serie_anio=serie_anio,
        serie_anio_anterior=serie_anio_anterior,
        serie_13=serie_13,
        media_movil=media_movil,
        ultimo_periodo=con_datos[-1] if con_datos else None,
    )


def calcular(fuente: Fuente, periodo: str) -> Calculo:
    if periodo not in fuente.por_periodo:
        raise ValueError(f"no hay datos de canales para {periodo[:7]}")
    canales = [_serie(fuente, periodo, [c.id], c, c.nombre, c.tipo) for c in CANALES]
    todos = _serie(fuente, periodo, [c.id for c in CANALES], None, "Todos los canales", "todos")
    contacto = _serie(fuente, periodo, [c.id for c in CONTACTO], None, "Canales de contacto", "contacto")
    anio = periodo[:4]
    canal_por_mes = []
    for p in fuente.periodos:
        if p[:4] != anio or p > periodo:
            continue
        lista = [(c, fuente.por_periodo[p][c.id]) for c in CANALES if c.id in fuente.por_periodo[p]]
        canal_por_mes.append((p, lista))
    return Calculo(
        periodo=periodo,
        fecha_corte=periodo[:8] + str(_dias_del_mes(periodo)),
        publicado_en=fuente.publicado_en,
        actualizacion_id=fuente.actualizacion_id,
        version_pipeline=fuente.version_pipeline,
        primer_periodo=fuente.periodo_minimo,
        todos=todos,
        contacto=contacto,
        canales=canales,
        canal_por_mes=canal_por_mes,
    )


def _dias_del_mes(periodo: str) -> int:
    import calendar

    return calendar.monthrange(int(periodo[:4]), int(periodo[5:7]))[1]
