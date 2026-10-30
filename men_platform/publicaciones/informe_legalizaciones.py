"""El Informe de Legalizaciones de un mes en PDF (D-79): portada, tabla de contenido, resumen ejecutivo con tarjetas,
objetivos, metodología, glosario, resultados (el resumen del mes por metodología, la comparación con el mes anterior,
la evolución del año, el volumen general, el porcentaje de oportunidad, el resultado y la tasa de legalización, los
tiempos de respuesta y las categorías: metodologías y tipos de documento, con las mismas vistas del informe
interactivo), observaciones, recomendaciones, conclusiones y anexos, sobre la base común de documento.py."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from men_platform.publicaciones import graficos_canales as gc
from men_platform.publicaciones import graficos_legalizaciones as gl
from men_platform.publicaciones import graficos_tablero as gt
from men_platform.publicaciones import graficos_tramites as gtr
from men_platform.publicaciones import interpretaciones_legalizaciones as interp
from men_platform.publicaciones.datos_legalizaciones import NOMBRES_RANGOS, Calculo, Categoria, Medidas
from men_platform.publicaciones.documento import (
    AREA,
    ENTIDAD,
    Cabecera,
    Constructor,
    Portada,
    generar_pdf,
    registrar_fuentes,
)
from men_platform.publicaciones.graficos_pqrsdf import AMARILLO, AZUL, ROJO
from men_platform.publicaciones.procedencia import Procedencia, fecha_generacion, filas_ficha, nota_cifra
from men_platform.publicaciones.redaccion_legalizaciones import plazo_en_texto, redactar
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
    numero_en_palabras,
    porcentaje,
    puntos,
    tramo_del_anio,
    variacion,
)

TITULO_INFORME = "Informe de Legalizaciones"
URL_INFORME = "https://men-src.github.io/legalizaciones/"
GUION = "–"
MAXIMO_BARRAS = 15  # tipos de documento que caben en las barras horizontales sin apretarse
MAXIMO_TREEMAP = 12
# Nombres cortos de las metodologías para los ejes y las tablas anchas.
CORTOS: dict[str, str] = {
    "pregrado": "Pregrado",
    "maestria": "Maestría",
    "especializacion": "Especializ.",
    "tecnologo": "Tecnólogo",
    "tecnico profesional": "Técnico prof.",
    "certificacion": "Certificación",
    "doctorado": "Doctorado",
    "documento men": "Doc. MEN",
    "resolucion": "Resolución",
    "distincion": "Distinción",
    "normalista": "Normalista",
}

Grupos = list[tuple[Categoria, Medidas]]


def _corto(k: Categoria) -> str:
    return CORTOS.get(k.fuente, k.nombre) if k.clase == "metodologia" else k.nombre


def _etiquetas(serie: list[tuple[str, object]]) -> list[str]:
    return [mes_corto_2(p) if len(serie) > 9 else mes_corto(p) for p, _ in serie]


def _pct(v: float | None, decimales: int = 2) -> str:
    return porcentaje(v, decimales) if v is not None else GUION


def _dec(v: float | None) -> str:
    return decimal(v, 1) if v is not None else GUION


def _dif(a: int | float | None, b: int | float | None) -> str:
    if a is None or b is None:
        return GUION
    d = a - b
    return f"{'+' if d > 0 else '−' if d < 0 else ''}{entero(abs(d))}"


def _pp(a: float | None, b: float | None) -> str:
    return puntos(a - b) if a is not None and b is not None else GUION


def _dif_dias(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return GUION
    d = round(a, 1) - round(b, 1)
    return f"{'+' if d > 0 else '−' if d < 0 else ''}{decimal(abs(d), 1)}"


class _Constructor(Constructor):
    """Las secciones del Informe de Legalizaciones sobre la base común."""

    def __init__(self, calculo: Calculo, textos: Textos, procedencia: Procedencia | None = None) -> None:
        self.procedencia = procedencia or Procedencia()
        super().__init__()
        self.calculo = calculo
        self.textos = textos
        # la tabla de contenido cabe en una página aunque la sección de resultados tenga nueve apartados
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
            "año anterior, en el volumen, el resultado, la oportunidad y los tiempos; cada una señala un hecho verificable en las tablas "
            "de este informe.",
            "Bajada",
        )
        self.lista(t.observaciones)
        self.titulo1("7. Recomendaciones")
        self.p(
            "Las recomendaciones responden a las observaciones anteriores y se dirigen a la entidad: a la Subdirección de Relacionamiento "
            "con la Ciudadanía y al equipo que gestiona la legalización de documentos.",
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
        m, ant, mismo = c.mes, c.mes_anterior, c.mismo_mes_anterior
        anio = c.anio
        mes = nombre_mes(c.periodo)
        ant_corto = mayuscula_inicial(mes_corto(c.periodo_anterior)) if c.periodo_anterior else ""
        mismo_corto = f"{mayuscula_inicial(mes_corto(c.periodo)[:3])} {anio - 1}"

        def lineas_volumen(campo: str, acumulado: bool = True) -> list[str]:
            v = getattr(m, campo)
            out = []
            if ant is not None:
                out.append(f"{ant_corto}: {entero(getattr(ant, campo))} ({variacion(v, getattr(ant, campo))})")
            if mismo is not None:
                out.append(f"{mismo_corto}: {entero(getattr(mismo, campo))} ({variacion(v, getattr(mismo, campo))})")
            if acumulado:
                out.append(f"Año {anio}: {entero(getattr(c.acumulado, campo))}")
            return out

        def lineas_indice(campo: str) -> list[str]:
            v = getattr(m, campo)
            out = []
            if ant is not None and getattr(ant, campo) is not None:
                out.append(f"{ant_corto}: {porcentaje(getattr(ant, campo))} ({_pp(v, getattr(ant, campo))})")
            if mismo is not None and getattr(mismo, campo) is not None:
                out.append(f"{mismo_corto}: {porcentaje(getattr(mismo, campo))} ({_pp(v, getattr(mismo, campo))})")
            out.append(f"Año {anio}: {_pct(getattr(c.acumulado, campo))}")
            return out

        lineas_dias = []
        if ant is not None and ant.promedio_dias_habiles_legalizadas is not None:
            lineas_dias.append(
                f"{ant_corto}: {_dec(ant.promedio_dias_habiles_legalizadas)} ({_dif_dias(m.promedio_dias_habiles_legalizadas, ant.promedio_dias_habiles_legalizadas)})"
            )
        if mismo is not None and mismo.promedio_dias_habiles_legalizadas is not None:
            lineas_dias.append(
                f"{mismo_corto}: {_dec(mismo.promedio_dias_habiles_legalizadas)} ({_dif_dias(m.promedio_dias_habiles_legalizadas, mismo.promedio_dias_habiles_legalizadas)})"
            )
        lineas_dias.append(f"{_dec(m.promedio_dias_legalizadas)} días calendario")
        lineas_curso = [
            f"{_pct(m.participacion_en_curso, 1)} de las radicadas del mes",
            f"Canceladas: {entero(m.canceladas)}",
        ]
        if ant is not None:
            lineas_curso.append(f"{ant_corto}: {entero(ant.en_curso)} en curso")
        principal = c.metodologias_mes[0] if c.metodologias_mes else None
        lineas_principal = (
            [f"{principal[0].nombre}: {entero(principal[1].radicadas)}", f"De {entero(m.radicadas)} radicadas en {mes}"]
            if principal
            else [GUION]
        )
        lineas_acumulado = []
        if c.acumulado_anterior is not None:
            lineas_acumulado.append(
                f"Mismo tramo de {anio - 1}: {entero(c.acumulado_anterior.radicadas)} ({variacion(c.acumulado.radicadas, c.acumulado_anterior.radicadas)})"
            )
        lineas_acumulado.append(
            f"{tramo_del_anio(c.periodo, mayuscula=True)}, {c.meses_acumulado} {'mes' if c.meses_acumulado == 1 else 'meses'} con datos"
        )
        if c.promedio_mensual and c.meses_acumulado >= 2:
            lineas_acumulado.append(f"Promedio mensual: {decimal(c.promedio_mensual, 1)}")
        tarjetas = [
            self.tarjeta("Radicadas en el mes", entero(m.radicadas), lineas_volumen("radicadas")),
            self.tarjeta("Legalizadas", entero(m.legalizadas), lineas_volumen("legalizadas")),
            self.tarjeta("Tasa de legalización", _pct(m.tasa_legalizacion), lineas_indice("tasa_legalizacion")),
            self.tarjeta("% de oportunidad", _pct(m.oportunidad), lineas_indice("oportunidad")),
            self.tarjeta("Días hábiles de gestión", _dec(m.promedio_dias_habiles_legalizadas), lineas_dias),
            self.tarjeta("En curso al corte", entero(m.en_curso), lineas_curso),
            self.tarjeta(
                "Metodología principal",
                _pct(c.participacion(principal[1]), 1) if principal else GUION,
                lineas_principal,
            ),
            self.tarjeta(f"Acumulado de {anio}", entero(c.acumulado.radicadas), lineas_acumulado),
        ]
        self.tarjetas("Tarjetas de resultados del mes y sus comparaciones", tarjetas)
        self.p(
            "Cada tarjeta trae el valor del mes y, debajo, el mes anterior, el mismo mes del año anterior y el acumulado del año; los "
            "volúmenes se comparan en porcentaje y los índices en puntos porcentuales.",
            "Nota",
        )

    # --- resultados ---------------------------------------------------------------------------------------------
    def _resultados(self) -> None:  # noqa: PLR0915 - los apartados del informe interactivo, en su orden
        c = self.calculo
        mes = mes_y_anio(c.periodo)
        anio = c.anio
        n = 5
        self.titulo1(f"{n}. Resultados")
        self.p(
            f"Esta sección recorre las legalizaciones radicadas en {mes}: primero el resumen del mes por metodología, después la comparación "
            f"con el mes anterior, la evolución de {anio}, el volumen general frente al año anterior, al mes anterior y a su media móvil, el "
            "porcentaje de oportunidad con todas sus vistas, el resultado y la tasa de legalización, los tiempos de respuesta y, por último, "
            "las metodologías y los tipos de documento. Cada gráfico y cada tabla van seguidos de su lectura."
        )
        self._resumen_del_mes(n)
        self._comparacion_mes_anterior(n)
        self._evolucion_del_anio(n)
        self._volumen_general(n)
        self._oportunidad(n)
        self._resultado(n)
        self._tiempos(n)
        self._metodologias(n)
        self._tipos_documento(n)

    def _resumen_del_mes(self, n: int) -> None:
        c = self.calculo
        mes = mes_y_anio(c.periodo)
        m = c.mes
        mets = c.metodologias_mes
        self.titulo2(
            f"{n}.1 Resumen del mes",
            f"Cuántos documentos de cada metodología se radicaron en {mes}, cuánto pesa cada una, cómo terminaron al corte y con qué oportunidad.",
        )
        filas = [
            [
                k.nombre,
                entero(v.radicadas),
                _pct(c.participacion(v), 1),
                entero(v.legalizadas),
                entero(v.canceladas),
                entero(v.en_curso),
                _pct(v.oportunidad),
            ]
            for k, v in mets
        ]
        filas.append(
            [
                "Total",
                entero(m.radicadas),
                _pct(1.0, 1),
                entero(m.legalizadas),
                entero(m.canceladas),
                entero(m.en_curso),
                _pct(m.oportunidad),
            ]
        )
        self.tabla(
            f"Resumen por metodología en {mes}: radicadas, participación, resultado al corte y porcentaje de oportunidad",
            ["Metodología", "Radicadas", "Participación", "Legalizadas", "Canceladas", "En curso", "% de oportunidad"],
            filas,
            [1.4, 0.85, 1.0, 0.95, 0.9, 0.8, 1.45],
            lectura=interp.tabla_metodologias(c),
            numericas={1, 2, 3, 4, 5, 6},
            resaltar=len(filas) - 1,
        )
        self.grafico(
            gc.barras_por_canal(
                [k.nombre for k, _ in mets],
                [v.radicadas for _, v in mets],
                [gl.color_metodologia(k.fuente, i) for i, (k, _) in enumerate(mets)],
            ),
            f"Documentos radicados por metodología en {mes}, de mayor a menor.",
            interp.barras_metodologias(c),
        )
        self.grafico(
            gc.barras_por_canal(
                ["Legalizadas", "Canceladas", "En curso"],
                [m.legalizadas, m.canceladas, m.en_curso],
                [AZUL, ROJO, AMARILLO],
            ),
            f"Resultado al corte de los documentos radicados en {mes}: legalizados, cancelados y en curso.",
            interp.resultado_mes(c),
        )
        self.grafico(
            gtr.treemap([(k.nombre, v.radicadas, gl.color_metodologia(k.fuente, i)) for i, (k, v) in enumerate(mets)]),
            f"Participación de cada metodología en {mes}: el área es proporcional a sus radicadas.",
            interp.treemap_metodologias(c),
        )

    def _comparacion_mes_anterior(self, n: int) -> None:
        c = self.calculo
        m, ant = c.mes, c.mes_anterior
        anio = c.anio
        if ant is None or not c.periodo_anterior:
            self.titulo2(
                f"{n}.2 Comparación con el mes inmediatamente anterior",
                f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico de la plataforma: no hay un mes anterior con datos para comparar.",
            )
            self.p(f"La comparación con el mes anterior empieza en el informe de {mes_y_anio_siguiente(c.periodo)}.")
            return
        mes_ant, mes_act = nombre_mes(c.periodo_anterior), nombre_mes(c.periodo)
        col_ant, col_act = mayuscula_inicial(mes_corto(c.periodo_anterior)), mayuscula_inicial(mes_corto(c.periodo))
        self.titulo2(
            f"{n}.2 Comparación con {mes_ant}, el mes inmediatamente anterior",
            f"Qué cambió entre {mes_ant} y {mes_act} de {anio} en los indicadores del mes y en las radicadas de cada metodología.",
        )
        filas = [
            [
                "Documentos radicados",
                entero(ant.radicadas),
                entero(m.radicadas),
                f"{_dif(m.radicadas, ant.radicadas)} ({variacion(m.radicadas, ant.radicadas)})",
            ],
            [
                "Legalizadas",
                entero(ant.legalizadas),
                entero(m.legalizadas),
                f"{_dif(m.legalizadas, ant.legalizadas)} ({variacion(m.legalizadas, ant.legalizadas)})",
            ],
            ["Canceladas", entero(ant.canceladas), entero(m.canceladas), _dif(m.canceladas, ant.canceladas)],
            ["En curso al corte", entero(ant.en_curso), entero(m.en_curso), _dif(m.en_curso, ant.en_curso)],
            [
                "Tasa de legalización",
                _pct(ant.tasa_legalizacion),
                _pct(m.tasa_legalizacion),
                _pp(m.tasa_legalizacion, ant.tasa_legalizacion),
            ],
            [
                "Legalizadas a tiempo",
                entero(ant.a_tiempo),
                entero(m.a_tiempo),
                f"{_dif(m.a_tiempo, ant.a_tiempo)} ({variacion(m.a_tiempo, ant.a_tiempo)})",
            ],
            [
                "Legalizadas extemporáneas",
                entero(ant.extemporaneas),
                entero(m.extemporaneas),
                _dif(m.extemporaneas, ant.extemporaneas),
            ],
            ["% de oportunidad", _pct(ant.oportunidad), _pct(m.oportunidad), _pp(m.oportunidad, ant.oportunidad)],
            [
                "Días hábiles de gestión (promedio)",
                _dec(ant.promedio_dias_habiles_legalizadas),
                _dec(m.promedio_dias_habiles_legalizadas),
                _dif_dias(m.promedio_dias_habiles_legalizadas, ant.promedio_dias_habiles_legalizadas),
            ],
            [
                "Días calendario (promedio)",
                _dec(ant.promedio_dias_legalizadas),
                _dec(m.promedio_dias_legalizadas),
                _dif_dias(m.promedio_dias_legalizadas, ant.promedio_dias_legalizadas),
            ],
            [
                "Pasaron por complementación",
                _pct(ant.tasa_complementacion, 1),
                _pct(m.tasa_complementacion, 1),
                _pp(m.tasa_complementacion, ant.tasa_complementacion),
            ],
            [
                "Pasaron por validación con la IES",
                _pct(ant.tasa_validacion_ies, 1),
                _pct(m.tasa_validacion_ies, 1),
                _pp(m.tasa_validacion_ies, ant.tasa_validacion_ies),
            ],
        ]
        self.tabla(
            f"Indicadores de {mes_ant} y {mes_act} de {anio}: volumen, resultado, oportunidad y tiempos, con la diferencia",
            ["Indicador", col_ant, col_act, "Diferencia"],
            filas,
            [2.3, 1.1, 1.1, 1.5],
            lectura=interp.comparacion_indicadores(c),
            numericas={1, 2, 3},
        )
        anteriores = c.metodologias_mes_anterior
        filas = []
        for k, v in c.metodologias_mes:
            previa = anteriores.get(k.id)
            filas.append(
                [
                    k.nombre,
                    entero(previa.radicadas) if previa else GUION,
                    entero(v.radicadas),
                    _dif(v.radicadas, previa.radicadas if previa else None),
                    variacion(v.radicadas, previa.radicadas if previa else None),
                ]
            )
        filas.append(
            [
                "Total",
                entero(ant.radicadas),
                entero(m.radicadas),
                _dif(m.radicadas, ant.radicadas),
                variacion(m.radicadas, ant.radicadas),
            ]
        )
        self.tabla(
            f"Documentos radicados por metodología: {mes_ant} y {mes_act} de {anio}, con la diferencia y la variación",
            ["Metodología", col_ant, col_act, "Diferencia", "Variación"],
            filas,
            [2.5, 1.0, 1.0, 1.0, 1.0],
            lectura=interp.comparacion_metodologias(c),
            numericas={1, 2, 3, 4},
            resaltar=len(filas) - 1,
        )

    def _evolucion_del_anio(self, n: int) -> None:
        c = self.calculo
        anio = c.anio
        self.titulo2(
            f"{n}.3 Evolución de {anio}",
            f"Los documentos radicados cada mes de {anio} frente al promedio mensual, el resultado de cada mes con su tasa de legalización y cómo se reparten las metodologías.",
        )
        if len(c.serie_anio) < 2:
            self.p(
                f"{mayuscula_inicial(nombre_mes(c.periodo))} es el primer mes de {anio} con datos: las vistas mes a mes del año (radicadas frente al promedio, "
                "resultado por mes y mezcla de metodologías) empiezan en el informe siguiente."
            )
            return
        etiquetas = _etiquetas(c.serie_anio)
        resaltar = next((i for i, (p, _) in enumerate(c.serie_anio) if p == c.periodo), None)
        promedio = c.promedio_mensual or 0
        self.grafico(
            gtr.barras_con_referencia(
                etiquetas, [m.radicadas for _, m in c.serie_anio], AZUL, ("Promedio mensual", promedio), resaltar
            ),
            f"Documentos radicados por mes en {anio}, con el promedio mensual de los meses con datos.",
            interp.radicadas_por_mes(c),
        )
        filas = [
            [
                mayuscula_inicial(nombre_mes(p)),
                entero(m.radicadas),
                decimal(promedio, 1),
                _dif(m.radicadas, promedio),
                variacion(m.radicadas, promedio),
            ]
            for p, m in c.serie_anio
        ]
        filas.append([tramo_del_anio(c.periodo, mayuscula=True), entero(c.acumulado.radicadas), "", "", ""])
        self.tabla(
            f"Documentos radicados por mes en {anio} frente al promedio mensual: diferencia en documentos y en porcentaje",
            ["Mes", "Radicadas", "Promedio", "Diferencia", "Variación"],
            filas,
            [1.6, 1.2, 1.1, 1.1, 1.1],
            numericas={1, 2, 3, 4},
            resaltar=len(filas) - 1,
        )
        partes_resultado = [
            ("Legalizadas", AZUL, [m.legalizadas for _, m in c.serie_anio]),
            ("Canceladas", ROJO, [m.canceladas for _, m in c.serie_anio]),
            ("En curso", AMARILLO, [m.en_curso for _, m in c.serie_anio]),
        ]
        self.grafico(
            gc.barras_con_linea(
                etiquetas,
                partes_resultado,
                ("Tasa de legalización", [m.tasa_legalizacion for _, m in c.serie_anio]),
                apiladas=True,
                resaltar=resaltar,
            ),
            f"Resultado al corte de los documentos radicados cada mes de {anio}, apilado, con la tasa de legalización del mes encima.",
            interp.resultado_por_mes(c),
        )
        self.grafico(
            gc.mezcla(etiquetas, partes_resultado),
            f"Resultado de cada mes de {anio} al 100 %: la parte legalizada, cancelada y en curso.",
            interp.resultado_100(c),
        )
        # la mezcla de metodologías: las seis mayores del año y el resto juntas en «Otras»
        mayores = [k for k, _ in c.metodologias_anio[:6]]
        partes = []
        for i, k in enumerate(mayores):
            partes.append(
                (
                    k.nombre,
                    gl.color_metodologia(k.fuente, i),
                    [por_mes.get(k.id, 0) for _, por_mes in c.metodologia_por_mes],
                )
            )
        ids = {k.id for k in mayores}
        resto = [sum(v for id_, v in por_mes.items() if id_ not in ids) for _, por_mes in c.metodologia_por_mes]
        if any(resto):
            partes.append(("Otras", "#c2cde0", resto))
        catalogo = {k.id: k for k, _ in c.metodologias_anio}
        self.grafico(
            gc.mezcla(etiquetas, partes),
            f"Cómo se reparten las metodologías mes a mes en {anio}, al 100 %"
            + (" (las de menor volumen van juntas en «Otras»)." if any(resto) else "."),
            interp.mezcla_metodologias(c, catalogo),
        )

    def _volumen_general(self, n: int) -> None:
        c = self.calculo
        anio = c.anio
        self.titulo2(
            f"{n}.4 Volumen general",
            f"Los documentos radicados por mes frente al mismo mes de {anio - 1}, frente al mes anterior y frente a su media móvil simple de tres meses.",
        )
        dibujados = 0
        actual = {int(p[5:7]): m.radicadas for p, m in c.serie_anio}
        anterior = {int(p[5:7]): m.radicadas for p, m in c.serie_anio_anterior}
        if len(c.serie_anio) >= 2 or anterior:
            self.grafico(
                gt.dos_anios(actual, anterior, anio, "entero", hasta=c.mes_numero),
                f"Documentos radicados por mes, {anio}" + (f" frente a {anio - 1}." if anterior else "."),
                interp.dos_anios_radicadas(c),
            )
            dibujados += 1
            if anterior:
                filas = [
                    [
                        mayuscula_inicial(nombre_mes(p)),
                        entero(m.radicadas),
                        entero(anterior[int(p[5:7])]) if int(p[5:7]) in anterior else GUION,
                        _dif(m.radicadas, anterior.get(int(p[5:7]))),
                        variacion(m.radicadas, anterior.get(int(p[5:7]))),
                    ]
                    for p, m in c.serie_anio
                ]
                filas.append(
                    [
                        tramo_del_anio(c.periodo, mayuscula=True),
                        entero(c.acumulado.radicadas),
                        entero(c.acumulado_anterior.radicadas) if c.acumulado_anterior else GUION,
                        _dif(c.acumulado.radicadas, c.acumulado_anterior.radicadas if c.acumulado_anterior else None),
                        variacion(
                            c.acumulado.radicadas, c.acumulado_anterior.radicadas if c.acumulado_anterior else None
                        ),
                    ]
                )
                self.tabla(
                    f"Documentos radicados por mes, {anio} frente a {anio - 1}: diferencia en documentos y en porcentaje",
                    ["Mes", str(anio), str(anio - 1), "Diferencia", "Variación"],
                    filas,
                    [1.6, 1.2, 1.1, 1.1, 1.1],
                    numericas={1, 2, 3, 4},
                    resaltar=len(filas) - 1,
                )
        serie13 = c.serie_13
        if len(serie13) >= 2:
            valores = [None] + [
                ((serie13[i][1].radicadas / serie13[i - 1][1].radicadas - 1) * 100)
                if serie13[i - 1][1].radicadas
                else None
                for i in range(1, len(serie13))
            ]
            self.grafico(
                gt.barras_variacion(_etiquetas(serie13), valores, "%"),
                f"Variación de los documentos radicados frente al mes anterior, últimos {len(serie13)} meses.",
                interp.variacion_radicadas(c),
            )
            dibujados += 1
        if any(c.media_movil_radicadas.get(p) is not None for p, _ in serie13):
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, float(m.radicadas)) for p, m in serie13],
                    [(p, c.media_movil_radicadas.get(p)) for p, _ in serie13],
                    c.periodo,
                    "entero",
                    "Radicadas",
                ),
                f"Documentos radicados frente a su media móvil simple de tres meses, últimos {len(serie13)} meses.",
                interp.media_movil_radicadas(c),
            )
            dibujados += 1
        if not dibujados:
            self.p(
                f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico de la plataforma: las vistas de volumen "
                f"(frente a {anio - 1}, frente al mes anterior y frente a la media móvil) empiezan en los informes siguientes."
            )

    def _oportunidad(self, n: int) -> None:
        c = self.calculo
        anio = c.anio
        m = c.mes
        plazo = plazo_en_texto(c)
        self.titulo2(
            f"{n}.5 Porcentaje de oportunidad",
            f"Cuántas de las legalizadas se gestionaron en hasta {plazo}, de la radicación a la legalización: el índice mes a mes y frente al año "
            "anterior, lo a tiempo y lo extemporáneo, su variación, su media móvil, el mapa de calor, la distribución por días hábiles y la "
            "oportunidad por metodología y por tipo de documento.",
        )
        actual = {int(p[5:7]): x.oportunidad for p, x in c.serie_anio}
        anterior = {int(p[5:7]): x.oportunidad for p, x in c.serie_anio_anterior}
        con_anterior = any(v is not None for v in anterior.values())
        if len(c.serie_anio) >= 2 or con_anterior:
            self.grafico(
                gt.dos_anios(actual, anterior, anio, "porcentaje", hasta=c.mes_numero, leyenda="lower right"),
                f"Porcentaje de oportunidad por mes, {anio}" + (f" frente a {anio - 1}." if con_anterior else "."),
                interp.oportunidad_dos_anios(c),
            )
            if con_anterior:
                filas = [
                    [
                        mayuscula_inicial(nombre_mes(p)),
                        _pct(x.oportunidad),
                        _pct(anterior.get(int(p[5:7]))),
                        _pp(x.oportunidad, anterior.get(int(p[5:7]))),
                    ]
                    for p, x in c.serie_anio
                ]
                filas.append(
                    [
                        tramo_del_anio(c.periodo, mayuscula=True),
                        _pct(c.acumulado.oportunidad),
                        _pct(c.acumulado_anterior.oportunidad) if c.acumulado_anterior else GUION,
                        _pp(
                            c.acumulado.oportunidad, c.acumulado_anterior.oportunidad if c.acumulado_anterior else None
                        ),
                    ]
                )
                self.tabla(
                    f"Porcentaje de oportunidad por mes, {anio} frente a {anio - 1}, con la diferencia en puntos porcentuales",
                    ["Mes", str(anio), str(anio - 1), "Diferencia"],
                    filas,
                    [1.8, 1.2, 1.2, 1.2],
                    numericas={1, 2, 3},
                    resaltar=len(filas) - 1,
                )
        if len(c.serie_anio) >= 2:
            etiquetas = _etiquetas(c.serie_anio)
            resaltar = next((i for i, (p, _) in enumerate(c.serie_anio) if p == c.periodo), None)
            self.grafico(
                gc.barras_con_linea(
                    etiquetas,
                    [
                        ("A tiempo", AZUL, [x.a_tiempo for _, x in c.serie_anio]),
                        ("Extemporáneas", ROJO, [x.extemporaneas for _, x in c.serie_anio]),
                    ],
                    ("% de oportunidad", [x.oportunidad for _, x in c.serie_anio]),
                    apiladas=True,
                    resaltar=resaltar,
                ),
                f"Legalizadas a tiempo (hasta {plazo}) y extemporáneas por mes de radicación en {anio}, con el porcentaje de oportunidad encima.",
                interp.a_tiempo_por_mes(c),
            )
        serie13 = c.serie_13
        cambios = [None] + [
            ((serie13[i][1].oportunidad - serie13[i - 1][1].oportunidad) * 100)
            if serie13[i][1].oportunidad is not None and serie13[i - 1][1].oportunidad is not None
            else None
            for i in range(1, len(serie13))
        ]
        if any(v is not None for v in cambios):
            self.grafico(
                gt.barras_variacion(_etiquetas(serie13), cambios, "pp"),
                f"Variación del porcentaje de oportunidad frente al mes anterior, en puntos porcentuales, últimos {len(serie13)} meses.",
                interp.variacion_oportunidad(c),
            )
        if any(c.media_movil_oportunidad.get(p) is not None for p, _ in serie13):
            self.grafico(
                gt.linea_con_media_movil(
                    [(p, x.oportunidad) for p, x in serie13],
                    [(p, c.media_movil_oportunidad.get(p)) for p, _ in serie13],
                    c.periodo,
                    "porcentaje",
                    "Oportunidad",
                ),
                f"Porcentaje de oportunidad frente a su media móvil ponderada de tres meses, últimos {len(serie13)} meses.",
                interp.media_movil_oportunidad(c),
            )
        celdas = sum(
            1
            for meses in c.matriz_oportunidad.values()
            for mes_n, v in meses.items()
            if v is not None and mes_n <= c.mes_numero
        )
        if celdas >= 2:
            self.grafico(
                gt.mapa_calor(c.matriz_oportunidad, (anio, c.mes_numero), hasta=c.mes_numero),
                f"Mapa de calor del porcentaje de oportunidad por mes y año, {'en' if c.mes_numero == 1 else 'de'} {tramo_del_anio(c.periodo)} de cada año.",
                interp.mapa_calor(c),
            )
        self.grafico(
            gl.histograma_habiles(m.habiles, c.plazo),
            f"Distribución de las {entero(m.legalizadas_con_fecha)} legalizadas con fecha de {mes_y_anio(c.periodo)} por días hábiles de gestión, con el plazo marcado.",
            interp.histograma(c),
        )
        self._oportunidad_categoria(c.metodologias_mes, "metodologia", "Metodología")
        self._oportunidad_categoria(c.documentos_mes[:MAXIMO_BARRAS], "documento", "Tipo de documento")

    def _oportunidad_categoria(self, grupos: Grupos, clase: str, etiqueta: str) -> None:
        c = self.calculo
        con_fecha = [(k, v) for k, v in grupos if v.legalizadas_con_fecha > 0]
        if not con_fecha:
            return
        mes = mes_y_anio(c.periodo)
        que = (
            "las metodologías"
            if clase == "metodologia"
            else f"los {len(con_fecha)} tipos de documento de mayor volumen"
        )
        self.grafico(
            gl.barras_apiladas_horizontales(
                [k.nombre for k, _ in con_fecha],
                [
                    ("A tiempo", AZUL, [v.a_tiempo for _, v in con_fecha]),
                    ("Extemporáneas", ROJO, [v.extemporaneas for _, v in con_fecha]),
                ],
                [f"{entero(v.legalizadas_con_fecha)} · {_pct(v.oportunidad, 1)} a tiempo" for _, v in con_fecha],
            ),
            f"Legalizadas a tiempo y extemporáneas de {que} en {mes}, con el total y su porcentaje de oportunidad.",
            interp.oportunidad_categoria(c, con_fecha, clase),
        )
        filas = [
            [
                k.nombre,
                entero(v.legalizadas_con_fecha),
                entero(v.a_tiempo),
                entero(v.extemporaneas),
                _pct(v.oportunidad),
                _dec(v.promedio_dias_habiles_legalizadas),
            ]
            for k, v in con_fecha
        ]
        m = c.mes
        filas.append(
            [
                "Total del mes",
                entero(m.legalizadas_con_fecha),
                entero(m.a_tiempo),
                entero(m.extemporaneas),
                _pct(m.oportunidad),
                _dec(m.promedio_dias_habiles_legalizadas),
            ]
        )
        self.tabla(
            f"Oportunidad por {etiqueta.lower()} en {mes}: legalizadas con fecha, a tiempo, extemporáneas, porcentaje de oportunidad y días hábiles promedio de gestión",
            [etiqueta, "Legalizadas", "A tiempo", "Extemporáneas", "% de oportunidad", "Días hábiles"],
            filas,
            [1.75, 0.9, 0.85, 1.05, 1.15, 0.95],
            numericas={1, 2, 3, 4, 5},
            resaltar=len(filas) - 1,
        )

    def _resultado(self, n: int) -> None:
        c = self.calculo
        anio = c.anio
        self.titulo2(
            f"{n}.6 Resultado y tasa de legalización",
            f"La tasa de legalización mes a mes frente a {anio - 1} y el resultado al corte de cada metodología y de cada tipo de documento.",
        )
        actual = {int(p[5:7]): x.tasa_legalizacion for p, x in c.serie_anio}
        anterior = {int(p[5:7]): x.tasa_legalizacion for p, x in c.serie_anio_anterior}
        con_anterior = any(v is not None for v in anterior.values())
        if len(c.serie_anio) >= 2 or con_anterior:
            self.grafico(
                gt.dos_anios(actual, anterior, anio, "porcentaje", hasta=c.mes_numero, leyenda="lower right"),
                f"Tasa de legalización por mes de radicación, {anio}"
                + (f" frente a {anio - 1}." if con_anterior else "."),
                interp.tasa_dos_anios(c),
            )
            if con_anterior:
                filas = [
                    [
                        mayuscula_inicial(nombre_mes(p)),
                        _pct(x.tasa_legalizacion),
                        _pct(anterior.get(int(p[5:7]))),
                        _pp(x.tasa_legalizacion, anterior.get(int(p[5:7]))),
                    ]
                    for p, x in c.serie_anio
                ]
                self.tabla(
                    f"Tasa de legalización por mes, {anio} frente a {anio - 1}, con la diferencia en puntos porcentuales",
                    ["Mes", str(anio), str(anio - 1), "Diferencia"],
                    filas,
                    [1.8, 1.2, 1.2, 1.2],
                    numericas={1, 2, 3},
                )
        else:
            self.p(
                f"{mayuscula_inicial(nombre_mes(c.periodo))} es el único mes con datos: la tasa de legalización mes a mes empieza en el informe siguiente."
            )
        self._resultado_categoria(c.metodologias_mes, "metodologia", "Metodología")
        self._resultado_categoria(c.documentos_mes[:MAXIMO_BARRAS], "documento", "Tipo de documento")

    def _resultado_categoria(self, grupos: Grupos, clase: str, etiqueta: str) -> None:
        c = self.calculo
        mes = mes_y_anio(c.periodo)
        que = "las metodologías" if clase == "metodologia" else f"los {len(grupos)} tipos de documento de mayor volumen"
        self.grafico(
            gl.barras_apiladas_horizontales(
                [k.nombre for k, _ in grupos],
                [
                    ("Legalizadas", AZUL, [v.legalizadas for _, v in grupos]),
                    ("Canceladas", ROJO, [v.canceladas for _, v in grupos]),
                    ("En curso", AMARILLO, [v.en_curso for _, v in grupos]),
                ],
                [f"{entero(v.radicadas)} · {_pct(v.tasa_legalizacion, 1)}" for _, v in grupos],
            ),
            f"Resultado al corte de {que} en {mes}: legalizadas, canceladas y en curso, con las radicadas y la tasa de legalización al final.",
            interp.resultado_categoria(c, grupos, clase),
        )
        filas = [
            [
                k.nombre,
                entero(v.radicadas),
                entero(v.legalizadas),
                _pct(v.tasa_legalizacion),
                entero(v.canceladas),
                entero(v.en_curso),
            ]
            for k, v in grupos
        ]
        m = c.mes
        filas.append(
            [
                "Total del mes",
                entero(m.radicadas),
                entero(m.legalizadas),
                _pct(m.tasa_legalizacion),
                entero(m.canceladas),
                entero(m.en_curso),
            ]
        )
        self.tabla(
            f"Resultado por {etiqueta.lower()} en {mes}: radicadas, legalizadas, tasa de legalización (legalizadas sobre legalizadas más canceladas), canceladas y en curso",
            [etiqueta, "Radicadas", "Legalizadas", "Tasa de legalización", "Canceladas", "En curso"],
            filas,
            [1.8, 0.9, 0.95, 1.4, 0.9, 0.8],
            numericas={1, 2, 3, 4, 5},
            resaltar=len(filas) - 1,
        )

    def _tiempos(self, n: int) -> None:
        c = self.calculo
        anio = c.anio
        self.titulo2(
            f"{n}.7 Tiempos de respuesta",
            "Cuántos días pasan entre la radicación de un documento y su resultado, en días calendario y en días hábiles: el promedio por mes, "
            "la distribución por rangos, las etapas de complementación y validación con la IES y los días por metodología.",
        )
        serie = c.serie_anio
        if len(serie) >= 2:
            etiquetas = _etiquetas(serie)
            resaltar = next((i for i, (p, _) in enumerate(serie) if p == c.periodo), None)
            self.grafico(
                gl.lineas_valores(
                    etiquetas,
                    [
                        ("Días calendario", AZUL, [x.promedio_dias for _, x in serie]),
                        ("Días hábiles", AMARILLO, [x.promedio_dias_habiles for _, x in serie]),
                    ],
                    "Días",
                    resaltar,
                ),
                f"Días promedio hasta el resultado de los documentos radicados cada mes de {anio}, en calendario y en hábiles.",
                interp.dias_por_mes(c),
            )
            filas = [
                [
                    mayuscula_inicial(nombre_mes(p)),
                    entero(x.con_dias),
                    _dec(x.promedio_dias),
                    _dec(x.promedio_dias_habiles),
                    _pct(x.hasta_cinco_dias, 1),
                    _pct(x.mas_de_quince_dias, 1),
                ]
                for p, x in serie
            ]
            a = c.acumulado
            filas.append(
                [
                    tramo_del_anio(c.periodo, mayuscula=True),
                    entero(a.con_dias),
                    _dec(a.promedio_dias),
                    _dec(a.promedio_dias_habiles),
                    _pct(a.hasta_cinco_dias, 1),
                    _pct(a.mas_de_quince_dias, 1),
                ]
            )
            self.tabla(
                f"Tiempos por mes en {anio}: documentos con resultado, días promedio (calendario y hábiles) y las dos colas de la distribución",
                ["Mes", "Con resultado", "Días calendario", "Días hábiles", "Hasta 5 días", "Más de 15 días"],
                filas,
                [1.2, 1.05, 1.1, 0.95, 0.95, 1.05],
                lectura=interp.tabla_tiempos(c),
                numericas={1, 2, 3, 4, 5},
                resaltar=len(filas) - 1,
            )
            self.grafico(
                gc.mezcla(
                    etiquetas,
                    [
                        (nombre, gl.COLORES_RANGOS[i], [x.rangos[i] for _, x in serie])
                        for i, nombre in enumerate(NOMBRES_RANGOS)
                    ],
                ),
                f"Distribución de los tiempos por mes en {anio}, al 100 %: la parte de cada rango de días calendario en los documentos con resultado.",
                interp.rangos_por_mes(c),
            )
            self.grafico(
                gc.lineas_niveles(
                    etiquetas,
                    [
                        ("Pasaron por complementación", ROJO, [x.tasa_complementacion for _, x in serie]),
                        ("Pasaron por validación con la IES", AMARILLO, [x.tasa_validacion_ies for _, x in serie]),
                    ],
                    resaltar,
                    leyenda="upper left",
                ),
                f"Parte de los documentos radicados cada mes de {anio} que pasó por complementación y por validación con la IES.",
                interp.etapas(c),
            )
        else:
            m = c.mes
            self.p(
                f"{mayuscula_inicial(nombre_mes(c.periodo))} es el único mes de {anio} con datos: los documentos con resultado tardaron en promedio "
                f"{_dec(m.promedio_dias)} días calendario y {_dec(m.promedio_dias_habiles)} días hábiles; el {_pct(m.hasta_cinco_dias, 1)} se resolvió en cinco "
                f"días o menos y el {_pct(m.mas_de_quince_dias, 1)} tardó más de quince. Las vistas mes a mes empiezan en el informe siguiente."
            )
        con_dias = [(k, v) for k, v in c.metodologias_mes if v.con_dias > 0]
        if con_dias:
            self.grafico(
                gl.barras_dobles_horizontales(
                    [k.nombre for k, _ in con_dias],
                    [
                        ("Días calendario", AZUL, [v.promedio_dias for _, v in con_dias]),
                        ("Días hábiles", AMARILLO, [v.promedio_dias_habiles for _, v in con_dias]),
                    ],
                ),
                f"Días promedio hasta el resultado por metodología en {mes_y_anio(c.periodo)}, de la de mayor a la de menor volumen.",
                interp.dias_categoria(c, con_dias),
            )

    def _metodologias(self, n: int) -> None:
        c = self.calculo
        anio = c.anio
        mes = mes_y_anio(c.periodo)
        mets = c.metodologias_mes
        self.titulo2(
            f"{n}.8 Por metodología",
            f"Las metodologías de mayor a menor volumen en {mes} con su participación acumulada, y cada una en lo corrido de {anio} frente a {anio - 1}.",
        )
        if len(mets) >= 2:
            self.grafico(
                gtr.pareto_tipos([(_corto(k), v.radicadas) for k, v in mets]),
                f"Pareto de las metodologías en {mes}: radicadas de mayor a menor y participación acumulada, con la guía del 80 %.",
                interp.pareto_categoria(c, mets, "metodologia"),
            )
        self._categoria_dos_anios(c.metodologias_anio, c.metodologias_anio_anterior, "metodologia", "Metodología")

    def _tipos_documento(self, n: int) -> None:
        c = self.calculo
        anio = c.anio
        mes = mes_y_anio(c.periodo)
        docs = c.documentos_mes
        self.titulo2(
            f"{n}.9 Por tipo de documento",
            f"Qué documentos se radican para legalizar: los tipos de mayor volumen en {mes}, su participación, el Pareto y cada tipo en lo corrido de {anio} frente a {anio - 1}.",
        )
        mayores = docs[:MAXIMO_BARRAS]
        self.grafico(
            gc.barras_por_canal(
                [k.nombre for k, _ in mayores],
                [v.radicadas for _, v in mayores],
                [gl.color_documento(i) for i in range(len(mayores))],
            ),
            f"Documentos radicados por tipo de documento en {mes}, de mayor a menor"
            + (f" (los {len(mayores)} de mayor volumen)." if len(docs) > MAXIMO_BARRAS else "."),
            interp.barras_documentos(c),
        )
        items = [(k.nombre, v.radicadas, gl.color_documento(i)) for i, (k, v) in enumerate(docs[:MAXIMO_TREEMAP])]
        otros = sum(v.radicadas for _, v in docs[MAXIMO_TREEMAP:])
        if otros:
            items.append(("Otros", otros, "#c2cde0"))
        self.grafico(
            gtr.treemap(items),
            f"Participación de cada tipo de documento en {mes}: el área es proporcional a sus radicadas"
            + (" (los de menor volumen van juntos en «Otros»)." if otros else "."),
            interp.treemap_documentos(c, MAXIMO_TREEMAP),
        )
        if len(docs) >= 2:
            pareto = [
                (k.nombre if len(k.nombre) <= 22 else k.nombre[:21].rstrip() + "…", v.radicadas)
                for k, v in docs[:MAXIMO_TREEMAP]
            ]
            if otros:
                pareto.append(("Otros", otros))
            self.grafico(
                gtr.pareto_tipos(pareto),
                f"Pareto de los tipos de documento en {mes}: radicadas de mayor a menor y participación acumulada, con la guía del 80 %.",
                interp.pareto_categoria(c, docs, "documento"),
            )
        self._categoria_dos_anios(
            c.documentos_anio[:MAXIMO_BARRAS], c.documentos_anio_anterior, "documento", "Tipo de documento"
        )

    def _categoria_dos_anios(self, grupos: Grupos, anteriores: dict[int, Medidas], clase: str, etiqueta: str) -> None:
        c = self.calculo
        anio = c.anio
        con_par = any(k.id in anteriores for k, _ in grupos)
        tramo = tramo_del_anio(c.periodo)
        que = "metodología" if clase == "metodologia" else "tipo de documento"
        if not grupos:
            return
        if grupos and not con_par and c.meses_acumulado < 2:
            self.p(
                f"{mayuscula_inicial(nombre_mes(c.periodo))} es el único mes de {anio} con datos y no hay datos de {anio - 1}: el acumulado por {que} es el del "
                "mes, que ya muestra el resumen del mes, y la comparación con el año anterior empieza cuando haya con qué hacerla."
            )
            return
        self.grafico(
            gtr.tipos_dos_anios(
                [k.nombre for k, _ in grupos],
                [v.radicadas for _, v in grupos],
                [anteriores[k.id].radicadas if k.id in anteriores else None for k, _ in grupos],
                anio,
                anio - 1 if con_par else None,
            ),
            f"Documentos radicados por {que}, {tramo} de {anio}"
            + (f" frente a los mismos meses de {anio - 1}." if con_par else "."),
            interp.categoria_dos_anios(c, grupos, anteriores, clase),
        )
        if con_par:
            filas = [
                [
                    k.nombre,
                    entero(v.radicadas),
                    entero(anteriores[k.id].radicadas) if k.id in anteriores else GUION,
                    _dif(v.radicadas, anteriores[k.id].radicadas if k.id in anteriores else None),
                    variacion(v.radicadas, anteriores[k.id].radicadas if k.id in anteriores else None),
                ]
                for k, v in grupos
            ]
            filas.append(
                [
                    "Total",
                    entero(c.acumulado.radicadas),
                    entero(c.acumulado_anterior.radicadas) if c.acumulado_anterior else GUION,
                    _dif(c.acumulado.radicadas, c.acumulado_anterior.radicadas if c.acumulado_anterior else None),
                    variacion(c.acumulado.radicadas, c.acumulado_anterior.radicadas if c.acumulado_anterior else None),
                ]
            )
            self.tabla(
                f"Documentos radicados por {que}, {tramo} de {anio} y de {anio - 1}: diferencia y variación",
                [etiqueta, str(anio), str(anio - 1), "Diferencia", "Variación"],
                filas,
                [2.5, 1.0, 1.0, 1.0, 1.0],
                numericas={1, 2, 3, 4},
                resaltar=len(filas) - 1,
            )

    # --- anexos ---------------------------------------------------------------------------------------------------
    def _anexos(self) -> None:
        c = self.calculo
        anio = c.anio
        mes = mes_y_anio(c.periodo)
        self.titulo1("Anexo A. Documentos radicados por mes, metodología y resultado")
        self.p(interp.anexo(c), "Bajada")
        mets = c.metodologias_anio
        totales = {p: m.radicadas for p, m in c.serie_anio}
        # hasta seis metodologías por tabla, para que cada nombre quepa en un renglón; la última trae el total
        grupos = [mets[i : i + 6] for i in range(0, len(mets), 6)] or [[]]
        for k, grupo in enumerate(grupos, start=1):
            ultimo = k == len(grupos)
            encabezados = ["Mes", *[_corto(cat) for cat, _ in grupo], *(["Total"] if ultimo else [])]
            filas = [
                [
                    mayuscula_inicial(nombre_mes(p)),
                    *[entero(por_mes.get(cat.id, 0)) for cat, _ in grupo],
                    *([entero(totales[p])] if ultimo else []),
                ]
                for p, por_mes in c.metodologia_por_mes
            ]
            filas.append(
                [
                    "Total",
                    *[entero(v.radicadas) for _, v in grupo],
                    *([entero(c.acumulado.radicadas)] if ultimo else []),
                ]
            )
            anchos = [1.0, *[max(0.8, 0.1 * len(h)) for h in encabezados[1:]]]
            parte = f" ({k} de {len(grupos)})" if len(grupos) > 1 else ""
            self.tabla(
                f"Documentos radicados por mes y metodología, {anio}{parte}",
                encabezados,
                filas,
                anchos,
                numericas=set(range(1, len(encabezados))),
                resaltar=len(filas) - 1,
                compacta=True,
            )
        filas = [
            [
                mayuscula_inicial(nombre_mes(p)),
                entero(x.radicadas),
                entero(x.legalizadas),
                entero(x.canceladas),
                entero(x.en_curso),
                _pct(x.tasa_legalizacion),
                entero(x.a_tiempo),
                _pct(x.oportunidad),
                _dec(x.promedio_dias_habiles_legalizadas),
            ]
            for p, x in c.serie_anio
        ]
        a = c.acumulado
        filas.append(
            [
                "Total",
                entero(a.radicadas),
                entero(a.legalizadas),
                entero(a.canceladas),
                entero(a.en_curso),
                _pct(a.tasa_legalizacion),
                entero(a.a_tiempo),
                _pct(a.oportunidad),
                _dec(a.promedio_dias_habiles_legalizadas),
            ]
        )
        self.tabla(
            f"Resultado y oportunidad por mes de radicación, {anio}: la tasa de legalización es las legalizadas sobre las legalizadas más las canceladas; las a tiempo son las legalizadas en hasta {plazo_en_texto(c)} y la oportunidad, su porcentaje sobre las legalizadas con fecha",
            [
                "Mes",
                "Radicadas",
                "Legalizadas",
                "Canceladas",
                "En curso",
                "Tasa",
                "A tiempo",
                "Oportunidad",
                "Días hábiles",
            ],
            filas,
            [1.0, 0.9, 1.1, 1.0, 0.85, 0.8, 0.9, 1.1, 1.15],
            numericas=set(range(1, 9)),
            resaltar=len(filas) - 1,
            compacta=True,
        )
        self.titulo1("Anexo B. Ficha técnica")
        generado = fecha_generacion(self.procedencia)
        m = c.mes
        filas = [
            ["Informe", f"{TITULO_INFORME}, {mes}"],
            ["Entidad", f"{ENTIDAD}, {AREA}"],
            [
                "Fuente",
                "El sistema de legalización de documentos de educación superior del Ministerio: una fila por documento radicado para legalizar, con su "
                "estado y sus fechas de proceso, leída completa en cada publicación de la plataforma",
            ],
            ["Corte de los datos", fecha_larga(c.fecha_corte)],
            ["Datos publicados en la plataforma", fecha_larga(c.publicado_en[:10])],
            ["Versión del pipeline", c.version_pipeline or GUION],
            [
                "Plazo de oportunidad",
                f"{mayuscula_inicial(plazo_en_texto(c))} de gestión, de la radicación a la legalización",
            ],
            [
                "Universo del mes",
                f"{entero(m.radicadas)} documentos radicados en {mes}, de {numero_en_palabras(len(c.metodologias_mes))} metodologías y "
                f"{numero_en_palabras(len(c.documentos_mes), femenino=False)} tipos de documento",
            ],
            ["Histórico disponible", f"Desde {mes_y_anio(c.primer_periodo)}"],
            ["Informe interactivo", URL_INFORME],
            *filas_ficha(
                self.procedencia, "legalizaciones", "legalizaciones", c.periodo, "api/v1/legalizaciones/cubo.json"
            ),
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
    m = c.mes
    portada = Portada(
        ["Informe", "de Legalizaciones"],
        mes,
        [
            "Los documentos de educación superior radicados para legalizar en el mes: cuántos",
            f"terminaron legalizados, en cuántos días y qué parte dentro del plazo de {plazo_en_texto(c)}",
        ],
        fecha_larga(c.fecha_corte),
        [
            (entero(m.radicadas), "documentos radicados en el mes"),
            (_pct(m.oportunidad), "de oportunidad en el plazo"),
            (_pct(m.tasa_legalizacion), "tasa de legalización"),
        ],
        textos.hallazgos,
        URL_INFORME,
        nota_corte=nota_cifra(p, "legalizaciones", c.periodo),
    )
    cabecera = Cabecera(TITULO_INFORME, mes, fecha_larga(c.fecha_corte))
    historia = _Constructor(c, textos, p).construir()
    return generar_pdf(
        destino,
        portada,
        cabecera,
        historia,
        f"{TITULO_INFORME} · {mes}",
        "Legalización de documentos de educación superior: volumen, resultado, oportunidad y tiempos",
    )


__all__ = ["TITULO_INFORME", "URL_INFORME", "generar", "lista_en_prosa"]
