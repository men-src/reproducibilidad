"""El Informe de Trámites de un mes en PDF (D-76): portada, tabla de contenido, resumen ejecutivo con tarjetas,
objetivos, metodología, glosario, resultados (el resumen del mes por tipo, la comparación con el mes anterior, la
evolución del año, el volumen general, cada tipo frente al año anterior y un apartado por tipo de trámite con datos en
el año, con las mismas vistas del informe interactivo), observaciones, recomendaciones, conclusiones y anexos, sobre la base común de
documento.py."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from men_platform.publicaciones import graficos_canales as gc
from men_platform.publicaciones import graficos_tablero as gt
from men_platform.publicaciones import graficos_tramites as gtr
from men_platform.publicaciones import interpretaciones_tramites as interp
from men_platform.publicaciones.datos_tramites import Calculo, Serie, cuantos_para
from men_platform.publicaciones.documento import (
    AREA,
    ENTIDAD,
    Cabecera,
    Constructor,
    Portada,
    generar_pdf,
    registrar_fuentes,
)
from men_platform.publicaciones.graficos_pqrsdf import AZUL
from men_platform.publicaciones.procedencia import Procedencia, fecha_generacion, filas_ficha, nota_cifra
from men_platform.publicaciones.redaccion_pqrsdf import Textos
from men_platform.publicaciones.redaccion_tramites import redactar
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
    numero_en_palabras,
    porcentaje,
    tramo_del_anio,
    variacion,
)

TITULO_INFORME = "Informe de Trámites"
URL_INFORME = "https://men-src.github.io/tramites/"
GUION = "–"


def _mismos(s: Serie) -> str:
    """«al mismo mes» cuando el año lleva un solo mes con datos; si no, «a los mismos meses»."""
    return "al mismo mes" if s.meses_acumulado == 1 else "a los mismos meses"


def _etiquetas(serie: list[tuple[str, object]]) -> list[str]:
    return [mes_corto_2(p) if len(serie) > 9 else mes_corto(p) for p, _ in serie]


def _pct(v: float | None, decimales: int = 1) -> str:
    return porcentaje(v, decimales) if v is not None else GUION


def _dif(a: int | float | None, b: int | float | None) -> str:
    if a is None or b is None:
        return GUION
    d = a - b
    return f"{'+' if d > 0 else '−' if d < 0 else ''}{entero(abs(d))}"


class _Constructor(Constructor):
    """Las secciones del Informe de Trámites sobre la base común."""

    def __init__(self, calculo: Calculo, textos: Textos, procedencia: Procedencia | None = None) -> None:
        self.procedencia = procedencia or Procedencia()
        super().__init__()
        self.calculo = calculo
        self.textos = textos
        # la tabla de contenido cabe en una página aunque haya diez apartados por tipo
        self.estilos["Toc0"].leading = 14
        self.estilos["Toc0"].spaceBefore = 2
        self.estilos["Toc1"].leading = 12.5

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
            "Las observaciones salen de las cifras del mes y de su comparación con el promedio mensual, con el mes anterior y con el "
            "año anterior, en total y por tipo de trámite; cada una señala un hecho verificable en las tablas de este informe.",
            "Bajada",
        )
        self.lista(t.observaciones)
        self.titulo1("7. Recomendaciones")
        self.p(
            "Las recomendaciones responden a las observaciones anteriores y se dirigen a la entidad: a la Subdirección de Relacionamiento "
            "con la Ciudadanía y a las áreas que gestionan cada tipo de trámite.",
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
        """Ocho tarjetas en dos filas: el valor del mes y, debajo, el mes anterior, el mismo mes del año anterior y el año."""
        c = self.calculo
        t = c.total
        anio = c.anio
        mes = nombre_mes(c.periodo)

        def lineas_de(s: Serie) -> list[str]:
            out = []
            if s.mes_anterior is not None and s.mes is not None:
                out.append(
                    f"{mayuscula_inicial(mes_corto(s.periodo_anterior))}: {entero(s.mes_anterior)} ({variacion(s.mes, s.mes_anterior)})"
                )
            if s.mismo_mes_anterior is not None and s.mes is not None:
                out.append(
                    f"{mayuscula_inicial(mes_corto(c.periodo)[:3])} {anio - 1}: {entero(s.mismo_mes_anterior)} "
                    f"({variacion(s.mes, s.mismo_mes_anterior)})"
                )
            out.append(f"Año {anio}: {entero(s.acumulado) if s.acumulado else GUION}")
            return out

        tipos = c.tipos_del_mes
        principal = tipos[0]
        mayor, menor = t.mes_mayor, t.mes_menor
        promedio = t.promedio_mensual
        lineas_promedio = []
        if t.promedio_anterior:
            lineas_promedio.append(
                f"Mismo tramo de {anio - 1}: {decimal(t.promedio_anterior, 1)} ({variacion(promedio, t.promedio_anterior)})"
            )
        if promedio and t.mes is not None:
            if t.meses_acumulado >= 2:
                lineas_promedio.append(f"{mayuscula_inicial(mes)}: {variacion(t.mes, promedio)} frente al promedio")
        lineas_promedio.append(
            "Sobre un mes con datos"
            if t.meses_acumulado == 1
            else f"Sobre {numero_en_palabras(t.meses_acumulado, femenino=False)} meses con datos"
        )
        lineas_mayor = []
        if mayor:
            lineas_mayor.append(
                mayuscula_inicial(nombre_mes(mayor[0])) + (" (este mes)" if mayor[0] == c.periodo else "")
            )
        if menor and mayor and menor[0] != mayor[0]:
            lineas_mayor.append(f"Más bajo: {entero(menor[1])} en {nombre_mes(menor[0])}")
        lineas_acumulado = []
        if t.acumulado_anterior:
            lineas_acumulado.append(
                f"Mismo tramo de {anio - 1}: {entero(t.acumulado_anterior)} ({variacion(t.acumulado, t.acumulado_anterior)})"
            )
        lineas_acumulado.append(
            f"{tramo_del_anio(c.periodo, mayuscula=True)}, {t.meses_acumulado} {'mes' if t.meses_acumulado == 1 else 'meses'} con datos"
        )
        sin_mes = [s for s in c.tipos if s.mes is None]
        lineas_tipos = [f"De {len(c.tipos)} tipos con datos en {anio}"]
        lineas_tipos.append(
            f"Sin datos en el mes: {lista_en_prosa([s.tramite.corto.lower() for s in sin_mes if s.tramite])}"
            if sin_mes
            else f"{cuantos_para([s.mes or 0 for s in tipos])} explican el 80 % del mes"
        )
        grandes = c.tipos_del_anio[:2]
        tarjetas = [
            self.tarjeta("Trámites gestionados en el mes", entero(t.mes), lineas_de(t)),
            self.tarjeta(f"Promedio mensual de {anio}", decimal(promedio, 1) if promedio else GUION, lineas_promedio),
            self.tarjeta(f"Mes más alto de {anio}", entero(mayor[1]) if mayor else GUION, lineas_mayor),
            self.tarjeta(
                "Trámite principal del mes",
                _pct(c.participacion(principal)),
                [f"{principal.nombre}: {entero(principal.mes)}", f"De {entero(t.mes)} trámites en {mes}"],
            ),
            *[
                self.tarjeta(f"{s.nombre} en el mes", entero(s.mes) if s.mes is not None else GUION, lineas_de(s))
                for s in grandes
            ],
            self.tarjeta(f"Acumulado de {anio}", entero(t.acumulado), lineas_acumulado),
            self.tarjeta("Tipos de trámite con datos en el mes", str(len(tipos)), lineas_tipos),
        ]
        self.tarjetas("Tarjetas de resultados del mes y sus comparaciones", tarjetas)
        self.p(
            "Cada tarjeta trae el valor del mes y, debajo, el mes anterior con datos, el mismo mes del año anterior y el acumulado del "
            "año; el promedio mensual es el total del año sobre sus meses con datos.",
            "Nota",
        )

    # --- resultados ---------------------------------------------------------------------------------------------
    def _resultados(self) -> None:  # noqa: PLR0915 - los apartados del informe interactivo, en su orden
        c = self.calculo
        t = c.total
        mes = mes_y_anio(c.periodo)
        anio = c.anio
        n = 5
        self.titulo1(f"{n}. Resultados")
        self.p(
            f"Esta sección recorre los trámites gestionados en {mes}: primero el resumen del mes por tipo, después la comparación con el "
            f"mes anterior, la evolución de {anio} frente al promedio mensual, el volumen general frente al año anterior, al mes anterior y "
            "a su media móvil, cada tipo frente al año anterior y, por último, un apartado por tipo de trámite. Cada gráfico y cada "
            "tabla van seguidos de su lectura."
        )

        # --- 5.1 resumen del mes -----------------------------------------------------------------------------
        self.titulo2(
            f"{n}.1 Resumen del mes",
            f"Cuántos trámites de cada tipo se gestionaron en {mes}, cuánto pesa cada uno y cuántos tipos explican la mayor parte del volumen.",
        )
        tipos = c.tipos_del_mes
        filas = []
        acumulado = 0.0
        for s in tipos:
            parte = c.participacion(s) or 0
            acumulado += parte
            promedio = s.promedio_mensual
            filas.append(
                [
                    s.nombre,
                    entero(s.mes),
                    _pct(parte),
                    _pct(acumulado),
                    decimal(promedio, 1) if promedio else GUION,
                    variacion(s.mes, promedio) if promedio else GUION,
                ]
            )
        filas.append(
            [
                "Total general",
                entero(t.mes),
                _pct(1.0),
                "",
                decimal(t.promedio_mensual, 1),
                variacion(t.mes, t.promedio_mensual),
            ]
        )
        self.tabla(
            f"Resumen por tipo de trámite en {mes}: trámites, participación, acumulado de mayor a menor y promedio mensual de {anio}",
            ["Tipo de trámite", "Trámites", "Participación", "Acumulado", f"Promedio {anio}", "Vs. promedio"],
            filas,
            [1.95, 0.8, 1.1, 0.95, 1.2, 1.1],
            lectura=interp.tabla_tipos(c),
            numericas={1, 2, 3, 4, 5},
            resaltar=len(filas) - 1,
        )
        self.grafico(
            gc.barras_por_canal(
                [s.nombre for s in tipos],
                [s.mes or 0 for s in tipos],
                [gtr.color_de(s.tramite, i) for i, s in enumerate(tipos)],
            ),
            f"Trámites gestionados por tipo en {mes}, de mayor a menor.",
            interp.barras_tipos(c),
        )
        self.grafico(
            gtr.treemap([(s.nombre, s.mes or 0, gtr.color_de(s.tramite, i)) for i, s in enumerate(tipos)]),
            f"Participación de cada tipo de trámite en {mes}: el área es proporcional a su volumen.",
            interp.treemap(c),
        )
        if len(tipos) >= 2:
            self.grafico(
                gtr.pareto_tipos([(s.tramite.corto if s.tramite else s.nombre, s.mes or 0) for s in tipos]),
                f"Pareto de los tipos de trámite en {mes}: volumen de mayor a menor y participación acumulada, con la guía del 80 %.",
                interp.pareto(c),
            )

        # --- 5.2 comparación con el mes anterior -------------------------------------------------------------
        if t.mes_anterior is None:
            self.titulo2(
                f"{n}.2 Comparación con el mes inmediatamente anterior",
                f"{mayuscula_inicial(mes)} es el primer mes del histórico de la plataforma: no hay un mes anterior con datos para comparar.",
            )
            self.p(f"La comparación con el mes anterior empieza en el informe de {mes_y_anio_siguiente(c.periodo)}.")
        else:
            mes_ant = nombre_mes(t.periodo_anterior)
            mes_act = nombre_mes(c.periodo)
            self.titulo2(
                f"{n}.2 Comparación con {mes_ant}, el mes inmediatamente anterior",
                f"Qué cambió entre {mes_ant} y {mes_act} de {anio} en el total general y en cada tipo de trámite.",
            )
            col_ant = mayuscula_inicial(mes_corto(t.periodo_anterior))
            col_act = mayuscula_inicial(mes_corto(c.periodo))
            filas = []
            for s in c.tipos:
                if s.mes is None and s.mes_anterior is None:
                    continue
                if s.mes is None and s.periodo_anterior != t.periodo_anterior:
                    continue
                etiqueta = s.nombre
                if s.mes is not None and s.mes_anterior is not None and s.periodo_anterior != t.periodo_anterior:
                    etiqueta += f" (frente a {mes_y_anio(s.periodo_anterior)})"
                filas.append(
                    [
                        etiqueta,
                        entero(s.mes_anterior) if s.mes_anterior is not None else GUION,
                        entero(s.mes) if s.mes is not None else GUION,
                        _dif(s.mes, s.mes_anterior),
                        variacion(s.mes, s.mes_anterior),
                    ]
                )
            filas.sort(key=lambda f: -(int(f[2].replace(".", "")) if f[2] != GUION else -1))
            filas.append(
                [
                    "Total general",
                    entero(t.mes_anterior),
                    entero(t.mes),
                    _dif(t.mes, t.mes_anterior),
                    variacion(t.mes, t.mes_anterior),
                ]
            )
            self.tabla(
                f"Trámites gestionados por tipo: {mes_ant} y {mes_act} de {anio}, con la diferencia y la variación",
                ["Tipo de trámite", col_ant, col_act, "Diferencia", "Variación"],
                filas,
                [2.5, 1.0, 1.0, 1.0, 1.0],
                lectura=interp.comparacion_mes_anterior(c),
                numericas={1, 2, 3, 4},
                resaltar=len(filas) - 1,
            )

        # --- 5.3 evolución del año ---------------------------------------------------------------------------
        self.titulo2(
            f"{n}.3 Evolución de {anio}",
            f"El total general de cada mes de {anio} frente al promedio mensual, los trámites por tipo mes a mes y cómo se reparten los tipos.",
        )
        if len(t.serie_anio) >= 2:
            etiquetas_anio = _etiquetas(t.serie_anio)
            resaltar = next((i for i, (p, _) in enumerate(t.serie_anio) if p == c.periodo), None)
            promedio = t.promedio_mensual or 0
            self.grafico(
                gtr.barras_con_referencia(
                    etiquetas_anio, [v for _, v in t.serie_anio], AZUL, ("Promedio mensual", promedio), resaltar
                ),
                f"Total general de trámites por mes en {anio}, con el promedio mensual de los meses con datos.",
                interp.total_por_mes(c),
            )
            filas = [
                [
                    mayuscula_inicial(nombre_mes(p)),
                    entero(v),
                    decimal(promedio, 1),
                    _dif(v, promedio),
                    variacion(v, promedio),
                ]
                for p, v in t.serie_anio
            ]
            filas.append([tramo_del_anio(c.periodo, mayuscula=True), entero(t.acumulado), "", "", ""])
            self.tabla(
                f"Total general por mes en {anio} frente al promedio mensual: diferencia en trámites y en porcentaje",
                ["Mes", "Total general", "Promedio", "Diferencia", "Variación"],
                filas,
                [1.6, 1.2, 1.1, 1.1, 1.1],
                numericas={1, 2, 3, 4},
                resaltar=len(filas) - 1,
            )
            partes = []
            for i, s in enumerate(c.tipos_del_anio):
                valores = [next((v for tr, v in lista if tr.id == s.tramite.id), 0) for _, lista in c.tipo_por_mes]
                if any(valores):
                    partes.append((s.nombre, gtr.color_de(s.tramite, i), valores))
            self.grafico(
                gc.barras_con_linea(etiquetas_anio, partes, None, apiladas=True, resaltar=resaltar),
                f"Trámites por tipo mes a mes en {anio}, apilados; el tipo de mayor volumen del año va abajo.",
                interp.apiladas_por_tipo(c),
            )
            self.grafico(
                gc.mezcla(etiquetas_anio, partes),
                f"Cómo se reparten los tipos de trámite mes a mes en {anio}, al 100 %.",
                interp.mezcla(c),
            )
        else:
            self.p(
                f"{mayuscula_inicial(nombre_mes(c.periodo))} es el primer mes de {anio} con datos: las vistas mes a mes del año (total "
                "frente al promedio, trámites por tipo apilados y mezcla de tipos) empiezan en el informe siguiente."
            )

        # --- 5.4 volumen general -----------------------------------------------------------------------------
        self.titulo2(
            f"{n}.4 Volumen general",
            f"El total general de trámites por mes frente al mismo mes de {anio - 1}, frente al mes anterior y frente a su media móvil "
            "simple de tres meses.",
        )
        self._vistas_volumen(t, "trámites")

        # --- 5.5 cada tipo frente al año anterior ------------------------------------------------------------
        tipos_anio = c.tipos_del_anio
        con_par = any(s.acumulado_anterior for s in tipos_anio)
        if con_par:
            self.titulo2(
                f"{n}.5 Cada tipo de trámite frente a {anio - 1}",
                f"El acumulado de {tramo_del_anio(c.periodo)} de {anio} de cada tipo frente {_mismos(t)} de {anio - 1}.",
            )
        else:
            self.titulo2(
                f"{n}.5 Trámites por tipo en {anio}",
                f"El acumulado de {tramo_del_anio(c.periodo)} de {anio} de cada tipo; no hay datos de {anio - 1} con los cuales compararlo.",
            )
        if tipos_anio and not con_par and t.meses_acumulado < 2:
            self.p(
                f"{mayuscula_inicial(nombre_mes(c.periodo))} es el único mes de {anio} con datos y no hay datos de {anio - 1}: el "
                "acumulado por tipo es el del mes, que ya muestra el resumen del mes, y la comparación con el año anterior "
                "empieza cuando haya con qué hacerla."
            )
        elif tipos_anio:
            self.grafico(
                gtr.tipos_dos_anios(
                    [s.nombre for s in tipos_anio],
                    [s.acumulado for s in tipos_anio],
                    [s.acumulado_anterior for s in tipos_anio],
                    anio,
                    anio - 1 if con_par else None,
                ),
                f"Trámites por tipo, {tramo_del_anio(c.periodo)} de {anio}"
                + (f" frente {_mismos(t)} de {anio - 1}." if con_par else "."),
                interp.tipos_dos_anios(c),
            )
            if con_par:
                filas = [
                    [
                        s.nombre,
                        entero(s.acumulado),
                        entero(s.acumulado_anterior) if s.acumulado_anterior is not None else GUION,
                        _dif(s.acumulado, s.acumulado_anterior),
                        variacion(s.acumulado, s.acumulado_anterior),
                    ]
                    for s in tipos_anio
                ]
                filas.append(
                    [
                        "Total general",
                        entero(t.acumulado),
                        entero(t.acumulado_anterior),
                        _dif(t.acumulado, t.acumulado_anterior),
                        variacion(t.acumulado, t.acumulado_anterior),
                    ]
                )
                self.tabla(
                    f"Trámites por tipo, {tramo_del_anio(c.periodo)} de {anio} y de {anio - 1}: diferencia y variación",
                    ["Tipo de trámite", str(anio), str(anio - 1), "Diferencia", "Variación"],
                    filas,
                    [2.5, 1.0, 1.0, 1.0, 1.0],
                    numericas={1, 2, 3, 4},
                    resaltar=len(filas) - 1,
                )
        else:
            self.p(f"No hay tipos con datos en {anio}.")

        # --- 5.6 en adelante: un apartado por tipo de trámite ------------------------------------------------
        con_serie = [s for s in c.tipos if len(s.serie_anio if len(s.serie_anio) >= 2 else s.serie_13) >= 2]
        sin_serie = [s for s in c.tipos if s not in con_serie]
        for k_tipo, s in enumerate(con_serie, start=6):
            self._apartado_tipo(n, k_tipo, s)
        if sin_serie:
            self.titulo2(
                f"{n}.{6 + len(con_serie)} Apartados por tipo de trámite",
                f"Los tipos que todavía no tienen dos meses con datos en la plataforma: {lista_en_prosa([s.nombre.lower() if s.tramite and s.tramite.fuente != 'pqrs' else s.nombre for s in sin_serie])}.",
            )
            self.p(
                f"{mayuscula_inicial(mes)} es el primer mes con datos de {numero_en_palabras(len(sin_serie), femenino=False) if len(sin_serie) > 1 else 'este tipo'} "
                f"{'tipos' if len(sin_serie) > 1 else ''} en la plataforma: los apartados por tipo, con sus vistas mes a mes frente al promedio y al año "
                "anterior, empiezan en el informe siguiente. Lo gestionado en el mes por cada uno está en el resumen del mes."
            )

    def _vistas_volumen(self, s: Serie, que: str) -> None:
        """Las vistas de volumen del informe interactivo: dos años, variación frente al mes anterior y media móvil."""
        c = self.calculo
        anio = c.anio
        es_anio = len(s.serie_anio) >= 2
        dibujados = 0
        if es_anio or (s.serie_anio and s.serie_anio_anterior):
            actual = {int(p[5:7]): v for p, v in s.serie_anio}
            anterior = {int(p[5:7]): v for p, v in s.serie_anio_anterior}
            self.grafico(
                gt.dos_anios(actual, anterior, anio, "entero", hasta=c.mes_numero),
                f"{s.nombre}: {que} por mes, {anio}" + (f" frente a {anio - 1}." if anterior else "."),
                interp.dos_anios(s, c),
            )
            dibujados += 1
            if anterior:
                filas = [
                    [
                        mayuscula_inicial(nombre_mes(p)),
                        entero(v),
                        entero(anterior.get(int(p[5:7]))) if int(p[5:7]) in anterior else GUION,
                        _dif(v, anterior.get(int(p[5:7]))),
                        variacion(v, anterior.get(int(p[5:7]))),
                    ]
                    for p, v in s.serie_anio
                ]
                filas.append(
                    [
                        tramo_del_anio(c.periodo, mayuscula=True),
                        entero(s.acumulado),
                        entero(s.acumulado_anterior) if s.acumulado_anterior is not None else GUION,
                        _dif(s.acumulado, s.acumulado_anterior),
                        variacion(s.acumulado, s.acumulado_anterior),
                    ]
                )
                self.tabla(
                    f"{s.nombre} por mes, {anio} frente a {anio - 1}: diferencia en {que} y en porcentaje",
                    ["Mes", str(anio), str(anio - 1), "Diferencia", "Variación"],
                    filas,
                    [1.6, 1.2, 1.1, 1.1, 1.1],
                    numericas={1, 2, 3, 4},
                    resaltar=len(filas) - 1,
                )
        if len(s.serie_13) >= 2:
            serie13 = s.serie_13
            valores = [None] + [
                ((serie13[i][1] / serie13[i - 1][1] - 1) * 100) if serie13[i - 1][1] else None
                for i in range(1, len(serie13))
            ]
            self.grafico(
                gt.barras_variacion(_etiquetas(serie13), valores, "%"),
                f"{s.nombre}: variación de {que} frente al mes anterior, últimos {len(serie13)} meses con datos.",
                interp.variacion_mensual(s),
            )
            dibujados += 1
        if any(s.media_movil.get(p) is not None for p, _ in s.serie_13):
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, float(v)) for p, v in s.serie_13],
                    [(p, s.media_movil.get(p)) for p, _ in s.serie_13],
                    c.periodo,
                    "entero",
                    mayuscula_inicial(que),
                ),
                f"{s.nombre}: {que} frente a su media móvil simple de tres meses, últimos {len(s.serie_13)} meses con datos.",
                interp.media_movil(s),
            )
            dibujados += 1
        if not dibujados:
            self.p(
                f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico de la plataforma: las vistas de volumen "
                f"(frente a {anio - 1}, frente al mes anterior y frente a la media móvil) empiezan en los informes siguientes."
            )

    def _apartado_tipo(self, n: int, k_tipo: int, s: Serie) -> None:
        """Un tipo con datos en el año: sus trámites mes a mes frente al promedio y frente al año anterior."""
        c = self.calculo
        anio = c.anio
        tramite = s.tramite
        nombre = s.nombre if tramite and tramite.fuente == "pqrs" else s.nombre.lower()
        bajada = f"Los trámites de {nombre} mes a mes, frente a su promedio mensual y al año anterior."
        if s.primer_periodo and s.primer_periodo > c.primer_periodo:
            bajada += f" El tipo tiene datos desde {mes_y_anio(s.primer_periodo)}."
        if s.ultimo_periodo and s.ultimo_periodo < c.periodo:
            bajada += f" Su último mes con datos es {mes_y_anio(s.ultimo_periodo)}."
        elif len(s.serie_anio) < len(c.total.serie_anio):
            bajada += f" En {anio} tiene datos en {lista_en_prosa([nombre_mes(p) for p, _ in s.serie_anio])}."
        self.titulo2(f"{n}.{k_tipo} {s.nombre}", bajada)
        es_anio = len(s.serie_anio) >= 2
        serie = s.serie_anio if es_anio else s.serie_13
        if len(serie) < 2:
            self.p(
                f"{mayuscula_inicial(mes_y_anio(serie[0][0]))} es el primer mes con datos de {nombre} en la plataforma: las vistas "
                f"mes a mes empiezan en el informe siguiente. El mes trae {entero(serie[0][1])} trámites."
            )
            return
        etiquetas = _etiquetas(serie)
        resaltar = next((i for i, (p, _) in enumerate(serie) if p == c.periodo), None)
        tramo = f"en {anio}" if es_anio else f"en los últimos {len(serie)} meses con datos"
        promedio = s.promedio_mensual if es_anio else sum(v for _, v in serie) / len(serie)
        self.grafico(
            gtr.barras_con_referencia(
                etiquetas,
                [v for _, v in serie],
                gtr.color_de(tramite) if tramite else AZUL,
                ("Promedio mensual", promedio or 0),
                resaltar,
            ),
            f"{s.nombre}: trámites por mes {tramo}, con el promedio mensual.",
            interp.tipo_mes_a_mes(s, c),
        )
        if es_anio or (s.serie_anio and s.serie_anio_anterior):
            actual = {int(p[5:7]): v for p, v in s.serie_anio}
            anterior = {int(p[5:7]): v for p, v in s.serie_anio_anterior}
            if anterior:
                self.grafico(
                    gt.dos_anios(actual, anterior, anio, "entero", hasta=c.mes_numero),
                    f"{s.nombre}: trámites por mes, {anio} frente a {anio - 1}.",
                    interp.dos_anios(s, c),
                )

    # --- anexos ---------------------------------------------------------------------------------------------------
    def _anexos(self) -> None:
        c = self.calculo
        t = c.total
        anio = c.anio
        mes = mes_y_anio(c.periodo)
        self.titulo1("Anexo A. Trámites por tipo y mes")
        self.p(interp.anexo(c), "Bajada")
        tipos = c.tipos_del_anio
        meses = [p for p, _ in t.serie_anio]
        totales = dict(t.serie_anio)
        # hasta seis tipos por tabla, para que cada nombre quepa en un renglón; la última trae el total general
        grupos = [tipos[i : i + 6] for i in range(0, len(tipos), 6)] or [[]]
        for k, grupo in enumerate(grupos, start=1):
            ultimo = k == len(grupos)
            encabezados = [
                "Mes",
                *[s.tramite.corto if s.tramite else s.nombre for s in grupo],
                *(["Total"] if ultimo else []),
            ]
            valores = {s.nombre: dict(s.serie_anio) for s in grupo}
            filas = [
                [
                    mayuscula_inicial(nombre_mes(p)),
                    *[entero(valores[s.nombre][p]) if p in valores[s.nombre] else GUION for s in grupo],
                    *([entero(totales[p])] if ultimo else []),
                ]
                for p in meses
            ]
            filas.append(["Total", *[entero(s.acumulado) for s in grupo], *([entero(t.acumulado)] if ultimo else [])])
            # el ancho de cada columna sigue al largo de su encabezado, con un mínimo para las cifras
            anchos = [1.0, *[max(0.8, 0.1 * len(h)) for h in encabezados[1:]]]
            parte = f" ({k} de {len(grupos)})" if len(grupos) > 1 else ""
            self.tabla(
                f"Trámites gestionados por mes y tipo, {anio}{parte}",
                encabezados,
                filas,
                anchos,
                numericas=set(range(1, len(encabezados))),
                resaltar=len(filas) - 1,
                compacta=True,
            )
        self.titulo1("Anexo B. Ficha técnica")
        generado = fecha_generacion(self.procedencia)
        filas = [
            ["Informe", f"{TITULO_INFORME}, {mes}"],
            ["Entidad", f"{ENTIDAD}, {AREA}"],
            [
                "Fuente",
                "Consolidado mensual de trámites de la Subdirección de Relacionamiento con la Ciudadanía (un total por mes y tipo de "
                "trámite) y los meses nuevos cargados por archivo con la misma forma",
            ],
            ["Corte de los datos", fecha_larga(c.fecha_corte)],
            ["Datos publicados en la plataforma", fecha_larga(c.publicado_en[:10])],
            ["Versión del pipeline", c.version_pipeline or GUION],
            [
                "Universo del mes",
                f"{entero(t.mes)} trámites gestionados de {numero_en_palabras(len(c.tipos_del_mes), femenino=False)} tipos en {mes}",
            ],
            ["Histórico disponible", f"Desde {mes_y_anio(c.primer_periodo)}"],
            ["Informe interactivo", URL_INFORME],
            *filas_ficha(self.procedencia, "tramites", "tramites", c.periodo, "api/v1/tramites/cubo.json"),
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
    t = c.total
    principal = c.tipos_del_mes[0]
    portada = Portada(
        ["Informe", "de Trámites"],
        mes,
        [
            "Los trámites que gestionó el Ministerio en el mes, por tipo, comparados con el",
            "promedio mensual, con el mes anterior y con el mismo mes del año anterior",
        ],
        fecha_larga(c.fecha_corte),
        [
            (entero(t.mes), "trámites gestionados en el mes"),
            (decimal(t.promedio_mensual, 1) if t.promedio_mensual else GUION, f"promedio mensual de {c.anio}"),
            (
                _pct(c.participacion(principal)),
                f"{principal.tramite.corto.lower() if principal.tramite else principal.nombre.lower()} (trámite principal)",
            ),
        ],
        textos.hallazgos,
        URL_INFORME,
        nota_corte=nota_cifra(p, "tramites", c.periodo),
    )
    cabecera = Cabecera(TITULO_INFORME, mes, fecha_larga(c.fecha_corte))
    historia = _Constructor(c, textos, p).construir()
    return generar_pdf(
        destino,
        portada,
        cabecera,
        historia,
        f"{TITULO_INFORME} · {mes}",
        "Trámites gestionados por tipo y mes",
    )
