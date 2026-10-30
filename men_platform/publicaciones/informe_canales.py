"""El Informe de Canales de Atención de un mes en PDF (D-74): portada, tabla de contenido, resumen ejecutivo con tarjetas,
objetivos, metodología, glosario, resultados (el resumen del mes, la comparación con el mes anterior y un apartado por
canal con las mismas vistas del informe interactivo), observaciones, recomendaciones, conclusiones y anexos, sobre la
base común de documento.py."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from men_platform.publicaciones import graficos_canales as gc
from men_platform.publicaciones import graficos_tablero as gt
from men_platform.publicaciones import interpretaciones_canales as interp
from men_platform.publicaciones.datos_canales import CANALES, Calculo, SerieCanal, Totales, sumar
from men_platform.publicaciones.documento import (
    AREA,
    ENTIDAD,
    Cabecera,
    Constructor,
    Portada,
    generar_pdf,
    registrar_fuentes,
)
from men_platform.publicaciones.graficos_canales import NEUTRO, PALETA_CANALES
from men_platform.publicaciones.graficos_pqrsdf import AMARILLO, AZUL, AZUL_CLARO, ROJO
from men_platform.publicaciones.procedencia import Procedencia, fecha_generacion, filas_ficha, nota_cifra
from men_platform.publicaciones.redaccion_canales import redactar
from men_platform.publicaciones.redaccion_pqrsdf import Textos
from men_platform.publicaciones.texto_es import (
    decimal,
    entero,
    fecha_larga,
    lista_en_prosa,
    mayuscula_inicial,
    mes_corto,
    mes_corto_2,
    mes_y_anio,
    mes_y_anio_siguiente,
    nombre_mes,
    porcentaje,
    puntos,
    tramo_del_anio,
    variacion,
)

TITULO_INFORME = "Informe de Canales de Atención"
URL_INFORME = "https://men-src.github.io/canales-atencion/"
GUION = "–"
RECORTE_VARIACION = 300.0  # una variación mayor que 300 % se dibuja recortada: el mes anterior fue atípico
NOMBRES_CORTOS = {
    "Atención Telefónica": "Telefónica",
    "Chat de Atención al Ciudadano": "Chat",
    "Llamada Virtual": "Llamada virtual",
    "Video Llamada Virtual": "Video llamada",
    "Chatbot": "Chatbot",
    "Devolución de Llamadas": "Devolución",
    "Atención Presencial": "Presencial",
    "Buzón de Voz": "Buzón",
}


def _etiquetas(serie: list[tuple[str, object]]) -> list[str]:
    return [mes_corto_2(p) if len(serie) > 9 else mes_corto(p) for p, _ in serie]


def _pct(v: float | None) -> str:
    return porcentaje(v) if v is not None else GUION


class _Constructor(Constructor):
    """Las secciones del Informe de Canales de Atención sobre la base común."""

    def __init__(self, calculo: Calculo, textos: Textos, procedencia: Procedencia | None = None) -> None:
        self.procedencia = procedencia or Procedencia()
        super().__init__()
        self.calculo = calculo
        self.textos = textos

    # --- secciones --------------------------------------------------------------------------------------------
    def construir(self) -> list:
        t = self.textos
        self.indice()
        self._resumen()
        self.titulo1("2. Objetivos")
        self.p("<b>Objetivo general.</b> " + escape(t.objetivo_general))
        self.espacio(0.2)
        self.p("<b>Objetivos específicos.</b>")
        self.lista(t.objetivos_especificos, numerada=True)
        self.titulo1("3. Metodología")
        for subtitulo, texto in t.metodologia:
            self.p(f"<b>{escape(subtitulo)}.</b> {escape(texto)}")
        self.glosario(4, t.glosario, t.siglas)
        self._resultados()
        self.titulo1("6. Observaciones")
        self.p(
            "Las observaciones salen de las cifras del mes y de su comparación con el mes anterior y con el propio historial de cada "
            "canal; cada una señala un hecho verificable en las tablas de este informe.",
            "Bajada",
        )
        self.lista(t.observaciones)
        self.titulo1("7. Recomendaciones")
        self.p(
            "Las recomendaciones responden a las observaciones anteriores y se dirigen a la entidad: a la Subdirección de Relacionamiento "
            "con la Ciudadanía, al operador del centro de contacto y a las áreas que acompañan la atención a la ciudadanía.",
            "Bajada",
        )
        self.lista(t.recomendaciones, numerada=True)
        self.titulo1("8. Conclusiones")
        for parrafo in t.conclusiones:
            self.p(escape(parrafo))
        self._anexos()
        return self.historia

    def _resumen(self) -> None:
        self.titulo1("1. Resumen ejecutivo")
        for parrafo in self.textos.resumen:
            self.p(escape(parrafo))
        self.espacio(0.2)
        self._tarjetas_indicadores()

    def _tarjetas_indicadores(self) -> None:
        """Ocho tarjetas en dos filas: el valor del mes y, debajo, el mes anterior con datos, el mismo mes del año anterior y el año."""
        c = self.calculo
        anio = c.anio

        def lineas(s: SerieCanal, f, comparar) -> list[str]:  # noqa: ANN001
            out = []
            if s.mes_anterior and s.mes:
                etiqueta = mayuscula_inicial(mes_corto(s.periodo_anterior))
                out.append(f"{etiqueta}: {f(s.mes_anterior)} ({comparar(s.mes, s.mes_anterior)})")
            if s.mismo_mes_anterior and s.mes:
                out.append(
                    f"{mayuscula_inicial(mes_corto(c.periodo)[:3])} {anio - 1}: {f(s.mismo_mes_anterior)} ({comparar(s.mes, s.mismo_mes_anterior)})"
                )
            out.append(f"Año {anio}: {f(s.acumulado) if s.acumulado.meses else GUION}")
            return out

        def var_entero(atributo: str):  # noqa: ANN202
            return lambda a, b: variacion(getattr(a, atributo), getattr(b, atributo))

        def var_pp(atributo: str):  # noqa: ANN202
            return lambda a, b: puntos((getattr(a, atributo) or 0) - (getattr(b, atributo) or 0))

        def tarjeta(titulo: str, s: SerieCanal, f, comparar) -> list:  # noqa: ANN001
            return self.tarjeta(titulo, f(s.mes) if s.mes else GUION, lineas(s, f, comparar))

        todos, k, bot, pres = c.todos, c.contacto, c.canal(5), c.canal(7)
        tarjetas = [
            tarjeta(
                "Interacciones recibidas (todos los canales)",
                todos,
                lambda t: entero(t.recibidas),
                var_entero("recibidas"),
            ),
            tarjeta("Atendidas (sin el chatbot)", todos, lambda t: entero(t.atendidas), var_entero("atendidas")),
            tarjeta(
                "Nivel de atención (canales de contacto)", k, lambda t: _pct(t.nivel_atencion), var_pp("nivel_atencion")
            ),
            tarjeta(
                "Nivel de servicio (canales de contacto)", k, lambda t: _pct(t.nivel_servicio), var_pp("nivel_servicio")
            ),
            tarjeta(
                "Nivel de abandono (canales de contacto)", k, lambda t: _pct(t.nivel_abandono), var_pp("nivel_abandono")
            ),
            tarjeta("Transacciones del chatbot", bot, lambda t: entero(t.recibidas), var_entero("recibidas")),
            tarjeta("Resolución del chatbot", bot, lambda t: _pct(t.resolucion), var_pp("resolucion")),
            tarjeta("Atenciones presenciales", pres, lambda t: entero(t.recibidas), var_entero("recibidas")),
        ]
        self.tarjetas("Tarjetas de resultados del mes y sus comparaciones", tarjetas)
        self.p(
            "Cada tarjeta trae el valor del mes y, debajo, el mes anterior con datos del canal, el mismo mes del año anterior y el "
            "acumulado del año; los niveles del conjunto son los de los cuatro canales de contacto.",
            "Nota",
        )

    # --- resultados ---------------------------------------------------------------------------------------------
    def _resultados(self) -> None:  # noqa: PLR0915 - un apartado por canal, en el orden del informe interactivo
        c = self.calculo
        mes = mes_y_anio(c.periodo)
        anio = c.anio
        n = 5
        todos, k = c.todos, c.contacto
        self.titulo1(f"{n}. Resultados")
        self.p(
            f"Esta sección recorre los canales de atención en {mes}: primero el resumen del mes (lo recibido por canal, la evolución del "
            "año y la mezcla de canales), después la comparación con el mes anterior y, por último, un apartado por canal con las mismas "
            "vistas del informe interactivo. Cada gráfico y cada tabla van seguidos de su lectura."
        )

        # --- 5.1 resumen del mes -----------------------------------------------------------------------------
        self.titulo2(
            f"{n}.1 Resumen del mes",
            f"Cuántas interacciones recibió cada canal en {mes}, cómo fue {anio} mes a mes y cómo se reparten los canales.",
        )
        filas = []
        for s in c.canales:
            if not s.mes:
                continue
            t, tipo = s.mes, s.tipo
            if tipo == "contacto":
                fila = [
                    s.nombre,
                    entero(t.recibidas),
                    entero(t.atendidas),
                    _pct(t.nivel_atencion),
                    _pct(t.nivel_servicio),
                    _pct(t.nivel_abandono),
                    "",
                ]
            elif tipo == "chatbot":
                fila = [
                    s.nombre,
                    entero(t.recibidas),
                    GUION,
                    GUION,
                    GUION,
                    GUION,
                    f"{entero(t.preguntas)} conversaciones, {_pct(t.resolucion)} resueltas",
                ]
            elif tipo == "callback":
                fila = [
                    s.nombre,
                    entero(t.recibidas),
                    entero(t.atendidas),
                    _pct(t.efectividad),
                    GUION,
                    _pct(t.nivel_abandono),
                    "Atención: efectividad; Abandono: no efectivas",
                ]
            else:
                fila = [s.nombre, entero(t.recibidas), entero(t.atendidas), GUION, GUION, GUION, "solo el total"]
            filas.append(fila)
        km = k.mes
        filas.append(
            [
                "Total (niveles de los canales de contacto)",
                entero(todos.mes.recibidas),
                entero(todos.mes.atendidas),
                _pct(km.nivel_atencion) if km else GUION,
                _pct(km.nivel_servicio) if km else GUION,
                _pct(km.nivel_abandono) if km else GUION,
                "",
            ]
        )
        self.tabla(
            f"Resumen por canal en {mes}: recibidas, atendidas, nivel de atención, nivel de servicio y nivel de abandono",
            ["Canal", "Recibidas", "Atendidas", "Atención", "Servicio", "Abandono", "Detalle"],
            filas,
            [2.0, 0.95, 0.95, 0.9, 0.85, 0.95, 1.75],
            lectura=interp.tabla_canales(c),
            numericas={1, 2, 3, 4, 5},
            resaltar=len(filas) - 1,
        )
        con_datos = sorted([s for s in c.canales if s.mes], key=lambda s: -s.mes.recibidas)
        segundo = con_datos[1] if len(con_datos) > 1 else None
        veces = (
            f"{decimal(con_datos[0].mes.recibidas / segundo.mes.recibidas, 1)} veces las del segundo canal ({segundo.nombre.lower()}, {entero(segundo.mes.recibidas)})"
            if segundo and segundo.mes.recibidas
            else "sin otro canal con el cual compararlo"
        )
        self.grafico(
            gc.barras_por_canal(
                [s.nombre for s in con_datos],
                [s.mes.recibidas for s in con_datos],
                [PALETA_CANALES[s.canal.id] for s in con_datos],
            ),
            f"Interacciones recibidas por canal en {mes}, de mayor a menor.",
            f"{con_datos[0].nombre} recibió {entero(con_datos[0].mes.recibidas)} interacciones, {veces}. Las barras ponen en escala lo que "
            "la tabla dice en cifras: el canal de mayor volumen sigue siendo la puerta principal del Ministerio.",
        )
        if len(c.canal_por_mes) >= 2:
            etiquetas_anio = _etiquetas(c.canal_por_mes)
            partes = []
            for canal in CANALES:
                valores = [
                    next((t.recibidas for cn, t in lista if cn.id == canal.id), 0) for _, lista in c.canal_por_mes
                ]
                if any(valores):
                    partes.append((canal.nombre, PALETA_CANALES[canal.id], valores))
            atencion_mes = [
                next((t.nivel_atencion for p2, t in k.serie_anio if p2 == p), None) for p, _ in c.canal_por_mes
            ]
            resaltar = next((i for i, (p, _) in enumerate(c.canal_por_mes) if p == c.periodo), None)
            self.grafico(
                gc.barras_con_linea(
                    etiquetas_anio,
                    partes,
                    ("Nivel de atención (contacto)", atencion_mes),
                    apiladas=True,
                    resaltar=resaltar,
                ),
                f"Interacciones recibidas por canal mes a mes en {anio}, apiladas, con el nivel de atención de los canales de contacto.",
                interp.apiladas_por_canal(c),
            )
            if k.serie_anio:
                etiquetas_k = _etiquetas(k.serie_anio)
                resaltar_k = next((i for i, (p, _) in enumerate(k.serie_anio) if p == c.periodo), None)
                self.grafico(
                    gc.lineas_niveles(
                        etiquetas_k,
                        [
                            ("Nivel de atención", AZUL, [t.nivel_atencion for _, t in k.serie_anio]),
                            ("Nivel de servicio", AMARILLO, [t.nivel_servicio for _, t in k.serie_anio]),
                        ],
                        resaltar_k,
                    ),
                    f"Niveles de atención y de servicio de los canales de contacto mes a mes en {anio}.",
                    interp.niveles_mes_a_mes(c),
                )
                self._tabla_niveles(
                    k.serie_anio,
                    f"Canales de contacto mes a mes en {anio}: recibidas, atendidas, transacciones NS, abandonadas, nivel de atención, nivel de servicio y nivel de abandono",
                    k.acumulado,
                    tramo_del_anio(c.periodo, mayuscula=True),
                )
            self.grafico(
                gc.mezcla(etiquetas_anio, partes),
                f"Cómo se reparten los canales mes a mes en {anio}, al 100 %.",
                interp.mezcla(c),
            )
        else:
            self.p(
                f"{mayuscula_inicial(nombre_mes(c.periodo))} es el primer mes de {anio} con datos: las vistas mes a mes del año (recibidas por "
                "canal apiladas, niveles de atención y de servicio y mezcla de canales) empiezan en el informe siguiente."
            )

        # --- 5.2 comparación con el mes anterior -------------------------------------------------------------
        if todos.mes_anterior is None:
            self.titulo2(
                f"{n}.2 Comparación con el mes inmediatamente anterior",
                f"{mayuscula_inicial(mes)} es el primer mes del histórico de la plataforma: no hay un mes anterior con datos para comparar.",
            )
            self.p(f"La comparación con el mes anterior empieza en el informe de {mes_y_anio_siguiente(c.periodo)}.")
        else:
            mes_ant = nombre_mes(todos.periodo_anterior)
            mes_act = nombre_mes(c.periodo)
            self.titulo2(
                f"{n}.2 Comparación con {mes_ant}, el mes inmediatamente anterior",
                f"Qué cambió entre {mes_ant} y {mes_act} de {anio} en lo recibido por cada canal, en los niveles de atención y de "
                "servicio de los canales de contacto, en la resolución del chatbot y en la efectividad de la devolución de llamadas y del "
                "buzón de voz.",
            )
            col_ant = mayuscula_inicial(mes_corto(todos.periodo_anterior))
            col_act = mayuscula_inicial(mes_corto(c.periodo))
            abr_ant, abr_act = mes_corto(todos.periodo_anterior)[:3], mes_corto(c.periodo)[:3]

            def etiqueta_de(s: SerieCanal) -> str:
                # un canal sin datos en el mes calendario anterior se compara con su mes anterior con datos, y se dice
                return (
                    s.nombre
                    if s.periodo_anterior == todos.periodo_anterior
                    else f"{s.nombre} (frente a {mes_y_anio(s.periodo_anterior)})"
                )

            def dif_pp(antes: float | None, ahora: float | None) -> str:
                return puntos(ahora - antes) if antes is not None and ahora is not None else GUION

            # 1. lo recibido por canal
            filas = []
            for s in c.canales:
                if not s.mes or not s.mes_anterior:
                    continue
                filas.append(
                    [
                        etiqueta_de(s),
                        entero(s.mes_anterior.recibidas),
                        entero(s.mes.recibidas),
                        variacion(s.mes.recibidas, s.mes_anterior.recibidas),
                    ]
                )
            a, m = todos.mes_anterior, todos.mes
            filas.append(["Total", entero(a.recibidas), entero(m.recibidas), variacion(m.recibidas, a.recibidas)])
            self.tabla(
                f"Interacciones recibidas por canal: {mes_ant} y {mes_act} de {anio}",
                ["Canal", col_ant, col_act, "Variación"],
                filas,
                [3.0, 1.1, 1.1, 1.1],
                lectura=interp.comparacion_mes_anterior(c),
                numericas={1, 2, 3},
                resaltar=len(filas) - 1,
            )
            # 2. los niveles de atención y de servicio de los canales de contacto
            filas = []
            for s in c.por_tipo("contacto"):
                if not s.mes or not s.mes_anterior:
                    continue
                a, m = s.mes_anterior, s.mes
                filas.append(
                    [
                        etiqueta_de(s),
                        _pct(a.nivel_atencion),
                        _pct(m.nivel_atencion),
                        dif_pp(a.nivel_atencion, m.nivel_atencion),
                        _pct(a.nivel_servicio),
                        _pct(m.nivel_servicio),
                        dif_pp(a.nivel_servicio, m.nivel_servicio),
                    ]
                )
            ka, km = k.mes_anterior, k.mes
            if ka and km:
                filas.append(
                    [
                        "Canales de contacto",
                        _pct(ka.nivel_atencion),
                        _pct(km.nivel_atencion),
                        dif_pp(ka.nivel_atencion, km.nivel_atencion),
                        _pct(ka.nivel_servicio),
                        _pct(km.nivel_servicio),
                        dif_pp(ka.nivel_servicio, km.nivel_servicio),
                    ]
                )
            if filas:
                self.tabla(
                    f"Nivel de atención y nivel de servicio de los canales de contacto: {mes_ant} y {mes_act} de {anio}",
                    [
                        "Canal",
                        f"Atención {abr_ant}",
                        f"Atención {abr_act}",
                        "Dif. (pp)",
                        f"Servicio {abr_ant}",
                        f"Servicio {abr_act}",
                        "Dif. (pp)",
                    ],
                    filas,
                    [1.6, 1.0, 1.0, 0.75, 1.0, 1.0, 0.75],
                    lectura=interp.comparacion_niveles(c),
                    numericas={1, 2, 3, 4, 5, 6},
                    resaltar=len(filas) - 1,
                )
            # 3. la resolución del chatbot y la efectividad de los canales de devolución
            filas = []
            for s in c.canales:
                if s.tipo not in ("chatbot", "callback") or not s.mes or not s.mes_anterior:
                    continue
                campo, nombre = ("resolucion", "Resolución") if s.tipo == "chatbot" else ("efectividad", "Efectividad")
                antes, ahora = getattr(s.mes_anterior, campo), getattr(s.mes, campo)
                filas.append([etiqueta_de(s), nombre, _pct(antes), _pct(ahora), dif_pp(antes, ahora)])
            if filas:
                self.tabla(
                    f"Resolución del chatbot y efectividad de la devolución de llamadas y del buzón de voz: {mes_ant} y {mes_act} de {anio}",
                    ["Canal", "Indicador", col_ant, col_act, "Dif. (pp)"],
                    filas,
                    [2.6, 1.2, 1.0, 1.0, 0.9],
                    lectura=interp.comparacion_otros(c),
                    numericas={2, 3, 4},
                )

        # --- 5.3 en adelante: un apartado por canal ------------------------------------------------------------
        for k_canal, s in enumerate(c.canales, start=3):
            self._apartado_canal(n, k_canal, s)

    def _tabla_niveles(
        self, serie: list[tuple[str, Totales]], leyenda: str, total: Totales, etiqueta_total: str
    ) -> None:
        def fila(etiqueta: str, t: Totales) -> list[str]:
            return [
                etiqueta,
                entero(t.recibidas),
                entero(t.atendidas),
                entero(t.en_nivel_servicio),
                entero(t.abandonadas),
                _pct(t.nivel_atencion),
                _pct(t.nivel_servicio),
                _pct(t.nivel_abandono),
            ]

        # si la serie cruza años (los últimos trece meses con datos), cada mes lleva su año
        varios_anios = len({p[:4] for p, _ in serie}) > 1
        filas = [fila(mayuscula_inicial(mes_y_anio(p) if varios_anios else nombre_mes(p)), t) for p, t in serie]
        filas.append(fila(etiqueta_total, total))
        self.tabla(
            leyenda,
            ["Mes", "Recibidas", "Atendidas", "Transac. NS", "Abandonadas", "Atención", "Servicio", "Abandono"],
            filas,
            [1.2, 0.9, 0.92, 1.05, 1.15, 0.85, 0.8, 0.92],
            numericas={1, 2, 3, 4, 5, 6, 7},
            resaltar=len(filas) - 1,
        )

    def _apartado_canal(self, n: int, k_canal: int, s: SerieCanal) -> None:  # noqa: PLR0915
        c = self.calculo
        canal = s.canal
        anio = c.anio
        bajadas = {
            "contacto": (
                f"Lo recibido y lo atendido en {s.nombre.lower()} mes a mes, sus niveles de atención, de servicio y de abandono, y su "
                "comparación con el año anterior, con el mes anterior y con su media móvil."
            ),
            "chatbot": (
                "Las transacciones y conversaciones del chatbot, lo que resolvió sin pasar a un agente y lo que transfirió, mes a mes, y su "
                "volumen frente al año anterior, al mes anterior y a su media móvil."
            ),
            "callback": (
                f"Las {canal.recibidas} y las llamadas de vuelta efectivas y no efectivas de {s.nombre.lower()}, mes a mes, con su "
                "efectividad y su volumen frente al año anterior, al mes anterior y a su media móvil."
            ),
            "presencial": "Las atenciones en ventanilla mes a mes, frente al año anterior, al mes anterior y a su media móvil.",
        }
        bajada = bajadas[s.tipo]
        if s.ultimo_periodo and s.ultimo_periodo < c.periodo:
            bajada += f" El canal tiene datos hasta {mes_y_anio(s.ultimo_periodo)}."
        elif len(s.serie_anio) < len(c.todos.serie_anio):
            bajada += f" En {anio} tiene datos en {lista_en_prosa([nombre_mes(p) for p, _ in s.serie_anio])}."
        self.titulo2(f"{n}.{k_canal} {s.nombre}", bajada)
        if not s.serie_anio and not s.serie_13:
            self.p(f"{s.nombre} todavía no tiene datos cargados en la plataforma.")
            return
        es_anio = len(s.serie_anio) >= 2
        serie = s.serie_anio if es_anio else s.serie_13
        total_serie = s.acumulado if es_anio else sumar([tt for _, tt in serie])
        etiquetas = _etiquetas(serie)
        resaltar = next((i for i, (p, _) in enumerate(serie) if p == c.periodo), None)
        tramo = f"en {anio}" if es_anio else f"en los últimos {len(serie)} meses con datos"
        rec = canal.recibidas
        recibidas = [t.recibidas for _, t in serie]
        atendidas = [t.atendidas for _, t in serie]

        def barras(partes, linea, leyenda, lectura, apiladas=False) -> None:  # noqa: ANN001
            self.grafico(
                gc.barras_con_linea(etiquetas, partes, linea, apiladas=apiladas, resaltar=resaltar), leyenda, lectura
            )

        if len(serie) < 2:
            self.p(
                f"{mayuscula_inicial(mes_y_anio(serie[0][0]))} es el primer mes con datos de {s.nombre.lower()} en la plataforma: las vistas "
                "mes a mes empiezan en el informe siguiente."
            )
            if s.tipo == "contacto":
                self._tabla_niveles(
                    serie,
                    f"{s.nombre} {tramo}: recibidas, atendidas, transacciones NS, abandonadas, nivel de atención, nivel de servicio y nivel de abandono",
                    total_serie,
                    "Total",
                )
        else:
            if s.tipo == "contacto":
                barras(
                    [("Recibidas", NEUTRO, recibidas), ("Atendidas", AZUL, atendidas)],
                    ("Nivel de atención", [t.nivel_atencion for _, t in serie]),
                    f"{s.nombre}: recibidas, atendidas y nivel de atención por mes {tramo}.",
                    interp.recibidas_atendidas(s, c),
                )
                barras(
                    [
                        ("Recibidas", NEUTRO, recibidas),
                        ("Transacciones NS", AZUL_CLARO, [t.en_nivel_servicio for _, t in serie]),
                    ],
                    ("Nivel de servicio", [t.nivel_servicio for _, t in serie]),
                    f"{s.nombre}: recibidas, transacciones NS y nivel de servicio por mes {tramo}.",
                    interp.servicio(s, c),
                )
                self.grafico(
                    gc.lineas_niveles(
                        etiquetas,
                        [
                            ("Nivel de atención", AZUL, [t.nivel_atencion for _, t in serie]),
                            ("Nivel de servicio", AMARILLO, [t.nivel_servicio for _, t in serie]),
                        ],
                        resaltar,
                    ),
                    f"{s.nombre}: nivel de atención frente a nivel de servicio por mes {tramo}.",
                    interp.niveles_canal(s, c),
                )
                self._tabla_niveles(
                    serie,
                    f"{s.nombre} mes a mes {tramo}: recibidas, atendidas, transacciones NS, abandonadas, nivel de atención, nivel de servicio y nivel de abandono",
                    total_serie,
                    tramo_del_anio(c.periodo, mayuscula=True) if es_anio else "Total",
                )
                barras(
                    [("Abandonadas", ROJO, [t.abandonadas for _, t in serie])],
                    ("Nivel de abandono", [t.nivel_abandono for _, t in serie]),
                    f"{s.nombre}: abandonos y nivel de abandono por mes {tramo}.",
                    interp.abandonos(s, c),
                )
            elif s.tipo == "chatbot":
                barras(
                    [
                        ("Transacciones", NEUTRO, recibidas),
                        ("Conversaciones", AZUL_CLARO, [t.preguntas for _, t in serie]),
                    ],
                    ("Resolución", [t.resolucion for _, t in serie]),
                    f"Chatbot: transacciones, conversaciones y resolución por mes {tramo}.",
                    interp.chatbot_transacciones(s, c),
                )
                barras(
                    [
                        ("Resueltas sin agente", AZUL, [t.preguntas_resueltas for _, t in serie]),
                        ("Transferidas a un agente", ROJO, [t.preguntas_no_resueltas for _, t in serie]),
                    ],
                    ("Resolución", [t.resolucion for _, t in serie]),
                    f"Chatbot: resueltas y transferidas, apiladas, con la resolución por mes {tramo}.",
                    interp.chatbot_resueltas(s, c),
                    apiladas=True,
                )
            elif s.tipo == "callback":
                barras(
                    [(mayuscula_inicial(rec), NEUTRO, recibidas), ("Llamadas efectivas", AZUL, atendidas)],
                    ("Efectividad", [t.efectividad for _, t in serie]),
                    f"{s.nombre}: {rec}, llamadas efectivas y efectividad por mes {tramo}.",
                    interp.callback_efectivas(s, c),
                )
                barras(
                    [("No efectivas", ROJO, [t.abandonadas for _, t in serie])],
                    ("Tasa de no efectividad", [t.nivel_abandono for _, t in serie]),
                    f"{s.nombre}: llamadas no efectivas y tasa de no efectividad por mes {tramo}.",
                    interp.callback_no_efectivas(s, c),
                )
            else:
                promedio = s.acumulado.promedio_mensual
                self.grafico(
                    gc.barras_con_linea(etiquetas, [("Atenciones", AZUL, recibidas)], None, resaltar=resaltar),
                    f"Atención presencial: atenciones en ventanilla por mes {tramo}"
                    + (f" (promedio mensual: {decimal(promedio, 1)})." if promedio else "."),
                    interp.presencial(s, c),
                )
        # las vistas de volumen comunes: dos años, variación y media móvil
        nombre_rec = mayuscula_inicial(rec)
        if es_anio or (s.serie_anio and s.serie_anio_anterior):
            actual = {int(p[5:7]): t.recibidas for p, t in s.serie_anio}
            anterior = {int(p[5:7]): t.recibidas for p, t in s.serie_anio_anterior}
            self.grafico(
                gt.dos_anios(actual, anterior, anio, "entero", hasta=c.mes_numero),
                f"{s.nombre}: {rec} por mes, {anio}" + (f" frente a {anio - 1}." if anterior else "."),
                interp.dos_anios_recibidas(s, c),
            )
        if len(s.serie_13) >= 2:
            serie13 = s.serie_13
            valores = [None] + [
                ((serie13[i][1].recibidas / serie13[i - 1][1].recibidas - 1) * 100)
                if serie13[i - 1][1].recibidas
                else None
                for i in range(1, len(serie13))
            ]
            self.grafico(
                gt.barras_variacion(_etiquetas(serie13), valores, "%", recorte=RECORTE_VARIACION),
                f"{s.nombre}: variación de {rec} frente al mes anterior con datos, últimos {len(serie13)} meses con datos.",
                interp.variacion_mensual(s),
            )
        if any(s.media_movil.get(p) is not None for p, _ in s.serie_13):
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, float(t.recibidas)) for p, t in s.serie_13],
                    [(p, s.media_movil.get(p)) for p, _ in s.serie_13],
                    c.periodo,
                    "entero",
                    nombre_rec,
                ),
                f"{s.nombre}: {rec} frente a su media móvil simple de tres meses, últimos {len(s.serie_13)} meses con datos.",
                interp.media_movil(s),
            )
        # los niveles frente al año anterior
        niveles = {
            "contacto": [
                ("nivel_atencion", "Nivel de atención"),
                ("nivel_servicio", "Nivel de servicio"),
                ("nivel_abandono", "Nivel de abandono"),
            ],
            "chatbot": [("resolucion", "Resolución")],
            "callback": [("efectividad", "Efectividad")],
            "presencial": [],
        }[s.tipo]
        if es_anio or (s.serie_anio and s.serie_anio_anterior):
            for campo, nombre in niveles:
                actual = {int(p[5:7]): getattr(t, campo) for p, t in s.serie_anio if getattr(t, campo) is not None}
                anterior = {
                    int(p[5:7]): getattr(t, campo) for p, t in s.serie_anio_anterior if getattr(t, campo) is not None
                }
                if not actual:
                    continue
                self.grafico(
                    gt.dos_anios(
                        actual,
                        anterior,
                        anio,
                        "porcentaje",
                        hasta=c.mes_numero,
                        leyenda="upper right" if campo == "nivel_abandono" else "lower left",
                    ),
                    f"{s.nombre}: {nombre.lower()} por mes, {anio}" + (f" frente a {anio - 1}." if anterior else "."),
                    interp.nivel_anual(s, c, campo),
                )

    # --- anexos ---------------------------------------------------------------------------------------------------
    def _anexos(self) -> None:
        c = self.calculo
        anio = c.anio
        mes = mes_y_anio(c.periodo)
        self.titulo1("Anexo A. Interacciones por canal y mes")
        self.p(interp.anexo(c), "Bajada")
        meses = [p for p, _ in c.todos.serie_anio]
        encabezados = ["Canal", *[mayuscula_inicial(mes_corto(p)[:3]) for p in meses], "Total"]
        filas = []
        for s in c.canales:
            if not s.serie_anio:
                continue
            valores = dict(s.serie_anio)
            filas.append(
                [
                    NOMBRES_CORTOS.get(s.nombre, s.nombre),
                    *[entero(valores[p].recibidas) if p in valores else GUION for p in meses],
                    entero(s.acumulado.recibidas),
                ]
            )
        totales = dict(c.todos.serie_anio)
        filas.append(["Total", *[entero(totales[p].recibidas) for p in meses], entero(c.todos.acumulado.recibidas)])
        self.tabla(
            f"Interacciones recibidas por canal y mes, {anio}",
            encabezados,
            filas,
            [1.1, *[0.7] * len(meses), 0.8],
            numericas=set(range(1, len(encabezados))),
            resaltar=len(filas) - 1,
        )
        self.titulo1("Anexo B. Ficha técnica")
        generado = fecha_generacion(self.procedencia)
        con_datos = [s for s in c.canales if s.mes]
        filas = [
            ["Informe", f"{TITULO_INFORME}, {mes}"],
            ["Entidad", f"{ENTIDAD}, {AREA}"],
            [
                "Fuente",
                "Tablas mensuales del centro de contacto del Ministerio y tabla de trámites (atención presencial); desde agosto de 2026, el "
                "informe mensual de gestión del operador del centro de contacto",
            ],
            ["Corte de los datos", fecha_larga(c.fecha_corte)],
            ["Datos publicados en la plataforma", fecha_larga(c.publicado_en[:10])],
            ["Versión del pipeline", c.version_pipeline or GUION],
            [
                "Universo del mes",
                f"{entero(c.todos.mes.recibidas)} interacciones recibidas en {len(con_datos)} canales en {mes}",
            ],
            ["Histórico disponible", f"Desde {mes_y_anio(c.primer_periodo)}"],
            ["Informe interactivo", URL_INFORME],
            *filas_ficha(self.procedencia, "canales", "canales", c.periodo, "api/v1/canales/cubo.json"),
            ["Generado", f"{generado}, por la Plataforma de Analítica de Datos"],
        ]
        self.tabla("Ficha técnica del informe", ["Campo", "Valor"], filas, [1.8, 4.2])


def generar(calculo: Calculo, destino: Path, procedencia: Procedencia | None = None) -> Path:
    """Escribe el PDF del mes en `destino` y devuelve su ruta. Con la procedencia (D-81) la ficha técnica dice de qué
    exportación, commit y reglas salió, si la cifra es provisional y qué revisiones la tocan."""
    registrar_fuentes()
    c = calculo
    p = procedencia or Procedencia()
    textos = redactar(c, p.parametros)
    mes = mayuscula_inicial(mes_y_anio(c.periodo))
    k = c.contacto.mes
    portada = Portada(
        ["Informe de", "Canales de Atención"],
        mes,
        [
            "Niveles de atención y de servicio de los canales de contacto, y lo recibido",
            "y atendido en el chatbot, la devolución de llamadas y la atención presencial",
        ],
        fecha_larga(c.fecha_corte),
        [
            (entero(c.todos.mes.recibidas), "interacciones recibidas en el mes"),
            (_pct(k.nivel_atencion) if k else GUION, "nivel de atención (contacto)"),
            (_pct(k.nivel_servicio) if k else GUION, "nivel de servicio (contacto)"),
        ],
        textos.hallazgos,
        URL_INFORME,
        nota_corte=nota_cifra(p, "canales", c.periodo),
    )
    cabecera = Cabecera(TITULO_INFORME, mes, fecha_larga(c.fecha_corte))
    historia = _Constructor(c, textos, p).construir()
    return generar_pdf(
        destino,
        portada,
        cabecera,
        historia,
        f"{TITULO_INFORME} · {mes}",
        "Niveles de atención y de servicio de los canales de atención",
    )
