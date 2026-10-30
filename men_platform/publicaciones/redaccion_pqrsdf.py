"""La redacción del Informe General de PQRSDF: párrafos en tercera persona, lenguaje neutro y claro, que salen de las
cifras del mes con reglas explícitas. Resumen ejecutivo, objetivos, metodología, glosario, observaciones,
recomendaciones y conclusiones. Nada se escribe a mano para un mes concreto: todo vale para cualquier mes. Las PQRSDF
del mes son las «gestionadas en el mes»: aquellas cuyo plazo de respuesta vence en el mes del informe."""

from __future__ import annotations

from dataclasses import dataclass

from men_platform.publicaciones.datos_pqrsdf import Calculo, Totales
from men_platform.publicaciones.senales import PORCENTAJE, frase_senal, parametro_numerico, serie_hasta
from men_platform.publicaciones.texto_es import (
    capitalizar,
    con_articulo,
    decimal,
    entero,
    entre_tramo,
    fecha_larga,
    lista_en_prosa,
    mayuscula_inicial,
    mes_y_anio,
    nombre_mes,
    numero_en_palabras,
    porcentaje,
    puntos,
    puntos_sin_signo,
    tramo_del_anio,
    variacion,
    variacion_relativa,
)

UMBRAL_DEPENDENCIA = 100  # radicados mínimos para juzgar la oportunidad de una dependencia en el mes
UMBRAL_TIPO = 200
OPORTUNIDAD_BAJA = 0.80  # valor interno; lo reemplaza ref.parametro oportunidad_referencia_pqrsdf (D-82, P-36)


