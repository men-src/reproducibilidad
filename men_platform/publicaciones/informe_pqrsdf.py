"""El Informe General de PQRSDF de un mes en PDF (D-73): portada, tabla de contenido, resumen ejecutivo, objetivos,
metodología, glosario de términos y siglas, resultados, observaciones, recomendaciones, conclusiones y anexos, sobre
la base común de documento.py (carta, Inter, la paleta de la plataforma, «Página X de Y»; cada título y cada subtítulo
empieza en una página nueva y cada gráfico y cada tabla lleva su interpretación)."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from men_platform.publicaciones import graficos_pqrsdf as g
from men_platform.publicaciones import graficos_tablero as gt
from men_platform.publicaciones import interpretaciones_pqrsdf as interp
from men_platform.publicaciones import interpretaciones_tablero as it
from men_platform.publicaciones.datos_pqrsdf import Calculo, Totales
from men_platform.publicaciones.documento import (  # noqa: F401 - ALTO_MINIATURA, dibujar_cabecera_portada y registrar_fuentes se reexportan
    ALTO_MINIATURA,
    AREA,
    ENTIDAD,
    Cabecera,
    Constructor,
    Portada,
    dibujar_cabecera_portada,
    generar_pdf,
    registrar_fuentes,
)
from men_platform.publicaciones.procedencia import Procedencia, fecha_generacion, filas_ficha, nota_cifra
from men_platform.publicaciones.redaccion_pqrsdf import Textos, cambios_por_dependencia, redactar
from men_platform.publicaciones.texto_es import (
    capitalizar,
    decimal,
    entero,
    fecha_larga,
    mayuscula_inicial,
    mes_corto,
    mes_corto_2,
    mes_y_anio,
    mes_y_anio_siguiente,
    nombre_mes,
    nombre_propio,
    porcentaje,
    puntos,
    tramo_del_anio,
    variacion,
)

TITULO_INFORME = "Informe General de PQRSDF"
URL_INFORME = "https://men-src.github.io/pqrsdf/"


class _Constructor(Constructor):
    """Las secciones del Informe General de PQRSDF sobre la base común."""

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
        self._objetivos()
        self._metodologia()
        self._glosario()
        self._resultados()
        self.titulo1("6. Observaciones")
        self.p(
            "Las observaciones salen de las cifras del mes y de su comparación con el mes anterior y con el propio historial de la entidad; cada una señala un hecho verificable en las tablas de este informe.",
            "Bajada",
        )
        self.lista(t.observaciones)
        self.titulo1("7. Recomendaciones")
        self.p(
            "Las recomendaciones responden a las observaciones anteriores y se dirigen a la entidad: a la alta dirección, a las dependencias que responden y a las áreas que acompañan la atención a la ciudadanía.",
            "Bajada",
        )
        self.lista(t.recomendaciones, numerada=True)
        self.titulo1("8. Conclusiones")
        for parrafo in t.conclusiones:
            self.p(escape(parrafo))
        self._anexos()
        return self.historia

    def _resumen(self) -> None:
        t = self.textos
        self.titulo1("1. Resumen ejecutivo")
        for parrafo in t.resumen:
            self.p(escape(parrafo))
        self.espacio(0.2)
        self._tarjetas_indicadores()

    def _tarjetas_indicadores(self) -> None:
        """Ocho tarjetas de resultados en dos filas: el valor del mes y, debajo, el mes anterior, el mismo mes del año anterior y el año."""
        c = self.calculo
        m, ant, mismo, acu = c.mes, c.mes_anterior, c.mismo_mes_anterior, c.acumulado
        mes_ant = mayuscula_inicial(mes_corto(c.periodo_anterior_str())) if ant else None
        mes_mismo = f"{mayuscula_inicial(mes_corto(c.periodo)[:3])} {c.anio - 1}"

        def tarjeta(titulo: str, f, variacion_fn) -> list:  # noqa: ANN001
            lineas = []
            if ant:
                lineas.append(f"{mes_ant}: {f(ant)} ({variacion_fn(m, ant)})")
            if mismo:
                lineas.append(f"{mes_mismo}: {f(mismo)} ({variacion_fn(m, mismo)})")
            lineas.append(f"Año {c.anio}: {f(acu)}")
            return self.tarjeta(titulo, f(m), lineas)

        def var_entero(atributo: str):  # noqa: ANN202
            return lambda a, b: variacion(getattr(a, atributo), getattr(b, atributo))

        def var_pp(atributo: str):  # noqa: ANN202
            return lambda a, b: puntos((getattr(a, atributo) or 0) - (getattr(b, atributo) or 0))

        def var_dias(atributo: str):  # noqa: ANN202
            def f(a: Totales, b: Totales) -> str:
                d = (getattr(a, atributo) or 0) - (getattr(b, atributo) or 0)
                return ("+" if d > 0 else "−" if d < 0 else "") + decimal(abs(d), 1) + " días"

            return f

        tarjetas = [
            tarjeta("PQRSDF gestionadas", lambda t: entero(t.radicados), var_entero("radicados")),
            tarjeta("Respondidas a tiempo", lambda t: entero(t.a_tiempo), var_entero("a_tiempo")),
            tarjeta("Extemporáneas", lambda t: entero(t.extemporaneas), var_entero("extemporaneas")),
            tarjeta(
                "Extemporáneas abiertas al corte",
                lambda t: entero(t.abiertas_vencidas),
                var_entero("abiertas_vencidas"),
            ),
            tarjeta("Oportunidad de respuesta", lambda t: porcentaje(t.oportunidad), var_pp("oportunidad")),
            tarjeta(
                "Tasa de extemporaneidad", lambda t: porcentaje(t.tasa_extemporaneas), var_pp("tasa_extemporaneas")
            ),
            tarjeta(
                "Días hábiles de gestión (promedio)",
                lambda t: decimal(t.promedio_dias_gestion, 1),
                var_dias("promedio_dias_gestion"),
            ),
            tarjeta(
                "Días hábiles de retraso (promedio)",
                lambda t: decimal(t.promedio_dias_retraso, 1),
                var_dias("promedio_dias_retraso"),
            ),
        ]
        self.tarjetas("Tarjetas de resultados del mes y sus comparaciones", tarjetas)
        self.interpretacion(interp.indicadores_tabla(c))

    def _objetivos(self) -> None:
        t = self.textos
        self.titulo1("2. Objetivos")
        self.p("<b>Objetivo general.</b> " + escape(t.objetivo_general))
        self.espacio(0.2)
        self.p("<b>Objetivos específicos.</b>")
        self.lista(t.objetivos_especificos, numerada=True)

    def _metodologia(self) -> None:
        self.titulo1("3. Metodología")
        for subtitulo, texto in self.textos.metodologia:
            self.p(f"<b>{escape(subtitulo)}.</b> {escape(texto)}")

    def _glosario(self) -> None:
        self.glosario(4, self.textos.glosario, self.textos.siglas)

    def _resultados(self) -> None:  # noqa: PLR0915 - un apartado por tema, en orden de lectura
        c = self.calculo
        m = c.mes
        mes = mes_y_anio(c.periodo)
        mes_ant = nombre_mes(c.periodo_anterior_str())
        anio, anio_ant = c.anio, c.anio - 1
        n = 5
        etiquetas_13 = [mes_corto_2(p) for p, _ in c.serie_13]
        # en los primeros meses del histórico no hay variación mensual, media móvil ni mapa de calor que mostrar
        hay_variacion = len(c.serie_13) >= 2
        hay_media_movil = any(c.media_movil_oportunidad.get(p) is not None for p, _ in c.serie_13)
        hay_mapa_calor = sum(len(meses) for meses in c.matriz_oportunidad.values()) > 1
        hay_anio_anterior = bool(c.serie_anio_anterior)
        comparado = f"{anio} frente a {anio_ant}" if hay_anio_anterior else str(anio)
        sufijo_comparado = f": {comparado}" if hay_anio_anterior else f", {anio}"

        def comparada(
            encabezados: list[str], filas: list[list[str]], anchos: list[float], quitar: set[int], numericas: set[int]
        ) -> tuple[list[str], list[list[str]], list[float], set[int]]:
            """Sin año anterior, la tabla pierde las columnas que lo comparan."""
            if hay_anio_anterior:
                return encabezados, filas, anchos, numericas
            dejar = [i for i in range(len(encabezados)) if i not in quitar]
            return (
                [encabezados[i] for i in dejar],
                [[f[i] for i in dejar] for f in filas],
                [anchos[i] for i in dejar],
                {dejar.index(i) for i in numericas if i in dejar},
            )

        self.titulo1(f"{n}. Resultados")
        self.p(
            f"Esta sección recorre la gestión de las PQRSDF de {mes} por apartados: el resumen del mes, la comparación con "
            "el mes inmediatamente anterior y, después, el porcentaje de oportunidad, el volumen general, el volumen a tiempo, el volumen extemporáneo, los "
            "requerimientos, los ejes temáticos y el canal de radicación; cierra con los tiempos de gestión. Cada gráfico y cada tabla van seguidos de su lectura."
        )

        # --- resumen del mes ---------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.1 Resumen del mes",
            f"Cómo quedaron las {entero(m.radicados)} PQRSDF gestionadas en {mes} al corte del {fecha_larga(c.fecha_corte)}, cómo fue el año mes a mes y qué dependencias concentraron la gestión.",
        )
        self.grafico(
            g.estados_del_mes(m), f"PQRSDF gestionadas en {mes}: a tiempo y extemporáneas.", interp.estados_grafico(c)
        )
        cerradas_ext = max(0, m.extemporaneas - m.abiertas_vencidas)
        filas = [
            ["A tiempo", entero(m.a_tiempo), porcentaje(m.a_tiempo / m.radicados if m.radicados else None)],
            [
                "Extemporáneas",
                entero(m.extemporaneas),
                porcentaje(m.extemporaneas / m.radicados if m.radicados else None),
            ],
            [
                "    cerradas después del plazo",
                entero(cerradas_ext),
                porcentaje(cerradas_ext / m.radicados if m.radicados else None),
            ],
            [
                "    abiertas al corte",
                entero(m.abiertas_vencidas),
                porcentaje(m.abiertas_vencidas / m.radicados if m.radicados else None),
            ],
            ["Total gestionadas en el mes", entero(m.radicados), porcentaje(1.0)],
        ]
        self.tabla(
            f"Estado de las PQRSDF gestionadas en {mes}",
            ["Estado", "PQRSDF", "Participación"],
            filas,
            [3, 1.2, 1.2],
            lectura=interp.estados_tabla(c),
            numericas={1, 2},
            resaltar=4,
        )
        self.grafico(
            gt.mes_a_mes(c.serie_anio, c.periodo),
            f"Mes a mes en {anio}: a tiempo, extemporáneas y porcentaje de oportunidad.",
            it.mes_a_mes(c),
        )
        filas = [
            [
                mayuscula_inicial(nombre_mes(p)),
                entero(t.radicados),
                entero(t.a_tiempo),
                entero(t.extemporaneas),
                porcentaje(t.oportunidad),
                decimal(t.promedio_dias_gestion, 1),
            ]
            for p, t in c.serie_anio
        ]
        acu = c.acumulado
        filas.append(
            [
                tramo_del_anio(c.periodo, mayuscula=True),
                entero(acu.radicados),
                entero(acu.a_tiempo),
                entero(acu.extemporaneas),
                porcentaje(acu.oportunidad),
                decimal(acu.promedio_dias_gestion, 1),
            ]
        )
        self.tabla(
            f"Volumen y oportunidad por mes de {anio}",
            ["Mes", "Gestionadas", "A tiempo", "Extemporáneas", "Oportunidad", "Días de gestión"],
            filas,
            [2.2, 1.3, 1.2, 1.3, 1.2, 1.3],
            lectura=interp.volumen_tabla(c),
            numericas={1, 2, 3, 4, 5},
            resaltar=len(filas) - 1,
        )
        top = [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"][:10]
        self.grafico(
            g.barras_horizontales([(k, (t.oportunidad or 0) * 100) for k, t in top], "porcentaje", limite_pct=True),
            f"Oportunidad de las diez dependencias con mayor volumen, {mes}.",
            interp.dependencias_grafico(c),
        )
        acumulado_dep = dict(c.por_dependencia_acumulado)
        filas = []
        for k, t in [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"][:15]:
            ac = acumulado_dep.get(k)
            filas.append(
                [
                    nombre_propio(k),
                    entero(t.radicados),
                    entero(t.a_tiempo),
                    entero(t.extemporaneas),
                    porcentaje(t.oportunidad),
                    porcentaje(ac.oportunidad) if ac else "–",
                ]
            )
        self.tabla(
            f"Dependencias y grupos: las quince de mayor volumen en {mes}",
            ["Dependencia", "Gestionadas", "A tiempo", "Extemp.", "Oport. mes", "Oport. año"],
            filas,
            [3.4, 1.1, 1, 0.9, 1.1, 1.1],
            lectura=interp.dependencias_tabla(c),
            numericas={1, 2, 3, 4, 5},
        )
        filas = []
        for k, t in c.por_grupo[:10]:
            unidad, dependencia = k.split("|", 1)
            filas.append(
                [
                    nombre_propio(unidad),
                    nombre_propio(dependencia),
                    entero(t.radicados),
                    entero(t.extemporaneas),
                    porcentaje(t.oportunidad),
                ]
            )
        if filas:
            self.tabla(
                f"Los grupos internos de trabajo con mayor volumen en {mes}",
                ["Grupo interno", "Dependencia", "Gestionadas", "Extemp.", "Oportunidad"],
                filas,
                [3, 2.5, 1.1, 1, 1.1],
                lectura=interp.grupos_tabla(c),
                numericas={2, 3, 4},
            )

        # --- comparación con el mes anterior ------------------------------------------------------------------
        if c.mes_anterior is None:
            self.titulo2(
                f"{n}.2 Comparación con el mes inmediatamente anterior",
                f"{mayuscula_inicial(mes)} es el primer mes del histórico de la plataforma: no hay un mes anterior con datos para comparar.",
            )
        else:
            self.titulo2(
                f"{n}.2 Comparación con {mes_ant}, el mes inmediatamente anterior",
                f"Qué cambió entre {mes_ant} y {nombre_mes(c.periodo)} de {anio} en volumen, oportunidad, extemporáneas, tiempos y dependencias.",
            )
        ant = c.mes_anterior
        if ant:
            self.grafico(
                g.comparacion_dos_meses(
                    ant, m, mayuscula_inicial(mes_y_anio(c.periodo_anterior_str())), mayuscula_inicial(mes)
                ),
                f"PQRSDF gestionadas, a tiempo y extemporáneas: {mes_ant} frente a {nombre_mes(c.periodo)} de {anio}.",
                interp.mes_anterior_grafico(c),
            )

            def dias(a: float | None, b: float | None) -> str:
                d = (b or 0) - (a or 0)
                return ("+" if d > 0 else "−" if d < 0 else "") + decimal(abs(d), 1)

            indicadores = [
                [
                    "PQRSDF gestionadas",
                    entero(ant.radicados),
                    entero(m.radicados),
                    variacion(m.radicados, ant.radicados),
                ],
                ["Respondidas a tiempo", entero(ant.a_tiempo), entero(m.a_tiempo), variacion(m.a_tiempo, ant.a_tiempo)],
                [
                    "Extemporáneas",
                    entero(ant.extemporaneas),
                    entero(m.extemporaneas),
                    variacion(m.extemporaneas, ant.extemporaneas),
                ],
                [
                    "Extemporáneas abiertas al corte",
                    entero(ant.abiertas_vencidas),
                    entero(m.abiertas_vencidas),
                    variacion(m.abiertas_vencidas, ant.abiertas_vencidas),
                ],
                [
                    "Oportunidad de respuesta",
                    porcentaje(ant.oportunidad),
                    porcentaje(m.oportunidad),
                    puntos((m.oportunidad or 0) - (ant.oportunidad or 0)),
                ],
                [
                    "Tasa de extemporaneidad",
                    porcentaje(ant.tasa_extemporaneas),
                    porcentaje(m.tasa_extemporaneas),
                    puntos((m.tasa_extemporaneas or 0) - (ant.tasa_extemporaneas or 0)),
                ],
                [
                    "Días hábiles de gestión (promedio)",
                    decimal(ant.promedio_dias_gestion, 1),
                    decimal(m.promedio_dias_gestion, 1),
                    dias(ant.promedio_dias_gestion, m.promedio_dias_gestion),
                ],
                [
                    "Días hábiles de retraso (promedio)",
                    decimal(ant.promedio_dias_retraso, 1),
                    decimal(m.promedio_dias_retraso, 1),
                    dias(ant.promedio_dias_retraso, m.promedio_dias_retraso),
                ],
            ]
            self.tabla(
                f"Indicadores de {mes_ant} y de {nombre_mes(c.periodo)} de {anio} y su variación",
                [
                    "Indicador",
                    mayuscula_inicial(mes_corto(c.periodo_anterior_str())),
                    mayuscula_inicial(mes_corto(c.periodo)),
                    "Variación",
                ],
                indicadores,
                [3.2, 1.3, 1.3, 1.3],
                lectura=interp.mes_anterior_tabla(c),
                numericas={1, 2, 3},
            )
            mejoras, retrocesos = cambios_por_dependencia(c)
            filas = []
            for k, d, a, t in retrocesos[:5]:
                filas.append(
                    [
                        nombre_propio(k),
                        entero(a.radicados),
                        porcentaje(a.oportunidad),
                        entero(t.radicados),
                        porcentaje(t.oportunidad),
                        puntos(d),
                    ]
                )
            for k, d, a, t in mejoras[:5]:
                filas.append(
                    [
                        nombre_propio(k),
                        entero(a.radicados),
                        porcentaje(a.oportunidad),
                        entero(t.radicados),
                        porcentaje(t.oportunidad),
                        puntos(d),
                    ]
                )
            if filas:
                abrev_ant, abrev = mes_corto(c.periodo_anterior_str())[:3], mes_corto(c.periodo)[:3]
                self.tabla(
                    f"Dependencias con mayor cambio de oportunidad frente a {mes_ant} (al menos 50 PQRSDF en ambos meses): retrocesos y mejoras",
                    [
                        "Dependencia",
                        f"Gest. {abrev_ant}",
                        f"Oport. {abrev_ant}",
                        f"Gest. {abrev}",
                        f"Oport. {abrev}",
                        "Diferencia",
                    ],
                    filas,
                    [3.2, 1, 1.1, 1, 1.1, 1.1],
                    lectura=interp.cambio_dependencias_tabla(c, mejoras, retrocesos),
                    numericas={1, 2, 3, 4, 5},
                )
        else:
            self.p(f"La comparación con el mes anterior empieza en el informe de {mes_y_anio_siguiente(c.periodo)}.")

        # --- % de oportunidad -----------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.3 Porcentaje de oportunidad",
            "El índice del mes frente al año anterior, su variación mes a mes, el mapa de calor del histórico"
            + (", la media móvil y el pronóstico." if c.pronostico else " y la media móvil."),
        )
        actual_op = {int(p[5:7]): t.oportunidad for p, t in c.serie_anio}
        anterior_op = {int(p[5:7]): t.oportunidad for p, t in c.serie_anio_anterior}
        self.grafico(
            gt.dos_anios(actual_op, anterior_op, anio, "porcentaje", hasta=c.mes_numero),
            f"Porcentaje de oportunidad por mes{sufijo_comparado}.",
            interp.dos_anios_grafico(c),
        )
        anterior_por_mes = {int(p[5:7]): t for p, t in c.serie_anio_anterior}
        filas = []
        for p, t in c.serie_anio:
            a = anterior_por_mes.get(int(p[5:7]))
            filas.append(
                [
                    mayuscula_inicial(nombre_mes(p)),
                    porcentaje(t.oportunidad),
                    porcentaje(a.oportunidad) if a else "–",
                    puntos((t.oportunidad or 0) - (a.oportunidad or 0)) if a else "–",
                ]
            )
        if c.acumulado_anterior:
            filas.append(
                [
                    tramo_del_anio(c.periodo, mayuscula=True),
                    porcentaje(acu.oportunidad),
                    porcentaje(c.acumulado_anterior.oportunidad),
                    puntos((acu.oportunidad or 0) - (c.acumulado_anterior.oportunidad or 0)),
                ]
            )
        enc, fil, anc, num = comparada(
            ["Mes", str(anio), str(anio_ant), "Diferencia"], filas, [2.2, 1.3, 1.3, 1.3], {2, 3}, {1, 2, 3}
        )
        self.tabla(
            f"Oportunidad por mes, {comparado}",
            enc,
            fil,
            anc,
            lectura=interp.dos_anios_tabla(c),
            numericas=num,
            resaltar=len(filas) - 1 if c.acumulado_anterior else None,
        )
        cambios = [None] + [
            ((c.serie_13[i][1].oportunidad or 0) - (c.serie_13[i - 1][1].oportunidad or 0)) * 100
            for i in range(1, len(c.serie_13))
        ]
        if hay_variacion:
            self.grafico(
                gt.barras_variacion(etiquetas_13, cambios, "pp"),
                "Variación del índice frente al mes anterior, en puntos porcentuales, últimos trece meses.",
                it.variacion_mensual(c, "oportunidad"),
            )
        if hay_mapa_calor:
            self.grafico(
                gt.mapa_calor(c.matriz_oportunidad, (anio, c.mes_numero), hasta=c.mes_numero),
                f"Mapa de calor del porcentaje de oportunidad por mes y año, {'en' if c.mes_numero == 1 else 'de'} {tramo_del_anio(c.periodo)} de cada año.",
                it.mapa_calor(c),
            )
        if hay_media_movil:
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, t.oportunidad) for p, t in c.serie_13],
                    [(p, c.media_movil_oportunidad.get(p)) for p, _ in c.serie_13],
                    c.periodo,
                    "porcentaje",
                    "Oportunidad",
                ),
                "Oportunidad de cada mes frente a su media móvil de los tres meses anteriores.",
                it.media_movil(c, "oportunidad"),
            )
        if c.pronostico:
            self.grafico(
                g.real_vs_pronostico(c.pronostico),
                f"Oportunidad real frente al pronóstico del modelo {c.modelo_pronostico.upper()}, {anio}.",
                interp.pronostico_grafico(c),
            )
            filas = [
                [
                    mayuscula_inicial(nombre_mes(p)),
                    porcentaje(r),
                    porcentaje(v),
                    puntos(r - v) if r is not None else "–",
                ]
                for p, r, v in c.pronostico
            ]
            self.tabla(
                f"Oportunidad real y pronosticada por mes, {anio}",
                ["Mes", "Real", "Pronóstico", "Diferencia"],
                filas,
                [2, 1.2, 1.2, 1.2],
                lectura=interp.pronostico_tabla(c),
                numericas={1, 2, 3},
                resaltar=len(filas) - 1,
            )

        # --- volumen general --------------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.4 Volumen general",
            "Cuántas PQRSDF se gestionaron cada mes, frente al año anterior, al mes anterior y a su media móvil.",
        )
        self.grafico(
            gt.dos_anios(
                {int(p[5:7]): t.radicados for p, t in c.serie_anio},
                {int(p[5:7]): t.radicados for p, t in c.serie_anio_anterior},
                anio,
                "entero",
                hasta=c.mes_numero,
            ),
            f"Total general por mes{sufijo_comparado}.",
            it.dos_anios_campo(c, "radicados"),
        )
        filas = []
        for p, t in c.serie_anio:
            a = anterior_por_mes.get(int(p[5:7]))
            filas.append(
                [
                    mayuscula_inicial(nombre_mes(p)),
                    entero(t.radicados),
                    entero(a.radicados) if a else "–",
                    variacion(t.radicados, a.radicados if a else None),
                ]
            )
        if c.acumulado_anterior:
            filas.append(
                [
                    tramo_del_anio(c.periodo, mayuscula=True),
                    entero(acu.radicados),
                    entero(c.acumulado_anterior.radicados),
                    variacion(acu.radicados, c.acumulado_anterior.radicados),
                ]
            )
        enc, fil, anc, num = comparada(
            ["Mes", str(anio), str(anio_ant), "Variación"], filas, [2.2, 1.3, 1.3, 1.3], {2, 3}, {1, 2, 3}
        )
        self.tabla(
            f"Total general por mes, {comparado}",
            enc,
            fil,
            anc,
            numericas=num,
            resaltar=len(filas) - 1 if c.acumulado_anterior else None,
        )
        cambios = [None] + [
            ((c.serie_13[i][1].radicados - c.serie_13[i - 1][1].radicados) / c.serie_13[i - 1][1].radicados * 100)
            if c.serie_13[i - 1][1].radicados
            else None
            for i in range(1, len(c.serie_13))
        ]
        if hay_variacion:
            self.grafico(
                gt.barras_variacion(etiquetas_13, cambios, "%"),
                "Variación del total general frente al mes anterior, últimos trece meses.",
                it.variacion_mensual(c, "radicados"),
            )
        if hay_media_movil:
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, t.radicados) for p, t in c.serie_13],
                    [(p, c.media_movil_radicados.get(p)) for p, _ in c.serie_13],
                    c.periodo,
                    "entero",
                    "Total general",
                ),
                "Total general de cada mes frente a su media móvil de los tres meses anteriores.",
                it.media_movil(c, "radicados"),
            )

        # --- volumen a tiempo -------------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.5 Volumen a tiempo",
            "Cuántas PQRSDF se respondieron a tiempo cada mes, frente al total, al año anterior, al mes anterior y a su media móvil.",
        )
        self.grafico(
            gt.brecha(c.serie_anio, "a_tiempo", "A tiempo", g.AZUL, c.periodo),
            f"Total general y a tiempo por mes en {anio}, con la parte a tiempo.",
            it.brecha(c, "a_tiempo"),
        )
        self.grafico(
            gt.dos_anios(
                {int(p[5:7]): t.a_tiempo for p, t in c.serie_anio},
                {int(p[5:7]): t.a_tiempo for p, t in c.serie_anio_anterior},
                anio,
                "entero",
                hasta=c.mes_numero,
            ),
            f"Volumen a tiempo por mes{sufijo_comparado}.",
            it.dos_anios_campo(c, "a_tiempo"),
        )
        filas = []
        for p, t in c.serie_anio:
            a = anterior_por_mes.get(int(p[5:7]))
            filas.append(
                [
                    mayuscula_inicial(nombre_mes(p)),
                    entero(t.radicados),
                    entero(t.a_tiempo),
                    porcentaje(t.oportunidad),
                    entero(a.a_tiempo) if a else "–",
                    variacion(t.a_tiempo, a.a_tiempo if a else None),
                ]
            )
        filas.append(
            [
                tramo_del_anio(c.periodo, mayuscula=True),
                entero(acu.radicados),
                entero(acu.a_tiempo),
                porcentaje(acu.oportunidad),
                entero(c.acumulado_anterior.a_tiempo) if c.acumulado_anterior else "–",
                variacion(acu.a_tiempo, c.acumulado_anterior.a_tiempo if c.acumulado_anterior else None),
            ]
        )
        enc, fil, anc, num = comparada(
            ["Mes", "Total general", f"A tiempo {anio}", "Parte", f"A tiempo {anio_ant}", "Variación"],
            filas,
            [2, 1.2, 1.2, 1, 1.2, 1.1],
            {4, 5},
            {1, 2, 3, 4, 5},
        )
        self.tabla(
            f"Volumen a tiempo por mes, {comparado}",
            enc,
            fil,
            anc,
            numericas=num,
            resaltar=len(filas) - 1,
        )
        cambios = [None] + [
            ((c.serie_13[i][1].a_tiempo - c.serie_13[i - 1][1].a_tiempo) / c.serie_13[i - 1][1].a_tiempo * 100)
            if c.serie_13[i - 1][1].a_tiempo
            else None
            for i in range(1, len(c.serie_13))
        ]
        if hay_variacion:
            self.grafico(
                gt.barras_variacion(etiquetas_13, cambios, "%"),
                "Variación del volumen a tiempo frente al mes anterior, últimos trece meses.",
                it.variacion_mensual(c, "a_tiempo"),
            )
        if hay_media_movil:
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, t.a_tiempo) for p, t in c.serie_13],
                    [(p, c.media_movil_a_tiempo.get(p)) for p, _ in c.serie_13],
                    c.periodo,
                    "entero",
                    "A tiempo",
                ),
                "Volumen a tiempo de cada mes frente a su media móvil de los tres meses anteriores.",
                it.media_movil(c, "a_tiempo"),
            )

        # --- volumen extemporáneo ---------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.6 Volumen extemporáneo",
            "Cuántas PQRSDF quedaron extemporáneas cada mes, su tasa sobre el total y qué dependencias y grupos las concentran.",
        )
        self.grafico(
            gt.brecha(c.serie_anio, "extemporaneas", "Extemporáneas", g.ROJO, c.periodo),
            f"Total general y extemporáneas por mes en {anio}, con la tasa de extemporaneidad.",
            it.brecha(c, "extemporaneas"),
        )
        self.grafico(
            gt.dos_anios(
                {int(p[5:7]): t.extemporaneas for p, t in c.serie_anio},
                {int(p[5:7]): t.extemporaneas for p, t in c.serie_anio_anterior},
                anio,
                "entero",
                hasta=c.mes_numero,
            ),
            f"Volumen extemporáneo por mes{sufijo_comparado}.",
            it.dos_anios_campo(c, "extemporaneas", menor_mejor=True),
        )
        filas = []
        for p, t in c.serie_anio:
            a = anterior_por_mes.get(int(p[5:7]))
            filas.append(
                [
                    mayuscula_inicial(nombre_mes(p)),
                    entero(t.radicados),
                    entero(t.extemporaneas),
                    porcentaje(t.tasa_extemporaneas),
                    entero(a.extemporaneas) if a else "–",
                    porcentaje(a.tasa_extemporaneas) if a else "–",
                ]
            )
        filas.append(
            [
                tramo_del_anio(c.periodo, mayuscula=True),
                entero(acu.radicados),
                entero(acu.extemporaneas),
                porcentaje(acu.tasa_extemporaneas),
                entero(c.acumulado_anterior.extemporaneas) if c.acumulado_anterior else "–",
                porcentaje(c.acumulado_anterior.tasa_extemporaneas) if c.acumulado_anterior else "–",
            ]
        )
        enc, fil, anc, num = comparada(
            ["Mes", "Total general", f"Extemp. {anio}", f"Tasa {anio}", f"Extemp. {anio_ant}", f"Tasa {anio_ant}"],
            filas,
            [2, 1.2, 1.2, 1.1, 1.2, 1.1],
            {4, 5},
            {1, 2, 3, 4, 5},
        )
        self.tabla(
            f"Volumen extemporáneo y tasa por mes, {comparado}",
            enc,
            fil,
            anc,
            numericas=num,
            resaltar=len(filas) - 1,
        )
        cambios = [None] + [
            (
                (c.serie_13[i][1].extemporaneas - c.serie_13[i - 1][1].extemporaneas)
                / c.serie_13[i - 1][1].extemporaneas
                * 100
            )
            if c.serie_13[i - 1][1].extemporaneas
            else None
            for i in range(1, len(c.serie_13))
        ]
        if hay_variacion:
            self.grafico(
                gt.barras_variacion(etiquetas_13, cambios, "%", menor_mejor=True),
                "Variación del volumen extemporáneo frente al mes anterior, últimos trece meses: rojo si sube, azul si baja.",
                it.variacion_mensual(c, "extemporaneas", menor_mejor=True),
            )
        if hay_media_movil:
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, t.extemporaneas) for p, t in c.serie_13],
                    [(p, c.media_movil_extemporaneas.get(p)) for p, _ in c.serie_13],
                    c.periodo,
                    "entero",
                    "Extemporáneas",
                ),
                "Volumen extemporáneo de cada mes frente a su media móvil de los tres meses anteriores.",
                it.media_movil(c, "extemporaneas"),
            )
        self.grafico(
            gt.dos_anios(
                {int(p[5:7]): t.tasa_extemporaneas for p, t in c.serie_anio},
                {int(p[5:7]): t.tasa_extemporaneas for p, t in c.serie_anio_anterior},
                anio,
                "porcentaje",
                hasta=c.mes_numero,
            ),
            f"Tasa de extemporaneidad por mes{sufijo_comparado}.",
            it.dos_anios_campo(c, "tasa_extemporaneas", menor_mejor=True),
        )
        cambios = [None] + [
            ((c.serie_13[i][1].tasa_extemporaneas or 0) - (c.serie_13[i - 1][1].tasa_extemporaneas or 0)) * 100
            for i in range(1, len(c.serie_13))
        ]
        if hay_variacion:
            self.grafico(
                gt.barras_variacion(etiquetas_13, cambios, "pp", menor_mejor=True),
                "Variación de la tasa de extemporaneidad frente al mes anterior, en puntos porcentuales: rojo si sube, azul si baja.",
                it.variacion_mensual(c, "tasa_extemporaneas", menor_mejor=True),
            )
        deps_ext = sorted(
            [(k, t) for k, t in c.por_dependencia if k != "sin dependencia" and t.extemporaneas],
            key=lambda kt: -kt[1].extemporaneas,
        )[:12]
        filas = [
            [
                nombre_propio(k),
                entero(t.radicados),
                entero(t.extemporaneas),
                entero(max(0, t.extemporaneas - t.abiertas_vencidas)),
                entero(t.abiertas_vencidas),
                porcentaje(t.tasa_extemporaneas),
            ]
            for k, t in deps_ext
        ]
        self.tabla(
            f"Dependencias con más extemporáneas en {mes}",
            ["Dependencia", "Gestionadas", "Extemp.", "Cerradas", "Abiertas", "Tasa"],
            filas,
            [3.4, 1.1, 1, 1, 1, 1],
            lectura=it.extemporaneas_dependencias(c),
            numericas={1, 2, 3, 4, 5},
        )
        grupos_ext = sorted([gr for gr in c.por_grupo if gr[1].extemporaneas], key=lambda gr: -gr[1].extemporaneas)[:8]
        filas = []
        for k, t in grupos_ext:
            unidad, dependencia = k.split("|", 1)
            filas.append(
                [
                    nombre_propio(unidad),
                    nombre_propio(dependencia),
                    entero(t.radicados),
                    entero(t.extemporaneas),
                    porcentaje(t.tasa_extemporaneas),
                ]
            )
        if filas:
            self.tabla(
                f"Grupos internos con más extemporáneas en {mes}",
                ["Grupo interno", "Dependencia", "Gestionadas", "Extemp.", "Tasa"],
                filas,
                [3, 2.5, 1.1, 1, 1],
                lectura=it.grupos_extemporaneas(c),
                numericas={2, 3, 4},
            )

        # --- requerimientos ---------------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.7 Requerimientos",
            "Qué tipos de requerimiento se gestionaron, cuánto pesa cada uno y cuáles se atendieron más a tiempo o fuera de plazo.",
        )
        tipos = [(k, t) for k, t in c.por_tipo if t.radicados > 0]
        self.grafico(
            gt.burbujas([(k, t.radicados, t.oportunidad) for k, t in tipos if k != "sin homologar"]),
            f"Volumen y oportunidad por tipo de requerimiento, {mes}.",
            it.requerimientos_burbujas(c),
        )
        self.grafico(
            g.barras_horizontales(
                [(capitalizar(k), t.radicados / m.radicados * 100 if m.radicados else 0) for k, t in tipos[:10]],
                "porcentaje",
            ),
            f"Participación de los diez tipos de mayor volumen en lo gestionado, {mes}.",
            interp.tipos_grafico(c),
        )
        acumulado_tipo = dict(c.por_tipo_acumulado)
        filas = [
            [
                capitalizar(k),
                entero(t.radicados),
                porcentaje(t.radicados / m.radicados if m.radicados else None, 1),
                entero(t.a_tiempo),
                entero(t.extemporaneas),
                porcentaje(t.oportunidad),
                porcentaje(acumulado_tipo[k].oportunidad) if k in acumulado_tipo else "–",
            ]
            for k, t in tipos
        ]
        self.tabla(
            f"PQRSDF gestionadas y oportunidad por tipo de requerimiento, {mes}",
            ["Tipo de requerimiento", "Gestionadas", "Particip.", "A tiempo", "Extemp.", "Oport. mes", "Oport. año"],
            filas,
            [2.6, 1.2, 0.9, 1, 0.9, 1, 1],
            lectura=interp.tipos_tabla(c),
            numericas={1, 2, 3, 4, 5, 6},
        )
        self.grafico(
            gt.flujos([(k, t.a_tiempo, t.extemporaneas) for k, t in tipos[:10]]),
            f"A tiempo y extemporáneas por tipo de requerimiento (los diez de mayor volumen), {mes}.",
            it.requerimientos_flujos(c),
        )

        # --- ejes temáticos ---------------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.8 Ejes temáticos",
            "De qué tratan las PQRSDF gestionadas: el detalle por eje, el peso de cada uno y el Pareto de los de mayor volumen.",
        )
        ejes = [(k, t) for k, t in c.por_eje if k != "sin eje tematico" and t.radicados > 0]
        filas = [
            [
                capitalizar(k),
                entero(t.radicados),
                porcentaje(t.radicados / m.radicados if m.radicados else None, 1),
                entero(t.a_tiempo),
                entero(t.extemporaneas),
                porcentaje(t.oportunidad),
            ]
            for k, t in ejes[:15]
        ]
        self.tabla(
            f"Resumen detallado: los quince ejes temáticos con más PQRSDF gestionadas, {mes}",
            ["Eje temático", "Gestionadas", "Particip.", "A tiempo", "Extemp.", "Oportunidad"],
            filas,
            [3.4, 1.2, 0.9, 1, 0.9, 1.1],
            lectura=interp.ejes_tabla(c),
            numericas={1, 2, 3, 4, 5},
        )
        self.grafico(
            g.barras_horizontales(
                [(capitalizar(k), t.radicados / m.radicados * 100 if m.radicados else 0) for k, t in ejes[:10]],
                "porcentaje",
            ),
            f"Participación de los diez ejes temáticos de mayor volumen, {mes}.",
            interp.ejes_grafico(c),
        )
        self.grafico(
            gt.pareto([(k, t.radicados) for k, t in ejes]),
            f"Pareto de los ejes temáticos por volumen, {mes}.",
            it.ejes_pareto(c),
        )

        # --- canal ------------------------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.9 Canal de radicación",
            "Por dónde entran las PQRSDF: la mezcla de canales mes a mes, la oportunidad de cada canal y qué tipo llega por cada uno.",
        )
        if c.por_canal:
            self.grafico(
                gt.mezcla_canales(c.canal_por_mes),
                f"Mezcla de canales de radicación por mes en {anio}.",
                it.canal_mezcla(c),
            )
            canales = [(k, t) for k, t in c.por_canal if t.radicados > 0]
            self.grafico(
                g.barras_horizontales(
                    [(capitalizar(k), (t.oportunidad or 0) * 100) for k, t in canales], "porcentaje", limite_pct=True
                ),
                f"Oportunidad de respuesta por canal, {mes}.",
                interp.canal_grafico(c),
            )
            filas = [
                [
                    capitalizar(k),
                    entero(t.radicados),
                    porcentaje(t.radicados / m.radicados if m.radicados else None, 1),
                    entero(t.a_tiempo),
                    entero(t.extemporaneas),
                    porcentaje(t.oportunidad),
                    decimal(t.promedio_dias_gestion, 1),
                ]
                for k, t in canales
            ]
            self.tabla(
                f"PQRSDF gestionadas y oportunidad por canal, {mes}",
                ["Canal", "Gestionadas", "Particip.", "A tiempo", "Extemp.", "Oportunidad", "Días"],
                filas,
                [2.4, 1.1, 1, 1, 0.9, 1.3, 0.8],
                lectura=interp.canal_tabla(c),
                numericas={1, 2, 3, 4, 5, 6},
            )
            nombres_canal = [k for k, _ in canales]
            filas = []
            for tipo, por_canal in c.tipos_por_canal[:10]:
                total = sum(por_canal.values()) or 1
                filas.append(
                    [
                        capitalizar(tipo),
                        entero(total),
                        *[porcentaje(por_canal.get(k, 0) / total, 1) for k in nombres_canal],
                    ]
                )
            self.tabla(
                f"Tipos por canal: por dónde llega cada tipo de requerimiento, {mes}",
                ["Tipo de requerimiento", "Gestionadas", *[capitalizar(k) for k in nombres_canal]],
                filas,
                [2.4, 1.1, *[1.3] * len(nombres_canal)],
                lectura=it.canal_tipos(c),
                numericas=set(range(1, 2 + len(nombres_canal))),
            )
        else:
            self.p(
                "El sistema de gestión documental registra el canal de radicación desde enero de 2024; para este mes no hay canal disponible."
            )

        # --- tiempos ----------------------------------------------------------------------------------------------
        self.titulo2(
            f"{n}.10 Tiempos de gestión y de retraso",
            "Cuántos días hábiles toma responder y cuántos días después del vencimiento se atienden las extemporáneas.",
        )
        self.grafico(
            g.dias_gestion(c.serie_13, c.periodo),
            "Días hábiles promedio de gestión y de retraso por mes, últimos trece meses.",
            interp.tiempos_grafico(c),
        )
        filas = [
            [
                mayuscula_inicial(mes_y_anio(p)),
                entero(t.radicados),
                decimal(t.promedio_dias_gestion, 1),
                entero(t.extemporaneas),
                decimal(t.promedio_dias_retraso, 1),
            ]
            for p, t in c.serie_13
        ]
        self.tabla(
            "Días hábiles promedio de gestión y de retraso por mes",
            ["Mes", "Gestionadas", "Gestión (días)", "Extemporáneas", "Retraso (días)"],
            filas,
            [2.2, 1.3, 1.3, 1.3, 1.3],
            lectura=interp.tiempos_tabla(c),
            numericas={1, 2, 3, 4},
            resaltar=len(filas) - 1,
        )

    def _anexos(self) -> None:
        c = self.calculo
        mes = mes_y_anio(c.periodo)
        self.titulo1("Anexo A. Oportunidad por dependencia")
        self.p(
            f"Todas las dependencias con PQRSDF gestionadas en {mes}, de mayor a menor volumen, con su oportunidad del mes y la acumulada del año.",
            "Bajada",
        )
        acumulado_dep = dict(c.por_dependencia_acumulado)
        filas = []
        for k, t in c.por_dependencia:
            ac = acumulado_dep.get(k)
            filas.append(
                [
                    nombre_propio(k),
                    entero(t.radicados),
                    entero(t.a_tiempo),
                    entero(t.extemporaneas),
                    porcentaje(t.oportunidad),
                    entero(ac.radicados) if ac else "–",
                    porcentaje(ac.oportunidad) if ac else "–",
                ]
            )
        m = c.mes
        filas.append(
            [
                "Total",
                entero(m.radicados),
                entero(m.a_tiempo),
                entero(m.extemporaneas),
                porcentaje(m.oportunidad),
                entero(c.acumulado.radicados),
                porcentaje(c.acumulado.oportunidad),
            ]
        )
        self.tabla(
            f"Oportunidad por dependencia, {mes} y acumulado {c.anio}",
            ["Dependencia", "Gestionadas", "A tiempo", "Extemp.", "Oport. mes", "Gest. año", "Oport. año"],
            filas,
            [2.9, 1.25, 1, 0.9, 1, 1.15, 1],
            numericas={1, 2, 3, 4, 5, 6},
            resaltar=len(filas) - 1,
        )
        self.titulo1("Anexo B. Ficha técnica")
        generado = fecha_generacion(self.procedencia)
        filas = [
            ["Informe", f"{TITULO_INFORME}, {mes}"],
            ["Entidad", f"{ENTIDAD}, {AREA}"],
            [
                "Fuente",
                "Sistema de gestión documental del Ministerio: archivo mensual con las PQRSDF cuyo plazo de respuesta vence en el mes",
            ],
            ["Corte de los datos", fecha_larga(c.fecha_corte)],
            ["Datos publicados en la plataforma", fecha_larga(c.publicado_en[:10])],
            ["Versión del pipeline", c.version_pipeline or "–"],
            ["Universo del mes", f"{entero(c.mes.radicados)} PQRSDF gestionadas en {mes}"],
            ["Histórico disponible", f"Desde {mes_y_anio(c.primer_periodo)}"],
            ["Informe interactivo", URL_INFORME],
            *filas_ficha(self.procedencia, "vencimiento", "pqrsdf", c.periodo, "api/v1/vencimiento/cubo.json"),
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
    portada = Portada(
        ["Informe General", "de PQRSDF"],
        mes,
        [
            "Oportunidad de respuesta a las peticiones, quejas, reclamos,",
            "sugerencias, denuncias y felicitaciones gestionadas en el mes",
        ],
        fecha_larga(c.fecha_corte),
        [
            (entero(c.mes.radicados), "PQRSDF gestionadas en el mes"),
            (porcentaje(c.mes.oportunidad), "respondidas a tiempo"),
            (f"{decimal(c.mes.promedio_dias_gestion, 1)} días", "hábiles de gestión en promedio"),
        ],
        textos.hallazgos,
        URL_INFORME,
        nota_corte=nota_cifra(p, "vencimiento", c.periodo),
    )
    cabecera = Cabecera(TITULO_INFORME, mes, fecha_larga(c.fecha_corte))
    historia = _Constructor(c, textos, p).construir()
    return generar_pdf(
        destino, portada, cabecera, historia, f"{TITULO_INFORME} · {mes}", "Oportunidad de respuesta de las PQRSDF"
    )
