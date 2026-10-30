"""La redacción del Informe de Legalizaciones: párrafos en tercera persona, lenguaje neutro y claro, que salen de las
cifras del mes con reglas explícitas. Resumen ejecutivo, hallazgos de portada, objetivos, metodología, glosario,
observaciones, recomendaciones y conclusiones. Nada se escribe a mano para un mes concreto: todo vale para cualquier
mes, y lo que no existe en un mes (un mes anterior, un año anterior) no se promete. El vocabulario es el del informe
interactivo: documentos radicados para legalizar, legalizadas (nunca «finalizadas»), canceladas, en curso al corte,
tasa de legalización (legalizadas sobre legalizadas más canceladas) y porcentaje de oportunidad (las legalizadas en
hasta el plazo de días hábiles sobre las legalizadas con fecha)."""

from __future__ import annotations

from men_platform.publicaciones.datos_legalizaciones import PARETO, Calculo, Categoria, Medidas
from men_platform.publicaciones.redaccion_pqrsdf import Textos
from men_platform.publicaciones.senales import PORCENTAJE, frase_senal, parametro_numerico, serie_hasta
from men_platform.publicaciones.texto_es import (
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

DESVIO_PROMEDIO = 0.10  # un mes a más del 10 % de su promedio mensual merece observación
SALTO_VOLUMEN = 0.15  # cambio fuerte de las radicadas de un mes al otro, o frente al año anterior
SALTO_ACUMULADO = 0.10
SALTO_OPORTUNIDAD = 0.03  # tres puntos porcentuales del índice
SALTO_TASA = 0.02  # dos puntos de la tasa de legalización
SALTO_DIAS = 0.5  # medio día hábil de gestión
EN_CURSO_ALTO = 0.10  # más del 10 % del mes seguía en curso al corte


def en_curso_en_texto(n: int, al_corte: bool = False, participacion: float | None = None) -> str:
    """«ninguno seguía en curso», «1 seguía en curso» o «1.884 seguían en curso»; con al_corte, «ninguno en curso al
    corte» y «N en curso al corte»; con participación, la cifra lleva su porcentaje entre paréntesis."""
    if not n:
        return "ninguno en curso al corte" if al_corte else "ninguno seguía en curso"
    cifra = entero(n)
    if participacion is not None:
        cifra += f" ({porcentaje(participacion, 1)})"
    if al_corte:
        return f"{cifra} en curso al corte"
    verbo = "seguía" if n == 1 else "seguían"
    return f"{cifra} {verbo} en curso"


def etapas_en_texto(complementacion: float, validacion: float, mes: str) -> str:
    """Las dos etapas con su porcentaje; cuando una no se dio en el mes (o redondea a cero), se dice sin la cifra."""
    ies = "validación con la institución de educación superior"

    def cuantos(valor: float) -> str | None:
        if not valor:
            return "ningún documento"
        if valor < 0.0005:
            return "menos del 0,1 % de los documentos"
        return None

    c, v = cuantos(complementacion), cuantos(validacion)
    if c and v:
        return f"En {mes}, {c} pasó por complementación y {v} por {ies}, las dos etapas que alargan el trámite."
    if c:
        return f"En {mes}, {c} pasó por complementación; el {porcentaje(validacion, 1)} pasó por {ies}, una etapa que alarga el trámite."
    if v:
        return (
            f"El {porcentaje(complementacion, 1)} de los documentos radicados en {mes} pasó por complementación, una etapa "
            f"que alarga el trámite; {v} pasó por {ies}."
        )
    return (
        f"El {porcentaje(complementacion, 1)} de los documentos radicados en {mes} pasó por complementación y el "
        f"{porcentaje(validacion, 1)} por {ies}; las dos etapas alargan el trámite."
    )


CONCENTRACION = 0.5  # la metodología principal concentra más de la mitad
UMBRAL_CATEGORIA = 100  # legalizadas con fecha mínimas para juzgar la oportunidad de una categoría
OPORTUNIDAD_BAJA = 0.70  # valor interno; lo reemplaza ref.parametro oportunidad_referencia_legalizaciones (D-82, P-36)
ETAPA_ALTA = 0.20  # más del 20 % de los documentos pasó por una etapa


def plazo_en_texto(c: Calculo) -> str:
    return f"{c.plazo} {'día hábil' if c.plazo == 1 else 'días hábiles'}"


def _pp(a: float | None, b: float | None) -> str:
    return puntos(a - b) if a is not None and b is not None else "–"


def _lado(valor: float, referencia: float) -> str:
    return "por encima" if valor >= referencia else "por debajo"


def resumen(c: Calculo) -> list[str]:
    m = c.mes
    ant = c.mes_anterior
    mismo = c.mismo_mes_anterior
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    parrafos: list[str] = []

    # 1. las radicadas del mes, su resultado y la tasa
    frase = f"En {mes} se radicaron {entero(m.radicadas)} documentos para legalizar ante el Ministerio de Educación Nacional"
    comparaciones = []
    if ant is not None and c.periodo_anterior:
        comparaciones.append(
            f"{variacion(m.radicadas, ant.radicadas)} frente a {nombre_mes(c.periodo_anterior)} ({entero(ant.radicadas)})"
        )
    if mismo is not None:
        comparaciones.append(
            f"{variacion(m.radicadas, mismo.radicadas)} frente a {nombre_mes(c.periodo)} de {anio_ant} ({entero(mismo.radicadas)})"
        )
    if comparaciones:
        frase += ": " + " y ".join(comparaciones)
    frase += (
        f". Al corte, {entero(m.legalizadas)} de ellos ya estaban legalizados, {entero(m.canceladas)} se cancelaron y "
        f"{en_curso_en_texto(m.en_curso)}; la tasa de legalización, las legalizadas sobre las legalizadas más las canceladas, "
        f"fue de {porcentaje(m.tasa_legalizacion)}"
    )
    promedio = c.promedio_mensual
    if promedio and c.meses_acumulado >= 2:
        frase += (
            f". El mes quedó {_lado(m.radicadas, promedio)} del promedio mensual de {anio} ({decimal(promedio, 1)} radicadas), "
            f"{variacion(m.radicadas, promedio)}"
        )
    parrafos.append(frase + ".")

    # 2. la oportunidad y los días de gestión
    frase = (
        f"El porcentaje de oportunidad fue de {porcentaje(m.oportunidad)}: {entero(m.a_tiempo)} de las {entero(m.legalizadas_con_fecha)} "
        f"legalizadas con fecha se gestionaron en hasta {plazo_en_texto(c)}"
    )
    partes = []
    if ant is not None and ant.oportunidad is not None and c.periodo_anterior:
        partes.append(
            f"{_pp(m.oportunidad, ant.oportunidad)} frente a {nombre_mes(c.periodo_anterior)} ({porcentaje(ant.oportunidad)})"
        )
    if mismo is not None and mismo.oportunidad is not None:
        partes.append(
            f"{_pp(m.oportunidad, mismo.oportunidad)} frente a {nombre_mes(c.periodo)} de {anio_ant} ({porcentaje(mismo.oportunidad)})"
        )
    if partes:
        frase += ", " + " y ".join(partes)
    if m.promedio_dias_habiles_legalizadas is not None:
        frase += (
            f". La gestión de las legalizadas tomó en promedio {decimal(m.promedio_dias_habiles_legalizadas, 1)} días hábiles "
            f"({decimal(m.promedio_dias_legalizadas, 1)} días calendario)"
        )
        if ant is not None and ant.promedio_dias_habiles_legalizadas is not None and c.periodo_anterior:
            frase += (
                f", frente a {decimal(ant.promedio_dias_habiles_legalizadas, 1)} en {nombre_mes(c.periodo_anterior)}"
            )
    parrafos.append(frase + ".")

    # 3. el reparto por metodología y por tipo de documento
    mets = c.metodologias_mes
    if mets:
        cat, mp = mets[0]
        frase = (
            f"Por metodología, {cat.bajo} concentró {entero(mp.radicadas)} radicadas ({porcentaje(c.participacion(mp), 1)} del mes), con una "
            f"tasa de legalización de {porcentaje(mp.tasa_legalizacion)} y {porcentaje(mp.oportunidad)} de oportunidad"
        )
        if len(mets) > 1:
            otras = [f"{k.bajo} ({entero(v.radicadas)}, {porcentaje(c.participacion(v), 1)})" for k, v in mets[1:4]]
            frase += f"; {'le siguió' if len(otras) == 1 else 'le siguieron'} {lista_en_prosa(otras)}"
        if len(mets) > 2:
            n = c.cuantas_para_pareto(mets)
            frase += (
                f". {mayuscula_inicial(numero_en_palabras(n))} {'metodología explica' if n == 1 else 'metodologías explican'} el "
                f"{porcentaje(PARETO, 0)} de las radicadas del mes"
            )
        docs = c.documentos_mes
        if docs:
            d0, v0 = docs[0]
            frase += f". Por tipo de documento, {d0.bajo} fue el más radicado ({entero(v0.radicadas)}, {porcentaje(c.participacion(v0), 1)})"
            if len(docs) > 1:
                siguientes = [
                    f"{k.bajo} ({entero(v.radicadas)}, {porcentaje(c.participacion(v), 1)})" for k, v in docs[1:3]
                ]
                frase += f", seguido de {lista_en_prosa(siguientes)}"
        parrafos.append(frase + ".")

    # 4. el año, cuando hay más de un mes
    if c.meses_acumulado >= 2:
        a = c.acumulado
        frase = f"{entre_tramo(c.periodo)} de {anio} se radicaron {entero(a.radicadas)} documentos"
        if c.acumulado_anterior is not None:
            frase += (
                f", {variacion(a.radicadas, c.acumulado_anterior.radicadas)} frente a los mismos meses de {anio_ant} "
                f"({entero(c.acumulado_anterior.radicadas)})"
            )
        mayor, menor = c.mes_mayor, c.mes_menor
        if mayor and menor and mayor[0] != menor[0]:
            frase += f"; el mes más alto fue {nombre_mes(mayor[0])} ({entero(mayor[1])}) y el más bajo {nombre_mes(menor[0])} ({entero(menor[1])})"
        frase += (
            f". En lo corrido del año la tasa de legalización es de {porcentaje(a.tasa_legalizacion)} y el porcentaje de oportunidad, "
            f"de {porcentaje(a.oportunidad)}"
        )
        if c.acumulado_anterior is not None and c.acumulado_anterior.oportunidad is not None:
            frase += f" ({_pp(a.oportunidad, c.acumulado_anterior.oportunidad)} frente al mismo tramo de {anio_ant})"
        parrafos.append(frase + ".")

    # 5. las etapas del trámite
    if m.tasa_complementacion is not None and m.tasa_validacion_ies is not None:
        parrafos.append(etapas_en_texto(m.tasa_complementacion, m.tasa_validacion_ies, nombre_mes(c.periodo)))
    return parrafos


def hallazgos(c: Calculo) -> list[str]:
    """Las cinco líneas de «En síntesis» de la portada, cortas para que quepan en una línea."""
    m = c.mes
    linea = f"{entero(m.radicadas)} documentos radicados para legalizar"
    if c.mes_anterior is not None and c.periodo_anterior:
        linea += f" ({variacion(m.radicadas, c.mes_anterior.radicadas)} frente a {nombre_mes(c.periodo_anterior)})"
    lineas = [linea]
    lineas.append(
        f"{porcentaje(m.oportunidad)} de oportunidad: {entero(m.a_tiempo)} legalizadas en hasta {plazo_en_texto(c)}"
    )
    lineas.append(
        f"Tasa de legalización de {porcentaje(m.tasa_legalizacion)}; {en_curso_en_texto(m.en_curso, al_corte=True)}"
    )
    if m.promedio_dias_habiles_legalizadas is not None:
        lineas.append(
            f"{decimal(m.promedio_dias_habiles_legalizadas, 1)} días hábiles de gestión en promedio "
            f"({decimal(m.promedio_dias_legalizadas, 1)} calendario)"
        )
    if c.metodologias_mes:
        cat, mp = c.metodologias_mes[0]
        lineas.append(
            f"{cat.nombre}: {entero(mp.radicadas)} radicadas, el {porcentaje(c.participacion(mp), 1)} del mes"
        )
    return lineas[:5]


def objetivos(c: Calculo) -> tuple[str, list[str]]:
    mes = mes_y_anio(c.periodo)
    anio_ant = c.anio - 1
    general = (
        f"Presentar las legalizaciones de documentos de educación superior radicadas ante el Ministerio de Educación Nacional en {mes}: "
        "cuántos documentos se radicaron, cuántos terminaron legalizados y en cuántos días, qué porcentaje se gestionó dentro del plazo "
        f"de {plazo_en_texto(c)} y cómo se reparten por metodología y por tipo de documento, comparadas con el mes anterior y con el año "
        "anterior, para que la entidad conozca el desempeño del trámite y tome decisiones sobre su operación."
    )
    partes = []
    if c.mes_anterior is not None and c.periodo_anterior:
        partes.append(f"con {nombre_mes(c.periodo_anterior)}, el mes inmediatamente anterior")
    if c.mismo_mes_anterior is not None:
        partes.append(f"con {nombre_mes(c.periodo)} de {anio_ant}")
    especificos = [
        f"Cuantificar los documentos radicados para legalizar en {mes}, su resultado al corte (legalizados, cancelados y en curso) y la "
        "tasa de legalización" + (f", y compararlos {lista_en_prosa(partes)}" if partes else "") + ".",
        f"Medir el porcentaje de oportunidad de las legalizaciones (las gestionadas en hasta {plazo_en_texto(c)} sobre las legalizadas con "
        "fecha) mes a mes, frente al año anterior, frente al mes anterior y frente a su media móvil, y la distribución de las legalizadas "
        "por días hábiles de gestión.",
        "Describir los tiempos de respuesta: los días calendario y hábiles entre la radicación y el resultado, su distribución por rangos "
        "y las etapas de complementación y validación con la institución de educación superior.",
        "Identificar las metodologías y los tipos de documento de mayor volumen, con su participación, su resultado y su oportunidad, y "
        "proponer acciones a la entidad.",
    ]
    return general, especificos


def metodologia(c: Calculo) -> list[tuple[str, str]]:
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    tramo = tramo_del_anio(c.periodo)
    comparaciones = "El informe es mensual"
    if c.mes_anterior is not None and c.periodo_anterior:
        comparaciones += (
            f": el mes se compara en primer lugar con el mes inmediatamente anterior ({nombre_mes(c.periodo_anterior)})"
        )
    if c.mismo_mes_anterior is not None or c.acumulado_anterior is not None:
        comparaciones += f"; después, con el mismo mes de {anio_ant}"
        if c.meses_acumulado >= 2 and c.acumulado_anterior is not None:
            comparaciones += f" y con el acumulado de {tramo} de {anio} frente a los mismos meses de {anio_ant}"
    comparaciones += (
        ". Las cifras de volumen se comparan en porcentaje; los índices (la tasa de legalización y el porcentaje de oportunidad), en "
        "puntos porcentuales. La media móvil de las radicadas es simple: el promedio de los tres meses inmediatamente anteriores, sin el "
        "mes evaluado; la de la oportunidad es ponderada: las legalizadas a tiempo de esos tres meses sobre sus legalizadas con fecha."
    )
    return [
        (
            "Fuentes",
            "El sistema de legalización de documentos de educación superior del Ministerio: una fila por documento radicado para legalizar "
            "(diplomas, actas de grado, certificados y otros), con su estado y sus fechas de proceso, que la plataforma lee completa en "
            "cada publicación y agrega por mes de radicación, metodología, tipo de documento y resultado. Este informe lee los mismos "
            f"agregados que alimentan el informe interactivo, con corte al {fecha_larga(c.fecha_corte)}. El número de documento del "
            "ciudadano y el radicado nunca salen de la fuente.",
        ),
        (
            "Unidad de medida",
            "El documento radicado para legalizar, contado una sola vez en el mes de su fecha de radicación. Una misma solicitud puede "
            "traer varios documentos; el informe cuenta documentos.",
        ),
        (
            "Resultado",
            "Sale solo del estado que registra el sistema al corte: legalizado (el documento terminó legalizado), cancelado y en curso "
            "(radicado, en trámite, en complementación, en validación con la institución de educación superior o en revisión). La tasa "
            "de legalización es las legalizadas sobre las legalizadas más las canceladas: lo en curso no cuenta, así que en los meses "
            "recientes sube a medida que los trámites terminan.",
        ),
        (
            "Oportunidad",
            "Se mide solo sobre lo efectivamente legalizado: una legalización es a tiempo si su gestión, los días hábiles entre la "
            f"radicación y la legalización contados con el calendario oficial, tomó hasta {plazo_en_texto(c)}, la regla oficial del área; "
            "pasado ese plazo es extemporánea. El porcentaje de oportunidad es las a tiempo sobre las legalizadas con fecha de resultado.",
        ),
        (
            "Tiempos",
            "Los días van de la radicación a la fecha del resultado (la de legalización o, si el sistema no la registró, la última fecha "
            "de proceso), en días calendario y en días hábiles, sobre los documentos que ya tienen resultado. Las etapas de complementación "
            "y de validación con la institución de educación superior son los documentos que registran esa fecha.",
        ),
        ("Comparaciones", comparaciones),
        (
            "Procesamiento",
            f"Los agregados se publican en la plataforma con cada actualización de datos; este informe de {mes} se generó de forma "
            "automática a partir de ellos: las cifras, los gráficos y los textos salen de reglas fijas, iguales para todos los meses, y no se "
            "corrigen a mano; las inconsistencias de la fuente se publican tal como llegan.",
        ),
    ]


def glosario(c: Calculo) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    plazo = plazo_en_texto(c)
    terminos = [
        ("A tiempo", f"Legalizada cuya gestión, de la radicación a la legalización, tomó hasta {plazo}."),
        ("Acumulado del año", "La suma de los documentos radicados de enero al mes del informe."),
        (
            "Cancelada",
            "Documento radicado cuyo trámite se canceló; cuenta en el denominador de la tasa de legalización.",
        ),
        (
            "Complementación",
            "Etapa en la que el ciudadano debe completar o corregir algo de la solicitud; el informe cuenta los documentos que pasaron por ella.",
        ),
        (
            "Días hábiles de gestión",
            "Los días hábiles entre la radicación del documento y su legalización, contados con el calendario oficial; el plazo de oportunidad se mide con ellos.",
        ),
        (
            "Documento radicado",
            "Cada documento de educación superior radicado para legalizar; es la unidad de medida del informe.",
        ),
        (
            "En curso",
            "Documento que al corte seguía en trámite (radicado, en trámite, en complementación, en validación con la IES o en revisión).",
        ),
        ("Extemporánea", f"Legalizada cuya gestión tomó más de {plazo}."),
        ("Legalizada", "Documento cuyo trámite terminó legalizado, según el estado que registra el sistema."),
        (
            "Legalización",
            "El trámite por el cual el Ministerio certifica la autenticidad de un documento de educación superior expedido en Colombia para que surta efecto en el exterior.",
        ),
        (
            "Media móvil",
            "Referencia de los tres meses inmediatamente anteriores, sin el mes evaluado: simple (el promedio) para las radicadas y ponderada (las a tiempo sobre las legalizadas con fecha) para la oportunidad.",
        ),
        (
            "Metodología",
            "El nivel académico o tipo de trámite con que el sistema clasifica cada documento: pregrado, maestría, especialización, tecnólogo, técnico profesional, certificación, doctorado, documento MEN, resolución, distinción y normalista.",
        ),
        (
            "Pareto",
            "Las categorías de mayor a menor volumen con su participación acumulada; la guía del 80 % señala cuántas explican la mayor parte.",
        ),
        (
            "Participación",
            "La parte de una metodología o de un tipo de documento en los documentos radicados del mes o del año, en porcentaje.",
        ),
        (
            "Plazo de oportunidad",
            f"{mayuscula_inicial(plazo)} de gestión, la regla oficial del área; vive en los parámetros de la plataforma.",
        ),
        (
            "Porcentaje de oportunidad",
            "Las legalizadas a tiempo sobre las legalizadas con fecha de resultado; se mide solo sobre lo efectivamente legalizado.",
        ),
        ("Promedio mensual", "Los documentos radicados del año divididos por sus meses con datos."),
        ("Tasa de legalización", "Las legalizadas sobre las legalizadas más las canceladas; lo en curso no cuenta."),
        (
            "Tipo de documento",
            "La clase de documento radicado: diploma de grado, acta de grado, certificado de calificaciones y otros.",
        ),
        (
            "Validación con la IES",
            "Etapa en la que el Ministerio verifica el documento con la institución de educación superior que lo expidió; el informe cuenta los documentos que pasaron por ella.",
        ),
        (
            "Variación",
            "Cambio de una cifra frente a otra: en porcentaje para los volúmenes y en puntos porcentuales para los índices.",
        ),
    ]
    terminos.sort(key=lambda par: par[0].lower())
    siglas = [
        ("IES", "Institución de educación superior."),
        ("MEN", "Ministerio de Educación Nacional."),
        ("pp", "Puntos porcentuales: la diferencia entre dos porcentajes."),
        ("SRC", "Subdirección de Relacionamiento con la Ciudadanía, que publica este informe."),
    ]
    return terminos, siglas


def _con_fecha(grupos: list[tuple[Categoria, Medidas]]) -> list[tuple[Categoria, Medidas]]:
    return [(k, v) for k, v in grupos if v.legalizadas_con_fecha >= UMBRAL_CATEGORIA]


def observaciones(c: Calculo) -> list[str]:
    m = c.mes
    ant = c.mes_anterior
    mismo = c.mismo_mes_anterior
    mes = nombre_mes(c.periodo)
    anio = c.anio
    lineas: list[str] = []
    promedio = c.promedio_mensual
    if promedio and c.meses_acumulado >= 2:
        desvio = m.radicadas / promedio - 1
        if abs(desvio) >= DESVIO_PROMEDIO:
            lineas.append(
                f"Las radicadas de {mes} ({entero(m.radicadas)}) quedaron {porcentaje(abs(desvio), 1)} {'por encima' if desvio > 0 else 'por debajo'} "
                f"del promedio mensual de {anio} ({decimal(promedio, 1)})."
            )
        else:
            lineas.append(
                f"Las radicadas de {mes} ({entero(m.radicadas)}) se mantuvieron cerca del promedio mensual de {anio} ({decimal(promedio, 1)}): "
                f"{variacion(m.radicadas, promedio)}."
            )
    if ant is not None and c.periodo_anterior:
        v = variacion_relativa(m.radicadas, ant.radicadas)
        if v is not None and abs(v) >= SALTO_VOLUMEN:
            lineas.append(
                f"Las radicadas {'crecieron' if v > 0 else 'cayeron'} {porcentaje(abs(v), 1)} frente a {nombre_mes(c.periodo_anterior)}: "
                f"de {entero(ant.radicadas)} a {entero(m.radicadas)} documentos."
            )
    if mismo is not None:
        v = variacion_relativa(m.radicadas, mismo.radicadas)
        if v is not None and abs(v) >= SALTO_VOLUMEN:
            lineas.append(
                f"El volumen del mes está {porcentaje(abs(v), 1)} {'por encima' if v > 0 else 'por debajo'} del de {mes} de {anio - 1} "
                f"({entero(mismo.radicadas)})."
            )
    if m.oportunidad is not None:
        if (
            ant is not None
            and ant.oportunidad is not None
            and c.periodo_anterior
            and abs(m.oportunidad - ant.oportunidad) >= SALTO_OPORTUNIDAD
        ):
            lineas.append(
                f"El porcentaje de oportunidad {'subió' if m.oportunidad > ant.oportunidad else 'bajó'} {puntos(m.oportunidad - ant.oportunidad)} "
                f"frente a {nombre_mes(c.periodo_anterior)}: de {porcentaje(ant.oportunidad)} a {porcentaje(m.oportunidad)}{_senal_oportunidad(c)}."
            )
        if (
            mismo is not None
            and mismo.oportunidad is not None
            and abs(m.oportunidad - mismo.oportunidad) >= SALTO_OPORTUNIDAD
        ):
            lineas.append(
                f"Frente a {mes} de {anio - 1}, la oportunidad {'mejoró' if m.oportunidad > mismo.oportunidad else 'retrocedió'} "
                f"{puntos(m.oportunidad - mismo.oportunidad)} ({porcentaje(mismo.oportunidad)} entonces)."
            )
        if m.oportunidad < OPORTUNIDAD_BAJA:
            lineas.append(
                f"{entero(m.extemporaneas)} legalizadas ({porcentaje(1 - m.oportunidad, 1)}) tardaron más de {plazo_en_texto(c)}: la oportunidad del "
                f"mes ({porcentaje(m.oportunidad)}) queda por debajo del {porcentaje(OPORTUNIDAD_BAJA, 0)}."
            )
    serie = [(p, x) for p, x in c.serie_anio if x.oportunidad is not None]
    if len(serie) >= 3:
        mejor = max(serie, key=lambda px: px[1].oportunidad or 0)
        peor = min(serie, key=lambda px: px[1].oportunidad or 0)
        if mejor[0] != peor[0]:
            lineas.append(
                f"En {anio} la mejor oportunidad fue la de {nombre_mes(mejor[0])} ({porcentaje(mejor[1].oportunidad)}) y la peor la de "
                f"{nombre_mes(peor[0])} ({porcentaje(peor[1].oportunidad)}): {puntos(mejor[1].oportunidad - peor[1].oportunidad)} de diferencia."
            )
    if ant is not None and m.tasa_legalizacion is not None and ant.tasa_legalizacion is not None and c.periodo_anterior:
        if abs(m.tasa_legalizacion - ant.tasa_legalizacion) >= SALTO_TASA:
            lineas.append(
                f"La tasa de legalización {'subió' if m.tasa_legalizacion > ant.tasa_legalizacion else 'bajó'} "
                f"{puntos(m.tasa_legalizacion - ant.tasa_legalizacion)} frente a {nombre_mes(c.periodo_anterior)} "
                f"({porcentaje(ant.tasa_legalizacion)} a {porcentaje(m.tasa_legalizacion)})."
            )
    if (m.participacion_en_curso or 0) >= EN_CURSO_ALTO:
        lineas.append(
            f"{entero(m.en_curso)} documentos de {mes} ({porcentaje(m.participacion_en_curso, 1)}) seguían en curso al corte: la tasa de "
            "legalización del mes subirá a medida que terminen."
        )
    dh, dh_ant = m.promedio_dias_habiles_legalizadas, ant.promedio_dias_habiles_legalizadas if ant is not None else None
    if dh is not None and dh_ant is not None and abs(dh - dh_ant) >= SALTO_DIAS and c.periodo_anterior:
        lineas.append(
            f"La gestión de las legalizadas tomó {decimal(dh, 1)} días hábiles en promedio, "
            f"{decimal(abs(dh - dh_ant), 1)} {'más' if dh > dh_ant else 'menos'} que en {nombre_mes(c.periodo_anterior)} ({decimal(dh_ant, 1)})."
        )
    mets = c.metodologias_mes
    if mets:
        cat, mp = mets[0]
        if (c.participacion(mp) or 0) >= CONCENTRACION:
            lineas.append(
                f"{mayuscula_inicial(cat.bajo)} concentró el {porcentaje(c.participacion(mp), 1)} de las radicadas del mes ({entero(mp.radicadas)}): "
                "lo que pase con esa metodología mueve el total."
            )
        con_fecha = _con_fecha(mets)
        if len(con_fecha) >= 2:
            peor = min(con_fecha, key=lambda kv: kv[1].oportunidad or 0)
            mejor = max(con_fecha, key=lambda kv: kv[1].oportunidad or 0)
            if peor[0].id != mejor[0].id:
                lineas.append(
                    f"Entre las metodologías con al menos {UMBRAL_CATEGORIA} legalizadas, la oportunidad más baja fue la de {peor[0].bajo} "
                    f"({porcentaje(peor[1].oportunidad)}, {entero(peor[1].legalizadas_con_fecha)} legalizadas) y la más alta la de {mejor[0].bajo} "
                    f"({porcentaje(mejor[1].oportunidad)})."
                )
    docs = _con_fecha(c.documentos_mes)
    if len(docs) >= 2:
        peor = min(docs, key=lambda kv: kv[1].oportunidad or 0)
        lineas.append(
            f"Entre los tipos de documento con al menos {UMBRAL_CATEGORIA} legalizadas, {peor[0].bajo} tuvo la oportunidad más baja "
            f"({porcentaje(peor[1].oportunidad)}) y {decimal(peor[1].promedio_dias_habiles_legalizadas, 1)} días hábiles de gestión en promedio."
        )
    if (m.tasa_complementacion or 0) >= ETAPA_ALTA or (m.tasa_validacion_ies or 0) >= ETAPA_ALTA:
        lineas.append(
            f"El {porcentaje(m.tasa_complementacion, 1)} de los documentos del mes pasó por complementación y el {porcentaje(m.tasa_validacion_ies, 1)} "
            "por validación con la IES: las dos etapas alargan la gestión y pesan en lo que queda en curso."
        )
    if c.acumulado_anterior is not None and c.meses_acumulado >= 2:
        v = variacion_relativa(c.acumulado.radicadas, c.acumulado_anterior.radicadas)
        if v is not None and abs(v) >= SALTO_ACUMULADO:
            lineas.append(
                f"El acumulado de {tramo_del_anio(c.periodo)} de {anio} ({entero(c.acumulado.radicadas)}) está {porcentaje(abs(v), 1)} "
                f"{'por encima' if v > 0 else 'por debajo'} del mismo tramo de {anio - 1} ({entero(c.acumulado_anterior.radicadas)})."
            )
    return lineas[:10]


def recomendaciones(c: Calculo) -> list[str]:
    m = c.mes
    ant = c.mes_anterior
    lineas: list[str] = []
    if m.oportunidad is not None and m.oportunidad < OPORTUNIDAD_BAJA:
        lineas.append(
            f"Revisar las {entero(m.extemporaneas)} legalizaciones que pasaron del plazo de {plazo_en_texto(c)} para separar las que esperaron "
            "al ciudadano o a la institución de las que se demoraron en la gestión interna, y actuar sobre estas últimas."
        )
    if (
        ant is not None
        and ant.oportunidad is not None
        and m.oportunidad is not None
        and m.oportunidad - ant.oportunidad <= -SALTO_OPORTUNIDAD
    ):
        lineas.append(
            f"Explicar la caída de la oportunidad frente a {nombre_mes(c.periodo_anterior or c.periodo)} ({puntos(m.oportunidad - ant.oportunidad)}) "
            "con las áreas que gestionan la legalización, antes de que la tendencia se consolide."
        )
    mets = _con_fecha(c.metodologias_mes)
    bajas = sorted(
        [(k, v) for k, v in mets if (v.oportunidad or 0) < OPORTUNIDAD_BAJA], key=lambda kv: kv[1].oportunidad or 0
    )
    if bajas:
        lineas.append(
            f"Dar prioridad a {lista_en_prosa([f'{k.bajo} ({porcentaje(v.oportunidad)})' for k, v in bajas[:3]])}, "
            f"{'la metodología' if len(bajas) == 1 else 'las metodologías'} con la oportunidad más baja del mes, con una ruta de gestión propia."
        )
    if (m.participacion_en_curso or 0) >= EN_CURSO_ALTO:
        lineas.append(
            f"Hacer seguimiento a los {entero(m.en_curso)} documentos que seguían en curso al corte, en especial a los que esperan validación "
            "con la institución de educación superior, para cerrarlos antes del próximo informe."
        )
    if (m.tasa_complementacion or 0) >= ETAPA_ALTA:
        lineas.append(
            f"Reducir la complementación, por la que pasó el {porcentaje(m.tasa_complementacion, 1)} de los documentos del mes: mejorar las "
            "instrucciones y la validación de la solicitud al radicar evita devoluciones al ciudadano."
        )
    if ant is not None and c.periodo_anterior:
        v = variacion_relativa(m.radicadas, ant.radicadas)
        if v is not None and v >= SALTO_VOLUMEN:
            lineas.append(
                f"Prever la capacidad de atención para los meses siguientes: las radicadas crecieron {porcentaje(v, 1)} frente a "
                f"{nombre_mes(c.periodo_anterior)} y, si se sostiene, la carga del equipo cambia."
            )
    serie = [(p, x) for p, x in c.serie_anio if x.oportunidad is not None]
    if len(serie) >= 3 and m.oportunidad is not None:
        mejor = max(serie, key=lambda px: px[1].oportunidad or 0)
        if mejor[0] != c.periodo and mejor[1].oportunidad - m.oportunidad >= 0.05:
            lineas.append(
                f"Replicar la gestión de {nombre_mes(mejor[0])}, el mes de mejor oportunidad de {c.anio} ({porcentaje(mejor[1].oportunidad)}): el "
                f"índice de {nombre_mes(c.periodo)} queda {puntos_sin_signo(mejor[1].oportunidad - m.oportunidad)} por debajo."
            )
    if (
        c.acumulado_anterior is not None
        and c.acumulado.oportunidad is not None
        and c.acumulado_anterior.oportunidad is not None
    ):
        brecha = c.acumulado.oportunidad - c.acumulado_anterior.oportunidad
        if brecha <= -0.05:
            lineas.append(
                f"Fijar una meta de oportunidad para el cierre de {c.anio}: el acumulado del año ({porcentaje(c.acumulado.oportunidad)}) va "
                f"{puntos(brecha)} frente al mismo tramo de {c.anio - 1} ({porcentaje(c.acumulado_anterior.oportunidad)})."
            )
    if (m.tasa_validacion_ies or 0) >= 0.10:
        lineas.append(
            f"Acordar con las instituciones de educación superior tiempos de respuesta para la validación, por la que pasó el "
            f"{porcentaje(m.tasa_validacion_ies, 1)} de los documentos del mes: es la etapa que más alarga la gestión y la que deja documentos en curso."
        )
    lineas.append(
        "Mantener el seguimiento mensual de la legalización con este informe y el interactivo, con el plazo de oportunidad como parámetro "
        "único de la plataforma, para que lo medido sea lo mismo mes a mes."
    )
    lineas.append(
        "Registrar en el sistema la fecha de legalización de todos los documentos legalizados, para que los días de gestión y la oportunidad "
        "se midan siempre con la misma fecha y no con la última etapa registrada."
    )
    return lineas[:7]


def conclusiones(c: Calculo) -> list[str]:
    m = c.mes
    ant = c.mes_anterior
    mismo = c.mismo_mes_anterior
    mes = mes_y_anio(c.periodo)
    anio = c.anio
    p1 = f"En {mes} se radicaron {entero(m.radicadas)} documentos para legalizar"
    if ant is not None and c.periodo_anterior:
        p1 += f", {variacion(m.radicadas, ant.radicadas)} frente a {nombre_mes(c.periodo_anterior)}"
    if mismo is not None:
        p1 += f" y {variacion(m.radicadas, mismo.radicadas)} frente a {nombre_mes(c.periodo)} de {anio - 1}"
    p1 += (
        f"; al corte {entero(m.legalizadas)} estaban legalizados ({porcentaje(m.tasa_legalizacion)} de tasa de legalización), "
        f"{entero(m.canceladas)} cancelados y {entero(m.en_curso)} en curso."
    )
    p2 = f"El porcentaje de oportunidad fue de {porcentaje(m.oportunidad)}"
    if ant is not None and ant.oportunidad is not None and c.periodo_anterior:
        p2 += (
            f", {_pp(m.oportunidad, ant.oportunidad)} frente a {nombre_mes(c.periodo_anterior)}{_senal_oportunidad(c)}"
        )
    if mismo is not None and mismo.oportunidad is not None:
        p2 += f" y {_pp(m.oportunidad, mismo.oportunidad)} frente a {nombre_mes(c.periodo)} de {anio - 1}"
    if m.promedio_dias_habiles_legalizadas is not None:
        p2 += f"; la gestión de las legalizadas tomó {decimal(m.promedio_dias_habiles_legalizadas, 1)} días hábiles en promedio"
    mets = _con_fecha(c.metodologias_mes)
    if len(mets) >= 2:
        mejor = max(mets, key=lambda kv: kv[1].oportunidad or 0)
        peor = min(mets, key=lambda kv: kv[1].oportunidad or 0)
        if mejor[0].id != peor[0].id:
            p2 += (
                f". Por metodología, la oportunidad más alta fue la de {mejor[0].bajo} ({porcentaje(mejor[1].oportunidad)}) y la más baja la de "
                f"{peor[0].bajo} ({porcentaje(peor[1].oportunidad)})"
            )
    p2 += "."
    p3 = ""
    if c.meses_acumulado >= 2:
        a = c.acumulado
        p3 = f"{entre_tramo(c.periodo)} de {anio} se radicaron {entero(a.radicadas)} documentos"
        if c.acumulado_anterior is not None:
            p3 += f", {variacion(a.radicadas, c.acumulado_anterior.radicadas)} frente al mismo tramo de {anio - 1}"
        p3 += f", con una tasa de legalización de {porcentaje(a.tasa_legalizacion)} y {porcentaje(a.oportunidad)} de oportunidad. "
    p3 += "El informe interactivo de la plataforma permite seguir mes a mes cada metodología y cada tipo de documento con las mismas cifras de este documento."
    return [p1, p2, p3]


def _aplicar_parametros(parametros: dict[str, str] | None) -> None:
    """Los umbrales de la redacción salen de ref.parametro cuando la exportación los trae (D-82, fichas FM-45 y FM-47)."""
    global OPORTUNIDAD_BAJA, EN_CURSO_ALTO, ETAPA_ALTA  # umbrales del módulo: los leen las observaciones y las recomendaciones
    OPORTUNIDAD_BAJA = parametro_numerico(parametros, "oportunidad_referencia_legalizaciones", OPORTUNIDAD_BAJA)
    EN_CURSO_ALTO = parametro_numerico(parametros, "en_curso_alto_legalizaciones", EN_CURSO_ALTO)
    ETAPA_ALTA = parametro_numerico(parametros, "etapa_alta_legalizaciones", ETAPA_ALTA)


def _senal_oportunidad(c: Calculo) -> str:
    return frase_senal(serie_hasta(c.serie_13, c.periodo, lambda x: x.oportunidad), porcentaje, PORCENTAJE)


def redactar(c: Calculo, parametros: dict[str, str] | None = None) -> Textos:
    _aplicar_parametros(parametros)
    general, especificos = objetivos(c)
    terminos, siglas = glosario(c)
    return Textos(
        resumen=resumen(c),
        hallazgos=hallazgos(c),
        objetivo_general=general,
        objetivos_especificos=especificos,
        metodologia=metodologia(c),
        observaciones=observaciones(c),
        recomendaciones=recomendaciones(c),
        conclusiones=conclusiones(c),
        glosario=terminos,
        siglas=siglas,
    )