def _dif(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def _sube_baja(delta: float | None, sube: str = "subió", baja: str = "bajó", igual: str = "se mantuvo") -> str:
    if delta is None or abs(delta) < 0.00005:
        return igual
    return sube if delta > 0 else baja


def _mas_menos(delta: float | None) -> str:
    if delta is None or abs(delta) < 0.00005:
        return "igual"
    return "más" if delta > 0 else "menos"


def _volumen(actual: int, anterior: int | None) -> str:
    """«15,23 % mayor» o «3,10 % menor», para seguir a «un volumen»."""
    v = variacion_relativa(actual, anterior)
    if v is None:
        return "sin comparación"
    if abs(v) < 0.00005:
        return "igual"
    return f"{decimal(abs(v) * 100, 2)} % {'mayor' if v > 0 else 'menor'}"


@dataclass
class Textos:
    resumen: list[str]
    hallazgos: list[str]
    objetivo_general: str
    objetivos_especificos: list[str]
    metodologia: list[tuple[str, str]]
    observaciones: list[str]
    recomendaciones: list[str]
    conclusiones: list[str]
    glosario: list[tuple[str, str]]
    siglas: list[tuple[str, str]]


def _comparaciones_metodologia(c: Calculo, mes_ant: str, anio: int, anio_ant: int) -> str:
    """El párrafo de comparaciones de la metodología, según lo que exista para el mes: mes anterior, año anterior y acumulado."""
    tramo = tramo_del_anio(c.periodo)
    if c.mes_anterior is not None:
        texto = (
            f"El informe es mensual: el mes se compara en primer lugar con el mes inmediatamente anterior ({mes_ant}), en volumen, oportunidad, "
            "extemporáneas y tiempos, y también por dependencia"
        )
    else:
        texto = (
            f"El informe es mensual. {capitalizar(nombre_mes(c.periodo))} de {anio} es el primer mes del histórico, así que no hay un mes anterior "
            "con el cual compararlo"
        )
    if c.mismo_mes_anterior is not None or c.acumulado_anterior is not None:
        texto += f"; después, con el mismo mes de {anio_ant} y con el acumulado de {tramo} de {anio} frente al mismo tramo de {anio_ant}."
    elif c.mes_numero > 1:
        texto += (
            f"; después, con el acumulado de {tramo} de {anio}. El histórico empieza en enero de {anio}, así que todavía no hay un año anterior "
            "con el cual comparar."
        )
    else:
        texto += "."
    return texto + (
        " Las variaciones de volumen se expresan en porcentaje y las de oportunidad en puntos porcentuales (pp). La serie de trece meses "
        "permite leer la tendencia y la estacionalidad."
    )


def _aplicar_parametros(parametros: dict[str, str] | None) -> None:
    """El umbral de oportunidad baja sale de ref.parametro cuando la exportación lo trae (D-82, ficha FM-12)."""
    global OPORTUNIDAD_BAJA  # umbral del módulo: lo leen las observaciones y las recomendaciones
    OPORTUNIDAD_BAJA = parametro_numerico(parametros, "oportunidad_referencia_pqrsdf", OPORTUNIDAD_BAJA)


def redactar(c: Calculo, parametros: dict[str, str] | None = None) -> Textos:
    _aplicar_parametros(parametros)
    m, ant, mismo, acu, acu_ant = c.mes, c.mes_anterior, c.mismo_mes_anterior, c.acumulado, c.acumulado_anterior
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    mes_ant = nombre_mes(c.periodo_anterior_str())
    resumen: list[str] = []

    # 1. volumen
    frase = f"En {mes} el Ministerio de Educación Nacional gestionó {entero(m.radicados)} PQRSDF, es decir, las que tenían su plazo de respuesta en ese mes"
    partes = []
    if ant:
        partes.append(f"{variacion(m.radicados, ant.radicados)} frente a {mes_ant} ({entero(ant.radicados)})")
    if mismo:
        partes.append(
            f"{variacion(m.radicados, mismo.radicados)} frente a {nombre_mes(c.periodo)} de {anio_ant} ({entero(mismo.radicados)})"
        )
    resumen.append(frase + (": " + " y ".join(partes) if partes else "") + ".")

    # 2. oportunidad y comparación con el mes anterior
    frase = (
        f"La entidad respondió a tiempo {entero(m.a_tiempo)} de ellas, una oportunidad de respuesta de {porcentaje(m.oportunidad)}. "
        f"Las {entero(m.extemporaneas)} restantes ({porcentaje(m.tasa_extemporaneas)}) quedaron extemporáneas"
    )
    if m.abiertas_vencidas:
        frase += f"; de estas, {entero(m.abiertas_vencidas)} seguían abiertas al corte del {fecha_larga(c.fecha_corte)}"
    frase += "."
    if ant:
        d = _dif(m.oportunidad, ant.oportunidad)
        frase += (
            f" Frente a {mes_ant}, el mes inmediatamente anterior, la oportunidad {_sube_baja(d)} {puntos_sin_signo(d)} "
            f"(de {porcentaje(ant.oportunidad)} a {porcentaje(m.oportunidad)}) y las extemporáneas pasaron de {entero(ant.extemporaneas)} a {entero(m.extemporaneas)}."
        )
    if mismo:
        d = _dif(m.oportunidad, mismo.oportunidad)
        frase += f" Frente a {nombre_mes(c.periodo)} de {anio_ant} ({porcentaje(mismo.oportunidad)}), {_sube_baja(d)} {puntos_sin_signo(d)}."
    resumen.append(frase)

    # 3. acumulado
    frase = f"{entre_tramo(c.periodo)} de {anio} la entidad gestionó {entero(acu.radicados)} PQRSDF, con una oportunidad acumulada de {porcentaje(acu.oportunidad)}"
    if acu_ant:
        d = _dif(acu.oportunidad, acu_ant.oportunidad)
        frase += f", {puntos(d)} frente al mismo periodo de {anio_ant} ({porcentaje(acu_ant.oportunidad)}, con {entero(acu_ant.radicados)} gestionadas)"
    frase += "."
    resumen.append(frase)

    # 4. tiempos
    frase = f"El tiempo promedio de gestión del mes fue de {decimal(m.promedio_dias_gestion, 1)} días hábiles"
    if ant:
        frase += f" ({decimal(ant.promedio_dias_gestion, 1)} en {mes_ant})"
    if m.promedio_dias_retraso is not None:
        frase += f" y las extemporáneas se atendieron, en promedio, {decimal(m.promedio_dias_retraso, 1)} días hábiles después de su vencimiento"
    if acu.promedio_dias_gestion is not None:
        frase += (
            f"; en lo corrido del año el promedio de gestión es de {decimal(acu.promedio_dias_gestion, 1)} días hábiles"
        )
    frase += "."
    resumen.append(frase)

    # 5. concentración por dependencia
    deps = [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"]
    if deps:
        top = deps[:2]
        parte_top = sum(t.radicados for _, t in top) / m.radicados if m.radicados else 0
        frase = (
            f"{lista_en_prosa([f'{con_articulo(k)} ({entero(t.radicados)}, {porcentaje(t.oportunidad)} a tiempo)' for k, t in top])} "
            f"concentraron el {porcentaje(parte_top, 1)} del volumen del mes entre {c.total_dependencias_con_radicados} dependencias con radicados."
        )
        frase = mayuscula_inicial(frase)
        bajas = sorted(
            [(k, t) for k, t in deps if t.radicados >= UMBRAL_DEPENDENCIA], key=lambda kt: kt[1].oportunidad or 0
        )[:3]
        if bajas:
            frase += f" Las menores oportunidades entre las dependencias con al menos {UMBRAL_DEPENDENCIA} radicados fueron las de {lista_en_prosa([f'{con_articulo(k)} ({porcentaje(t.oportunidad)})' for k, t in bajas])}."
        resumen.append(frase)

    # 6. tipos y canal
    tipos = [(k, t) for k, t in c.por_tipo if k != "sin homologar"]
    if tipos:
        k0, t0 = tipos[0]
        frase = f"Por tipo de requerimiento, {capitalizar(k0).lower() if not k0.isupper() else k0} representó el {porcentaje(t0.radicados / m.radicados if m.radicados else None, 1)} de lo gestionado, con {porcentaje(t0.oportunidad)} a tiempo"
        peor = sorted([(k, t) for k, t in tipos if t.radicados >= UMBRAL_TIPO], key=lambda kt: kt[1].oportunidad or 0)
        if peor and peor[0][0] != k0:
            frase += f"; el tipo con menor oportunidad entre los de más de {UMBRAL_TIPO} radicados fue {capitalizar(peor[0][0]).lower()} ({porcentaje(peor[0][1].oportunidad)})"
        frase += "."
        if c.por_canal:
            canales = [(k, t) for k, t in c.por_canal if k != "sin informacion"]
            if canales:
                frase += f" Por canal de radicación, {lista_en_prosa([f'{capitalizar(k).lower()} {porcentaje(t.radicados / m.radicados if m.radicados else None, 1)} ({porcentaje(t.oportunidad)} a tiempo)' for k, t in canales[:3]])}."
        resumen.append(frase)

    # 7. pronóstico
    if c.pronostico and c.pronostico[-1][0] == c.periodo and c.pronostico[-1][1] is not None:
        _, real, pron = c.pronostico[-1]
        d = real - pron
        resumen.append(
            f"El modelo {c.modelo_pronostico.upper()} esperaba una oportunidad de {porcentaje(pron)} para el mes; el resultado real, {porcentaje(real)}, quedó "
            f"{decimal(abs(d) * 100, 2)} puntos porcentuales {'por encima' if d > 0 else 'por debajo'} de lo previsto."
        )

    hallazgos = [
        f"{entero(m.radicados)} PQRSDF gestionadas en el mes",
        f"{porcentaje(m.oportunidad)} respondidas a tiempo"
        + (f" ({puntos(_dif(m.oportunidad, ant.oportunidad))} frente a {mes_ant})" if ant else ""),
        f"{entero(m.extemporaneas)} extemporáneas ({porcentaje(m.tasa_extemporaneas)})",
        f"{decimal(m.promedio_dias_gestion, 1)} días hábiles de gestión en promedio",
        f"{porcentaje(acu.oportunidad)} de oportunidad acumulada en {anio}",
    ]

    objetivo_general = (
        f"Presentar el comportamiento de la oportunidad de respuesta de las PQRSDF gestionadas por el Ministerio de Educación Nacional en {mes}, "
        "a partir de los agregados oficiales de la Plataforma de Analítica de Datos, como insumo para el seguimiento y la toma de decisiones de la "
        "entidad en su conjunto: la alta dirección, las dependencias que responden y las áreas que acompañan la atención a la ciudadanía."
    )
    comparaciones = []
    if c.mes_anterior is not None:
        comparaciones.append("con el mes inmediatamente anterior")
    if c.mismo_mes_anterior is not None:
        comparaciones.append(f"con el mismo mes de {anio_ant}")
    if c.mes_numero > 1:
        comparaciones.append("con el acumulado del año")
    objetivos_especificos = [
        f"Cuantificar el volumen de PQRSDF gestionadas en {mes}, su oportunidad de respuesta y sus tiempos de gestión"
        + (f", y compararlos {lista_en_prosa(comparaciones)}." if comparaciones else "."),
        "Caracterizar la gestión por viceministerio, dependencia, grupo interno de trabajo, tipo de requerimiento, canal de radicación y eje temático, "
        "e identificar dónde se concentran el volumen y las respuestas extemporáneas.",
        "Formular observaciones, recomendaciones y conclusiones que orienten acciones de mejora de la oportunidad en el mes siguiente"
        + (", con el pronóstico del modelo como referencia." if c.pronostico else "."),
    ]

    metodologia = [
        (
            "Fuentes de información",
            "Las cifras provienen del archivo mensual que el sistema de gestión documental del Ministerio entrega a la Subdirección de Relacionamiento con "
            "la Ciudadanía con las PQRSDF cuyo plazo de respuesta vence en el mes. La plataforma lo carga en una base de datos con reglas de negocio escritas "
            f"y versionadas, calcula los agregados y los publica; este informe se genera desde esos mismos agregados, con el corte del {fecha_larga(c.fecha_corte)}.",
        ),
        (
            "Universo y unidad de análisis",
            f"Las PQRSDF gestionadas en {mes} son las que tenían su fecha de vencimiento en ese mes, sin importar cuándo se radicaron: son las que la entidad "
            "debía responder en el mes. La unidad de análisis es el radicado; cada uno cuenta una sola vez, en el mes de su vencimiento. El histórico "
            f"disponible comienza en {mes_y_anio(c.primer_periodo)}.",
        ),
        (
            "Estados de oportunidad",
            "Como el archivo se descarga por fecha de vencimiento, toda PQRSDF del mes ya venció al corte y queda en uno de dos estados: a tiempo, si se "
            "cerró en la fecha de vencimiento o antes (se compara solo la fecha, sin la hora), o extemporánea, en cualquier otro caso. Una extemporánea "
            "puede estar cerrada, si ya se respondió después del plazo, o abierta, si al corte seguía sin respuesta; el informe presenta las dos partes "
            "porque la abierta todavía se puede atender.",
        ),
        (
            "Indicadores",
            "La oportunidad de respuesta es el cociente entre las PQRSDF respondidas a tiempo y el total gestionado en el periodo. Los días hábiles de gestión "
            "van de la radicación a la finalización (o a la foto, si el radicado sigue abierto) y se promedian sobre todas las gestionadas; los días hábiles "
            "de retraso cuentan desde el vencimiento hasta la finalización y se promedian solo sobre las extemporáneas. Los días hábiles excluyen fines de "
            "semana y festivos de Colombia.",
        ),
        ("Comparaciones", _comparaciones_metodologia(c, mes_ant, anio, anio_ant)),
        (
            "Pronóstico",
            f"El pronóstico mensual del índice de oportunidad lo produce un modelo {c.modelo_pronostico.upper()} del área, ajustado por fuera de la plataforma "
            "para la entidad completa. El informe muestra el valor previsto y el real de cada mes del año, hasta el mes del informe.",
        ),
        (
            "Alcance, calidad y limitaciones",
            "Las dependencias se presentan con su nombre vigente y los grupos internos de trabajo se agregan a su dependencia; los radicados que el archivo "
            "no asocia a una dependencia homologada aparecen como «sin dependencia». El canal de radicación existe en el sistema desde enero de 2024. "
            "Los estados corresponden a la foto del archivo al corte: una publicación posterior puede actualizar meses ya publicados cuando llegan datos "
            "nuevos; la cifra vigente es siempre la de la última publicación. Ningún dato identifica personas: son conteos y promedios.",
        ),
    ]

    if not c.pronostico:  # los meses anteriores a la serie pronosticada no describen un pronóstico que no muestran
        metodologia = [m for m in metodologia if m[0] != "Pronóstico"]

    observaciones = _observaciones(c)
    recomendaciones = _recomendaciones(c)
    conclusiones = _conclusiones(c)

    glosario = [
        ("A tiempo", "Radicado cerrado que finalizó en la fecha de vencimiento o antes."),
        ("Abierta", "Radicado que al corte seguía sin respuesta; como ya venció, es una extemporánea abierta."),
        (
            "Cerrada",
            "Radicado que ya tiene respuesta; según la fecha en que se cerró es a tiempo o extemporánea cerrada.",
        ),
        (
            "Canal",
            "Medio por el que ingresó la PQRSDF: correo electrónico, web o correspondencia. El sistema lo registra desde enero de 2024.",
        ),
        ("Corte", "Última fecha que cubren los datos de una publicación."),
        ("Dependencia", "Área del Ministerio responsable de responder el radicado, con su nombre vigente."),
        (
            "Días hábiles de gestión",
            "Días hábiles entre la radicación y la finalización, o la foto si el radicado sigue abierto.",
        ),
        ("Días hábiles de retraso", "Días hábiles entre el vencimiento y la finalización de una PQRSDF extemporánea."),
        ("Eje temático", "Asunto en que el sistema clasifica la PQRSDF."),
        (
            "Extemporánea",
            "Radicado que no se respondió en la fecha de vencimiento o antes: cerrado después del plazo (extemporánea cerrada) o sin respuesta al corte (extemporánea abierta).",
        ),
        (
            "Fecha de vencimiento",
            "Plazo legal de respuesta que calcula el sistema de gestión documental a partir de la radicación y del tipo de requerimiento.",
        ),
        ("Foto", "Día al que corresponde el estado de cada radicado en un archivo; nunca es anterior al corte."),
        (
            "Gestionadas en el mes",
            "PQRSDF cuya fecha de vencimiento cae en el mes del informe: las que la entidad debía responder en ese mes.",
        ),
        (
            "Grupo interno de trabajo",
            "Equipo dentro de una dependencia al que se asigna el radicado; sus cifras se agregan a la dependencia.",
        ),
        (
            "Oportunidad de respuesta",
            "Proporción de las PQRSDF gestionadas en el periodo que se respondieron a tiempo.",
        ),
        # sin pronóstico publicado (retirado, D-82) el glosario no lo describe
        *(
            [("Pronóstico", "Valor del índice de oportunidad que el modelo estadístico esperaba para el mes.")]
            if c.pronostico
            else []
        ),
        ("Puntos porcentuales (pp)", "Diferencia aritmética entre dos porcentajes."),
        ("Radicado", "Identificador único que el sistema de gestión documental asigna a cada PQRSDF."),
        (
            "Tasa de extemporaneidad",
            "Proporción de las PQRSDF gestionadas en el periodo que quedaron extemporáneas; complementa la oportunidad.",
        ),
        (
            "Tipo de requerimiento",
            "Clase de solicitud según el sistema: derecho de petición, queja, reclamo, trámite, tutela, entre otros.",
        ),
        (
            "Viceministerio",
            "Área de primer nivel a la que pertenece la dependencia; incluye el Despacho del Ministro y la Secretaría General.",
        ),
    ]
    siglas = [
        ("IES", "Institución de educación superior."),
        ("MEN", "Ministerio de Educación Nacional."),
        ("PQRSDF", "Peticiones, quejas, reclamos, sugerencias, denuncias y felicitaciones."),
        ("pp", "Puntos porcentuales."),
        *(
            [
                (
                    "SARIMA",
                    "Modelo estadístico de series de tiempo (autorregresivo integrado de media móvil, con estacionalidad) usado para el pronóstico.",
                )
            ]
            if c.pronostico
            else []
        ),
        ("SRC", "Subdirección de Relacionamiento con la Ciudadanía."),
    ]
    return Textos(
        resumen,
        hallazgos,
        objetivo_general,
        objetivos_especificos,
        metodologia,
        observaciones,
        recomendaciones,
        conclusiones,
        glosario,
        siglas,
    )


def _promedio_oportunidad(serie: list[tuple[str, Totales]]) -> float | None:
    radicados = sum(t.radicados for _, t in serie)
    a_tiempo = sum(t.a_tiempo for _, t in serie)
    return a_tiempo / radicados if radicados else None


def cambios_por_dependencia(
    c: Calculo, umbral: int = 50
) -> tuple[list[tuple[str, float, Totales, Totales]], list[tuple[str, float, Totales, Totales]]]:
    """Mejoras y retrocesos de oportunidad frente al mes anterior entre dependencias con volumen en ambos meses."""
    anterior = dict(c.por_dependencia_anterior)
    cambios = []
    for k, t in c.por_dependencia:
        a = anterior.get(k)
        if k == "sin dependencia" or not a or t.radicados < umbral or a.radicados < umbral:
            continue
        cambios.append((k, (t.oportunidad or 0) - (a.oportunidad or 0), a, t))
    mejoras = sorted([x for x in cambios if x[1] >= 0.01], key=lambda x: -x[1])
    retrocesos = sorted([x for x in cambios if x[1] <= -0.01], key=lambda x: x[1])
    return mejoras, retrocesos


def _observaciones(c: Calculo) -> list[str]:
    m, ant, acu, acu_ant = c.mes, c.mes_anterior, c.acumulado, c.acumulado_anterior
    mes = mes_y_anio(c.periodo)
    mes_ant = nombre_mes(c.periodo_anterior_str())
    obs: list[str] = []

    # frente al mes inmediatamente anterior, juzgado contra la variación habitual de los doce anteriores (D-82)
    if ant:
        d = (m.oportunidad or 0) - (ant.oportunidad or 0)
        senal = frase_senal(serie_hasta(c.serie_13, c.periodo, lambda t: t.oportunidad), porcentaje, PORCENTAJE)
        obs.append(
            f"Frente a {mes_ant}, la oportunidad {_sube_baja(d)} {puntos_sin_signo(d)} con un volumen {_volumen(m.radicados, ant.radicados)}{senal}: "
            f"las respuestas a tiempo pasaron de {entero(ant.a_tiempo)} a {entero(m.a_tiempo)} y las extemporáneas de {entero(ant.extemporaneas)} a {entero(m.extemporaneas)}."
        )
    # frente a su propio historial de doce meses
    previos = [(p, t) for p, t in c.serie_13 if p != c.periodo]
    promedio = _promedio_oportunidad(previos)
    if promedio is not None:
        d = (m.oportunidad or 0) - promedio
        obs.append(
            f"La oportunidad de {mes} ({porcentaje(m.oportunidad)}) se ubicó {decimal(abs(d) * 100, 2)} pp {'por encima' if d >= 0 else 'por debajo'} del "
            f"promedio de los doce meses anteriores ({porcentaje(promedio)})."
        )
    # tendencia de los últimos tres meses
    if len(c.serie_13) >= 6:
        ultimos, previos3 = c.serie_13[-3:], c.serie_13[-6:-3]
        pu, pp_ = _promedio_oportunidad(ultimos), _promedio_oportunidad(previos3)
        if pu is not None and pp_ is not None:
            d = pu - pp_
            obs.append(
                f"El promedio de oportunidad del último trimestre ({porcentaje(pu)}) {_sube_baja(d, 'mejoró', 'empeoró')} {puntos_sin_signo(d)} frente al de los tres meses "
                f"anteriores ({porcentaje(pp_)}), lo que marca la dirección de la tendencia reciente."
            )
    # acumulado del año frente al anterior
    if acu_ant:
        d = (acu.oportunidad or 0) - (acu_ant.oportunidad or 0)
        obs.append(
            f"En el acumulado del año la oportunidad es de {porcentaje(acu.oportunidad)}, {puntos(d)} frente al mismo tramo del año anterior, con un volumen "
            f"{_volumen(acu.radicados, acu_ant.radicados)} ({entero(acu.radicados)} frente a {entero(acu_ant.radicados)} gestionadas)."
        )
    # dependencias con oportunidad baja y volumen
    deps = [(k, t) for k, t in c.por_dependencia if k != "sin dependencia" and t.radicados >= UMBRAL_DEPENDENCIA]
    bajas = [(k, t) for k, t in deps if (t.oportunidad or 0) < OPORTUNIDAD_BAJA]
    if bajas:
        obs.append(
            f"{numero_en_palabras(len(bajas)).capitalize()} {'dependencia' if len(bajas) == 1 else 'dependencias'} con al menos {UMBRAL_DEPENDENCIA} radicados en el mes "
            f"{'quedó' if len(bajas) == 1 else 'quedaron'} por debajo del {porcentaje(OPORTUNIDAD_BAJA, 0)} de oportunidad: "
            f"{lista_en_prosa([f'{con_articulo(k)} ({porcentaje(t.oportunidad)}, {entero(t.extemporaneas)} extemporáneas)' for k, t in sorted(bajas, key=lambda kt: kt[1].oportunidad or 0)[:5]])}."
        )
    # cambios por dependencia frente al mes anterior
    mejoras, retrocesos = cambios_por_dependencia(c)
    if retrocesos:
        obs.append(
            f"Las dependencias que más retrocedieron frente a {mes_ant} fueron {lista_en_prosa([f'{con_articulo(k)} ({porcentaje(a.oportunidad)} a {porcentaje(t.oportunidad)})' for k, _, a, t in retrocesos[:3]])}."
        )
    if mejoras:
        obs.append(
            f"Las que más mejoraron fueron {lista_en_prosa([f'{con_articulo(k)} ({porcentaje(a.oportunidad)} a {porcentaje(t.oportunidad)})' for k, _, a, t in mejoras[:3]])}."
        )
    # concentración de extemporáneas
    por_ext = sorted(
        [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"], key=lambda kt: -kt[1].extemporaneas
    )[:3]
    if m.extemporaneas and por_ext:
        parte = sum(t.extemporaneas for _, t in por_ext) / m.extemporaneas
        obs.append(
            f"Tres dependencias reúnen el {porcentaje(parte, 1)} de las extemporáneas del mes: "
            f"{lista_en_prosa([f'{con_articulo(k)} ({entero(t.extemporaneas)})' for k, t in por_ext])}."
        )
    # tipo con menor oportunidad
    tipos = sorted(
        [(k, t) for k, t in c.por_tipo if k != "sin homologar" and t.radicados >= UMBRAL_TIPO],
        key=lambda kt: kt[1].oportunidad or 0,
    )
    if tipos and (tipos[0][1].oportunidad or 0) < (m.oportunidad or 0) - 0.05:
        k, t = tipos[0]
        obs.append(
            f"El tipo de requerimiento «{capitalizar(k)}» tuvo la menor oportunidad entre los de volumen relevante: {porcentaje(t.oportunidad)} sobre {entero(t.radicados)} "
            f"gestionadas, {puntos((t.oportunidad or 0) - (m.oportunidad or 0))} frente al total del mes."
        )
    # canal
    if c.por_canal:
        canales = [(k, t) for k, t in c.por_canal if k != "sin informacion" and t.radicados >= UMBRAL_TIPO]
        if len(canales) >= 2:
            peor = min(canales, key=lambda kt: kt[1].oportunidad or 0)
            mejor = max(canales, key=lambda kt: kt[1].oportunidad or 0)
            d = (mejor[1].oportunidad or 0) - (peor[1].oportunidad or 0)
            if d >= 0.02:
                obs.append(
                    f"Por canal, las PQRSDF radicadas por {capitalizar(peor[0]).lower()} alcanzaron {porcentaje(peor[1].oportunidad)} de oportunidad, "
                    f"{decimal(d * 100, 2)} pp menos que las radicadas por {capitalizar(mejor[0]).lower()} ({porcentaje(mejor[1].oportunidad)})."
                )
    # abiertas vencidas al corte
    if m.abiertas_vencidas:
        obs.append(
            f"Al corte del {fecha_larga(c.fecha_corte)}, {entero(m.abiertas_vencidas)} de las extemporáneas de {mes} "
            f"({porcentaje(m.abiertas_vencidas / m.extemporaneas if m.extemporaneas else None, 1)}) seguían abiertas y, mientras no se cierren, "
            "siguen acumulando días de retraso."
        )
    # retraso promedio
    if m.promedio_dias_retraso is not None and acu.promedio_dias_retraso is not None:
        d = m.promedio_dias_retraso - acu.promedio_dias_retraso
        obs.append(
            f"Las extemporáneas del mes se atendieron en promedio {decimal(m.promedio_dias_retraso, 1)} días hábiles después del vencimiento, "
            f"{decimal(abs(d), 1)} días {_mas_menos(d)} que el promedio del año ({decimal(acu.promedio_dias_retraso, 1)})."
        )
    # pronóstico
    if c.pronostico:
        con_real = [(p, r, v) for p, r, v in c.pronostico if r is not None]
        por_debajo = sum(1 for _, r, v in con_real if r < v)
        if con_real:
            n = len(con_real)
            cuantos = (
                f"En todos los {numero_en_palabras(n, False)} meses"
                if por_debajo == n
                else f"En {numero_en_palabras(por_debajo, False)} de los {numero_en_palabras(n, False)} meses"
            )
            obs.append(
                f"{cuantos} del año con dato real la oportunidad quedó por debajo del pronóstico del modelo "
                f"{c.modelo_pronostico.upper()}; la diferencia promedio del año es de {puntos(sum(r - v for _, r, v in con_real) / n)}."
            )
    # sin dependencia
    sin_dep = next((t for k, t in c.por_dependencia if k == "sin dependencia"), None)
    if sin_dep and m.radicados and sin_dep.radicados / m.radicados >= 0.01:
        obs.append(
            f"{entero(sin_dep.radicados)} radicados del mes ({porcentaje(sin_dep.radicados / m.radicados, 1)}) no traen una dependencia homologada en el archivo "
            "y se presentan como «sin dependencia», lo que resta precisión al análisis por área."
        )
    return obs


def _recomendaciones(c: Calculo) -> list[str]:
    m = c.mes
    mes_ant = nombre_mes(c.periodo_anterior_str())
    rec: list[str] = []
    deps = [(k, t) for k, t in c.por_dependencia if k != "sin dependencia" and t.radicados >= UMBRAL_DEPENDENCIA]
    bajas = sorted(
        [(k, t) for k, t in deps if (t.oportunidad or 0) < OPORTUNIDAD_BAJA], key=lambda kt: kt[1].oportunidad or 0
    )
    if bajas:
        rec.append(
            f"Acordar con {lista_en_prosa([con_articulo(k) for k, _ in bajas[:3]])} un plan de mejora con metas mensuales de oportunidad y seguimiento "
            "semanal de los radicados próximos a vencer, dado que concentran la mayor parte de la brecha del mes."
        )
    _, retrocesos = cambios_por_dependencia(c)
    if retrocesos:
        rec.append(
            f"Revisar qué cambió en {lista_en_prosa([con_articulo(k) for k, _, _, _ in retrocesos[:3]])}, que perdieron oportunidad frente a {mes_ant}: "
            "un retroceso en un solo mes suele tener una causa identificable (picos de demanda, vacantes, cambios de procedimiento) que conviene atender antes de que se repita."
        )
    por_ext = sorted(
        [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"], key=lambda kt: -kt[1].extemporaneas
    )[:3]
    if por_ext and m.extemporaneas:
        rec.append(
            f"Revisar con {lista_en_prosa([con_articulo(k) for k, _ in por_ext])} las causas de sus extemporáneas (volumen, complejidad, dependencia de "
            "terceros o asignación tardía) y priorizar las de mayor retraso, porque allí está la mayor parte de las respuestas fuera de plazo."
        )
    if m.abiertas_vencidas:
        rec.append(
            f"Cerrar en el menor tiempo posible las {entero(m.abiertas_vencidas)} extemporáneas del mes que seguían abiertas al corte, y responder a la "
            "ciudadanía sobre su estado: cada día adicional aumenta el retraso promedio y el riesgo de reclamos y tutelas."
        )
    tipos = sorted(
        [(k, t) for k, t in c.por_tipo if k != "sin homologar" and t.radicados >= UMBRAL_TIPO],
        key=lambda kt: kt[1].oportunidad or 0,
    )
    if tipos and (tipos[0][1].oportunidad or 0) < (m.oportunidad or 0) - 0.05:
        rec.append(
            f"Examinar el flujo de respuesta del tipo «{capitalizar(tipos[0][0])}», que presenta la menor oportunidad entre los tipos de mayor volumen, "
            "y definir plantillas, responsables y plazos internos más cortos que el plazo legal."
        )
    if c.por_canal:
        canales = [(k, t) for k, t in c.por_canal if k != "sin informacion" and t.radicados >= UMBRAL_TIPO]
        if len(canales) >= 2:
            peor = min(canales, key=lambda kt: kt[1].oportunidad or 0)
            rec.append(
                f"Fortalecer la radicación y el direccionamiento de las PQRSDF que llegan por {capitalizar(peor[0]).lower()}, el canal con menor oportunidad, "
                "para que lleguen a la dependencia competente el mismo día de su ingreso."
            )
    if c.pronostico:
        rec.append(
            f"Mantener el pronóstico del modelo {c.modelo_pronostico.upper()} como referencia de cada mes y revisar las causas cuando el resultado real quede por "
            "debajo de lo previsto durante dos meses seguidos, ya que señala un cambio de comportamiento y no una variación aleatoria."
        )
    sin_dep = next((t for k, t in c.por_dependencia if k == "sin dependencia"), None)
    if sin_dep and m.radicados and sin_dep.radicados / m.radicados >= 0.01:
        rec.append(
            "Completar la homologación de dependencias en el sistema de gestión documental para que ningún radicado quede «sin dependencia» y el análisis "
            "por área refleje la responsabilidad real."
        )
    rec.append(
        "Divulgar este informe en la entidad con las cifras de cada dependencia y mantener el informe interactivo de la plataforma como herramienta de "
        "seguimiento diario, de modo que la oportunidad se gestione durante el mes y no solo se mida al cierre."
    )
    return rec


def _conclusiones(c: Calculo) -> list[str]:
    m, acu, acu_ant, ant, mismo = c.mes, c.acumulado, c.acumulado_anterior, c.mes_anterior, c.mismo_mes_anterior
    mes = mes_y_anio(c.periodo)
    con: list[str] = []
    partes = []
    if ant:
        d = _dif(m.oportunidad, ant.oportunidad)
        partes.append(f"{_sube_baja(d, 'mejor', 'peor', 'igual')} que el mes inmediatamente anterior ({puntos(d)})")
    if mismo:
        d = _dif(m.oportunidad, mismo.oportunidad)
        partes.append(f"{_sube_baja(d, 'mejor', 'peor', 'igual')} que el mismo mes del año anterior ({puntos(d)})")
    con.append(
        f"En {mes} el Ministerio respondió a tiempo el {porcentaje(m.oportunidad)} de las {entero(m.radicados)} PQRSDF que gestionó, un resultado "
        + (" y ".join(partes) if partes else "")
        + f". Quedaron {entero(m.extemporaneas)} respuestas fuera de plazo."
    )
    if acu_ant:
        d = (acu.oportunidad or 0) - (acu_ant.oportunidad or 0)
        con.append(
            f"En lo corrido de {c.anio} la oportunidad acumulada es de {porcentaje(acu.oportunidad)}, {decimal(abs(d) * 100, 2)} pp "
            f"{'más' if d >= 0 else 'menos'} que en el mismo tramo de {c.anio - 1}, con un volumen {_volumen(acu.radicados, acu_ant.radicados)}. "
            + (
                "La entidad atiende más solicitudes con una menor proporción a tiempo, lo que indica presión sobre la capacidad de respuesta."
                if d < 0 and (variacion_relativa(acu.radicados, acu_ant.radicados) or 0) > 0
                else ""
            )
        )
    deps = [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"]
    por_ext = sorted(deps, key=lambda kt: -kt[1].extemporaneas)[:3]
    if por_ext and m.extemporaneas:
        parte = sum(t.extemporaneas for _, t in por_ext) / m.extemporaneas
        con.append(
            f"La brecha se concentra: {lista_en_prosa([con_articulo(k) for k, _ in por_ext])} reúnen el {porcentaje(parte, 1)} de las extemporáneas del mes, "
            "de modo que las acciones de mejora tienen un foco claro y un número manejable de responsables."
        )
    con.append(
        f"Los tiempos de gestión ({decimal(m.promedio_dias_gestion, 1)} días hábiles en promedio) y de retraso ({decimal(m.promedio_dias_retraso, 1)} días hábiles "
        "en las extemporáneas) muestran que la mayoría de las respuestas se produce dentro del plazo y que el retraso, cuando ocurre, es de días y no de "
        "semanas; el reto está en cerrar lo que queda abierto al vencer."
        if m.promedio_dias_retraso is not None and m.promedio_dias_retraso <= 10
        else f"Los tiempos de gestión ({decimal(m.promedio_dias_gestion, 1)} días hábiles en promedio) y de retraso ({decimal(m.promedio_dias_retraso, 1)} días hábiles "
        "en las extemporáneas) indican que las respuestas fuera de plazo no son marginales: el retraso promedio supera las dos semanas hábiles y exige "
        "intervenir el flujo de las dependencias con mayor volumen extemporáneo."
    )
    if c.pronostico and c.pronostico[-1][0] == c.periodo and c.pronostico[-1][1] is not None:
        _, real, pron = c.pronostico[-1]
        con.append(
            f"Frente al pronóstico del modelo {c.modelo_pronostico.upper()} ({porcentaje(pron)}), el mes cerró {'por encima' if real >= pron else 'por debajo'} de lo "
            f"esperado ({porcentaje(real)}); el seguimiento mensual de esa diferencia permitirá anticipar los meses de mayor riesgo del año."
        )
    return [mayuscula_inicial(x.strip()) for x in con if x.strip()]
