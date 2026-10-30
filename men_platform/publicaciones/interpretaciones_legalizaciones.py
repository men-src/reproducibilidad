"""La narrativa bajo cada gráfico y cada tabla del Informe de Legalizaciones: lo que muestra la pieza, dicho con las
cifras del mes, en tercera persona y sin rótulo. Cada función recibe el cálculo (y, cuando aplica, los grupos de una
categoría) y devuelve un párrafo; nada se escribe a mano para un mes concreto. Cuando una serie cruza dos años (los
últimos trece meses), los meses se nombran con su año para que no haya dos «enero»."""

from __future__ import annotations

from men_platform.publicaciones.datos_legalizaciones import NOMBRES_RANGOS, PARETO, Calculo, Categoria, Medidas
from men_platform.publicaciones.redaccion_legalizaciones import en_curso_en_texto, plazo_en_texto
from men_platform.publicaciones.texto_es import (
    decimal,
    entero,
    entre_tramo,
    lista_en_prosa,
    mayuscula_inicial,
    mes_y_anio,
    nombre_mes,
    numero_en_palabras,
    porcentaje,
    puntos,
    variacion,
)

Grupos = list[tuple[Categoria, Medidas]]


def _mes(c: Calculo) -> str:
    return nombre_mes(c.periodo)


def _etiqueta(p: str, serie: list) -> str:
    """«enero» si toda la serie es del mismo año; «enero de 2024» si cruza años."""
    return nombre_mes(p) if len({q[:4] for q, _ in serie}) <= 1 else mes_y_anio(p)


def _cuantos(n: int, femenino: bool = False) -> str:
    if n == 0:
        return "ninguno" if not femenino else "ninguna"
    return numero_en_palabras(n, femenino=femenino) if n != 1 else ("uno" if not femenino else "una")


def _plural(clase: str) -> str:
    return "metodologías" if clase == "metodologia" else "tipos de documento"


def _singular(clase: str) -> str:
    return "metodología" if clase == "metodologia" else "tipo de documento"


# --- 5.1 resumen del mes ----------------------------------------------------------------------------------------


def tabla_metodologias(c: Calculo) -> str:
    mets = c.metodologias_mes
    cat, mp = mets[0]
    frase = (
        f"La tabla reparte los {entero(c.mes.radicadas)} documentos radicados en {_mes(c)} entre las "
        f"{numero_en_palabras(len(mets))} metodologías con datos: {cat.bajo} es la principal, con {entero(mp.radicadas)} "
        f"({porcentaje(c.participacion(mp), 1)} del total), una tasa de legalización de {porcentaje(mp.tasa_legalizacion)} y "
        f"{porcentaje(mp.oportunidad)} de oportunidad"
    )
    if len(mets) > 1:
        k2, m2 = mets[1]
        frase += f"; le sigue {k2.bajo} ({entero(m2.radicadas)}, {porcentaje(c.participacion(m2), 1)})"
    con_fecha = [(k, v) for k, v in mets if v.legalizadas_con_fecha >= 100]
    if len(con_fecha) >= 2:
        mejor = max(con_fecha, key=lambda kv: kv[1].oportunidad or 0)
        peor = min(con_fecha, key=lambda kv: kv[1].oportunidad or 0)
        if mejor[0].id != peor[0].id:
            frase += (
                f". Entre las de al menos cien legalizadas, la mejor oportunidad es la de {mejor[0].bajo} ({porcentaje(mejor[1].oportunidad)}) y "
                f"la más baja la de {peor[0].bajo} ({porcentaje(peor[1].oportunidad)})"
            )
    return (
        frase
        + ". La tasa de legalización deja fuera lo en curso; la oportunidad se mide solo sobre las legalizadas con fecha."
    )


def barras_metodologias(c: Calculo) -> str:
    mets = c.metodologias_mes
    cat, mp = mets[0]
    frase = (
        f"Las barras ponen en escala lo que la tabla dice en cifras: {cat.bajo} sumó {entero(mp.radicadas)} radicadas"
    )
    if len(mets) > 1:
        k2, m2 = mets[1]
        veces = mp.radicadas / m2.radicadas if m2.radicadas else None
        if veces:
            frase += f", {decimal(veces, 1)} veces las de la segunda metodología ({k2.bajo})"
    pequenas = [k for k, v in mets if (c.participacion(v) or 0) < 0.01]
    if pequenas:
        frase += f". {mayuscula_inicial(lista_en_prosa([k.bajo for k in pequenas]))} {'pesa' if len(pequenas) == 1 else 'pesan'} menos del 1 % cada una"
    return frase + "."


def resultado_mes(c: Calculo) -> str:
    m = c.mes
    return (
        f"De los {entero(m.radicadas)} documentos radicados en {_mes(c)}, {entero(m.legalizadas)} ({porcentaje(m.legalizadas / m.radicadas if m.radicadas else None, 1)}) "
        f"estaban legalizados al corte, {entero(m.canceladas)} ({porcentaje(m.canceladas / m.radicadas if m.radicadas else None, 1)}) se cancelaron y "
        f"{en_curso_en_texto(m.en_curso, participacion=m.participacion_en_curso)}. La tasa de legalización, {porcentaje(m.tasa_legalizacion)}, "
        "sale de las legalizadas sobre las legalizadas más las canceladas: lo en curso puede terminar en cualquiera de los dos resultados."
    )


def treemap_metodologias(c: Calculo) -> str:
    mets = c.metodologias_mes
    cat, mp = mets[0]
    dos = sum(c.participacion(v) or 0 for _, v in mets[:2])
    frase = f"Cada metodología ocupa un área proporcional a sus radicadas en {_mes(c)}: {cat.bajo} cubre el {porcentaje(c.participacion(mp), 1)} del cuadro"
    if len(mets) > 1:
        frase += f" y, con {mets[1][0].bajo}, el {porcentaje(dos, 1)}"
    return frase + ". La participación dice cuánto pesa cada metodología en el mes, no cuánto crece."


# --- 5.2 comparación con el mes anterior ------------------------------------------------------------------------


def comparacion_indicadores(c: Calculo) -> str:
    m, ant = c.mes, c.mes_anterior
    if ant is None or not c.periodo_anterior:
        return f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico: no hay un mes anterior con el cual comparar."
    mes_ant = nombre_mes(c.periodo_anterior)
    frase = (
        f"Frente a {mes_ant}, las radicadas pasaron de {entero(ant.radicadas)} a {entero(m.radicadas)} ({variacion(m.radicadas, ant.radicadas)}) y las "
        f"legalizadas de {entero(ant.legalizadas)} a {entero(m.legalizadas)} ({variacion(m.legalizadas, ant.legalizadas)})"
    )
    if m.oportunidad is not None and ant.oportunidad is not None:
        frase += f"; la oportunidad {'subió' if m.oportunidad >= ant.oportunidad else 'bajó'} {puntos(m.oportunidad - ant.oportunidad)}"
    if m.tasa_legalizacion is not None and ant.tasa_legalizacion is not None:
        frase += f" y la tasa de legalización {'subió' if m.tasa_legalizacion >= ant.tasa_legalizacion else 'bajó'} {puntos(m.tasa_legalizacion - ant.tasa_legalizacion)}"
    frase += (
        f". Lo en curso ({entero(m.en_curso)} frente a {entero(ant.en_curso)}) pesa más en el mes reciente porque ha tenido menos tiempo para terminar: "
        "por eso su tasa de legalización tiende a subir en los informes siguientes."
    )
    return frase


def comparacion_metodologias(c: Calculo) -> str:
    ant = c.metodologias_mes_anterior
    if not ant or not c.periodo_anterior:
        return "No hay un mes anterior con el cual comparar las metodologías."
    subidas, bajadas = [], []
    for k, v in c.metodologias_mes:
        previo = ant.get(k.id)
        if previo is None or previo.radicadas < 50:
            continue
        texto = f"{k.bajo} ({variacion(v.radicadas, previo.radicadas)})"
        (subidas if v.radicadas >= previo.radicadas else bajadas).append(texto)
    frase = f"Frente a {nombre_mes(c.periodo_anterior)}, "
    partes = []
    if subidas:
        partes.append(f"{'subió' if len(subidas) == 1 else 'subieron'} {lista_en_prosa(subidas)}")
    if bajadas:
        partes.append(f"{'bajó' if len(bajadas) == 1 else 'bajaron'} {lista_en_prosa(bajadas)}")
    if not partes:
        return frase + "ninguna metodología con al menos cincuenta radicadas cambió de volumen."
    return (
        frase
        + "; ".join(partes)
        + ". Las metodologías con menos de cincuenta radicadas en el mes anterior se muestran sin juzgar su variación."
    )


# --- 5.3 evolución del año --------------------------------------------------------------------------------------


def radicadas_por_mes(c: Calculo) -> str:
    serie = c.serie_anio
    promedio = c.promedio_mensual or 0
    mayor, menor = c.mes_mayor, c.mes_menor
    arriba = [p for p, m in serie if m.radicadas > promedio]
    frase = (
        f"En {c.anio} se radicaron más documentos en {nombre_mes(mayor[0])} ({entero(mayor[1])}) y menos en {nombre_mes(menor[0])} "
        f"({entero(menor[1])}); el promedio mensual de los {numero_en_palabras(len(serie), femenino=False)} meses con datos es de {decimal(promedio, 1)}"
    )
    frase += f" y {_mes(c)} quedó {'por encima' if c.mes.radicadas >= promedio else 'por debajo'} de él, con {entero(c.mes.radicadas)} ({variacion(c.mes.radicadas, promedio)})"
    frase += f". {mayuscula_inicial(_cuantos(len(arriba)))} de los {_cuantos(len(serie))} meses {'superó' if len(arriba) == 1 else 'superaron'} el promedio."
    return frase


def resultado_por_mes(c: Calculo) -> str:
    serie = c.serie_anio
    con_tasa = [(p, m) for p, m in serie if m.tasa_legalizacion is not None]
    mejor = max(con_tasa, key=lambda pm: pm[1].tasa_legalizacion or 0)
    peor = min(con_tasa, key=lambda pm: pm[1].tasa_legalizacion or 0)
    frase = (
        f"Cada columna apila el resultado de los documentos radicados en el mes: legalizados abajo, cancelados y en curso arriba, con la tasa de "
        f"legalización encima. En {c.anio} la tasa más alta fue la de {nombre_mes(mejor[0])} ({porcentaje(mejor[1].tasa_legalizacion)}) y la más baja la de "
        f"{nombre_mes(peor[0])} ({porcentaje(peor[1].tasa_legalizacion)})"
    )
    mas_curso = max(serie, key=lambda pm: pm[1].participacion_en_curso or 0)
    frase += (
        f". Lo en curso pesa más en {nombre_mes(mas_curso[0])} ({porcentaje(mas_curso[1].participacion_en_curso, 1)} de sus radicadas): los meses "
        "recientes han tenido menos tiempo para terminar."
    )
    return frase


def resultado_100(c: Calculo) -> str:
    primero = c.serie_anio[0]
    ultimo = c.serie_anio[-1]
    return (
        f"Al 100 %, la parte legalizada de cada mes se lee de frente: {porcentaje(primero[1].legalizadas / primero[1].radicadas if primero[1].radicadas else None, 1)} en "
        f"{nombre_mes(primero[0])} y {porcentaje(ultimo[1].legalizadas / ultimo[1].radicadas if ultimo[1].radicadas else None, 1)} en {nombre_mes(ultimo[0])}, donde lo en "
        f"curso es el {porcentaje(ultimo[1].participacion_en_curso, 1)}. La parte cancelada es pequeña en todos los meses; la diferencia entre meses está en cuánto "
        "sigue en curso, que baja a medida que el mes envejece."
    )


def mezcla_metodologias(c: Calculo, catalogo: dict[int, Categoria]) -> str:
    serie = c.metodologia_por_mes
    p, ultimo = serie[-1]
    total = sum(ultimo.values()) or 1
    partes = sorted(ultimo.items(), key=lambda kv: -kv[1])
    principal = partes[0]
    nombre = catalogo[principal[0]].bajo if principal[0] in catalogo else "sin homologar"
    frase = f"En {nombre_mes(p)}, {nombre} fue el {porcentaje(principal[1] / total, 1)} de las radicadas"
    p0, primero = serie[0]
    if p0 != p:
        total0 = sum(primero.values()) or 1
        parte0 = primero.get(principal[0], 0) / total0
        frase += f", frente al {porcentaje(parte0, 1)} de {nombre_mes(p0)}"
    if len(partes) > 1:
        segundo = partes[1]
        nombre2 = catalogo[segundo[0]].bajo if segundo[0] in catalogo else "sin homologar"
        frase += f"; {nombre2} fue el {porcentaje(segundo[1] / total, 1)}"
    return (
        frase
        + ". La mezcla dice cuánto pesa cada metodología, no cuánto crece: una puede ganar parte mientras todas bajan."
    )


# --- 5.4 volumen general ----------------------------------------------------------------------------------------


def dos_anios_radicadas(c: Calculo) -> str:
    anio, anio_ant = c.anio, c.anio - 1
    actual = {int(p[5:7]): m.radicadas for p, m in c.serie_anio}
    anterior = {int(p[5:7]): m.radicadas for p, m in c.serie_anio_anterior}
    comunes = [k for k in actual if k in anterior]
    if not comunes:
        if len(c.serie_anio) == 1:
            return f"No hay meses de {anio_ant} con datos para comparar; {anio} empieza con {nombre_mes(c.periodo)}, con {entero(c.mes.radicadas)} radicadas."
        mayor = c.mes_mayor
        return f"No hay meses de {anio_ant} con datos para comparar; en {anio} el mes de más radicadas fue {nombre_mes(mayor[0])} ({entero(mayor[1])})."
    arriba = [k for k in comunes if actual[k] > anterior[k]]
    frase = f"De los {_cuantos(len(comunes))} meses de {anio} con un par en {anio_ant}, {_cuantos(len(arriba))} {'superó' if len(arriba) == 1 else 'superaron'} al año anterior"
    mayor = max(comunes, key=lambda k: abs(actual[k] - anterior[k]))
    frase += (
        f"; la mayor diferencia fue en {nombre_mes(f'{anio}-{mayor:02d}-01')}: {entero(actual[mayor])} frente a {entero(anterior[mayor])} "
        f"({variacion(actual[mayor], anterior[mayor])})"
    )
    if c.mes_numero in anterior:
        frase += f". {mayuscula_inicial(_mes(c))} quedó {variacion(actual[c.mes_numero], anterior[c.mes_numero])} frente a {_mes(c)} de {anio_ant}"
    if c.acumulado_anterior is not None and c.meses_acumulado >= 2:
        frase += (
            f"; el acumulado de los mismos meses pasó de {entero(c.acumulado_anterior.radicadas)} a {entero(c.acumulado.radicadas)} "
            f"({variacion(c.acumulado.radicadas, c.acumulado_anterior.radicadas)})"
        )
    return frase + "."


def variacion_radicadas(c: Calculo) -> str:
    serie = c.serie_13
    pares = [
        (serie[i][0], serie[i][1].radicadas, serie[i - 1][1].radicadas)
        for i in range(1, len(serie))
        if serie[i - 1][1].radicadas
    ]
    if not pares:
        return "No hay dos meses consecutivos con datos para medir la variación."
    sube = max(pares, key=lambda x: x[1] / x[2])
    baja = min(pares, key=lambda x: x[1] / x[2])
    ultimo = pares[-1]
    return (
        f"La mayor subida de un mes al siguiente fue en {mes_y_anio(sube[0])} ({variacion(sube[1], sube[2])}) y la mayor caída en "
        f"{mes_y_anio(baja[0])} ({variacion(baja[1], baja[2])}). {mayuscula_inicial(mes_y_anio(ultimo[0]))} varió {variacion(ultimo[1], ultimo[2])} frente al "
        "mes anterior. Cada barra compara el mes con el inmediatamente anterior; enero se compara con diciembre del año anterior."
    )


def media_movil_radicadas(c: Calculo) -> str:
    serie = [
        (p, m.radicadas, c.media_movil_radicadas.get(p))
        for p, m in c.serie_13
        if c.media_movil_radicadas.get(p) is not None
    ]
    if not serie:
        return "Todavía no hay tres meses anteriores con datos para calcular la media móvil."
    arriba = [x for x in serie if x[1] > (x[2] or 0)]
    p, v, mm = serie[-1]
    return (
        f"De los {_cuantos(len(serie))} meses con media móvil, {_cuantos(len(arriba))} {'quedó' if len(arriba) == 1 else 'quedaron'} por encima de ella. En "
        f"{mes_y_anio(p)}, {entero(v)} radicadas frente a una media de {entero(round(mm or 0))} de los tres meses anteriores ({variacion(v, mm)}). La media "
        "móvil suaviza los picos y dice si el mes está por encima o por debajo de su tendencia reciente."
    )


# --- 5.5 porcentaje de oportunidad ------------------------------------------------------------------------------


def oportunidad_dos_anios(c: Calculo) -> str:
    anio, anio_ant = c.anio, c.anio - 1
    actual = {int(p[5:7]): m.oportunidad for p, m in c.serie_anio if m.oportunidad is not None}
    anterior = {int(p[5:7]): m.oportunidad for p, m in c.serie_anio_anterior if m.oportunidad is not None}
    comunes = [k for k in actual if k in anterior]
    mejor = max(actual.items(), key=lambda kv: kv[1])
    peor = min(actual.items(), key=lambda kv: kv[1])
    frase = (
        f"En {anio} la oportunidad más alta fue la de {nombre_mes(f'{anio}-{mejor[0]:02d}-01')} ({porcentaje(mejor[1])}) y la más baja la de "
        f"{nombre_mes(f'{anio}-{peor[0]:02d}-01')} ({porcentaje(peor[1])})"
    )
    if comunes:
        arriba = [k for k in comunes if actual[k] > anterior[k]]
        frase += f". {mayuscula_inicial(_cuantos(len(arriba)))} de los {_cuantos(len(comunes))} meses con un par en {anio_ant} {'superó' if len(arriba) == 1 else 'superaron'} al año anterior"
        if c.mes_numero in anterior:
            frase += f"; {_mes(c)} quedó {puntos(actual[c.mes_numero] - anterior[c.mes_numero])} frente a {_mes(c)} de {anio_ant} ({porcentaje(anterior[c.mes_numero])})"
    else:
        frase += f". No hay meses de {anio_ant} con los cuales comparar"
    return (
        frase
        + ". El índice se lee junto con el volumen: un mes con muchas legalizadas y buena oportunidad vale más que uno tranquilo."
    )


def a_tiempo_por_mes(c: Calculo) -> str:
    serie = c.serie_anio
    mas_tarde = max(serie, key=lambda pm: pm[1].extemporaneas)
    m = c.mes
    return (
        f"Las columnas apilan las legalizadas de cada mes de radicación: a tiempo (hasta {plazo_en_texto(c)}) abajo y extemporáneas arriba, con el "
        f"porcentaje de oportunidad encima. En {_mes(c)}, {entero(m.a_tiempo)} de {entero(m.legalizadas_con_fecha)} legalizadas se gestionaron a tiempo y "
        f"{entero(m.extemporaneas)} tardaron más; el mes con más extemporáneas de {c.anio} fue {nombre_mes(mas_tarde[0])} ({entero(mas_tarde[1].extemporaneas)})."
    )


def variacion_oportunidad(c: Calculo) -> str:
    serie = [(p, m.oportunidad) for p, m in c.serie_13]
    cambios = [
        (serie[i][0], serie[i][1] - serie[i - 1][1])
        for i in range(1, len(serie))
        if serie[i][1] is not None and serie[i - 1][1] is not None
    ]
    if not cambios:
        return "No hay meses consecutivos con oportunidad para medir la variación."
    sube = max(cambios, key=lambda x: x[1])
    baja = min(cambios, key=lambda x: x[1])
    ultimo = cambios[-1]
    return (
        f"De un mes al siguiente, la oportunidad subió más en {mes_y_anio(sube[0])} ({puntos(sube[1])}) y bajó más en {mes_y_anio(baja[0])} ({puntos(baja[1])}). "
        f"En {mes_y_anio(ultimo[0])} la variación fue de {puntos(ultimo[1])}, {'una mejora' if ultimo[1] > 0 else 'un retroceso' if ultimo[1] < 0 else 'sin cambio'} "
        "frente al mes inmediatamente anterior. Las barras del mismo color seguidas muestran rachas; los cambios de signo, meses que rompen la tendencia."
    )


def media_movil_oportunidad(c: Calculo) -> str:
    actual = c.mes.oportunidad
    mm = c.media_movil_oportunidad.get(c.periodo)
    if actual is None or mm is None:
        return "No hay tres meses anteriores completos para calcular la media móvil ponderada."
    ultimos = [(p, m.oportunidad, c.media_movil_oportunidad.get(p)) for p, m in c.serie_13[1:]]
    encima = sum(1 for _, v, media in ultimos if v is not None and media is not None and v > media)
    return (
        f"La media móvil ponderada compara cada mes con las legalizadas a tiempo de los tres meses anteriores sobre sus legalizadas con fecha. En {_mes(c)}, la "
        f"oportunidad fue de {porcentaje(actual)} frente a una media móvil de {porcentaje(mm)} ({puntos(actual - mm)}); en {numero_en_palabras(encima, False)} de los "
        f"últimos {_cuantos(len(ultimos))} meses el valor real quedó por encima de su media móvil. Estar por encima es una buena señal: el mes mejora su tendencia reciente."
    )


def mapa_calor(c: Calculo) -> str:
    celdas = [
        (a, m, v)
        for a, meses in c.matriz_oportunidad.items()
        for m, v in meses.items()
        if v is not None and m <= c.mes_numero
    ]
    if len(celdas) <= 1:
        return f"El histórico empieza en {mes_y_anio(c.periodo)}, así que el mapa tiene por ahora una sola celda; cada mes nuevo agregará la suya."
    mejor = max(celdas, key=lambda x: x[2])
    peor = min(celdas, key=lambda x: x[2])
    mismo_mes = sorted([(a, v) for a, m, v in celdas if m == c.mes_numero], key=lambda x: -x[1])
    puesto = next(i for i, (a, _) in enumerate(mismo_mes, start=1) if a == c.anio)
    fila_actual = [v for a, _, v in celdas if a == c.anio]
    fila_anterior = [v for a, _, v in celdas if a == c.anio - 1]
    texto = (
        f"{entre_tramo(c.periodo)} de cada año del histórico, el mejor mes fue {nombre_mes(f'{mejor[0]}-{mejor[1]:02d}-01')} de {mejor[0]} ({porcentaje(mejor[2])}) y el peor "
        f"{nombre_mes(f'{peor[0]}-{peor[1]:02d}-01')} de {peor[0]} ({porcentaje(peor[2])})."
    )
    if len(mismo_mes) == 1:
        texto += f" Es el primer {_mes(c)} del histórico."
    else:
        texto += f" Entre los {numero_en_palabras(len(mismo_mes), False)} meses de {_mes(c)} del histórico, el de {c.anio} ocupa el puesto {puesto}."
    if fila_actual and fila_anterior:
        prom_a = sum(fila_actual) / len(fila_actual)
        prom_b = sum(fila_anterior) / len(fila_anterior)
        texto += f" La fila de {c.anio} es, en promedio, {'más clara' if prom_a < prom_b else 'más oscura'} que la de {c.anio - 1}: {porcentaje(prom_a)} frente a {porcentaje(prom_b)}."
    return (
        texto
        + " Las celdas rojas marcan los meses que exigen explicación; las azules oscuras, los que vale la pena replicar."
    )


def histograma(c: Calculo) -> str:
    m = c.mes
    conteos = m.habiles
    total = sum(conteos) or 1
    moda = max(range(len(conteos)), key=lambda i: conteos[i])
    limite = min(max(0, c.plazo), 15)
    dentro = sum(conteos[: limite + 1])
    tarde_mucho = sum(conteos[limite + 6 :])  # más de cinco días hábiles pasado el plazo
    etiqueta_moda = f"{moda} {'día hábil' if moda == 1 else 'días hábiles'}" if moda < 16 else "más de 15 días hábiles"
    return (
        f"La mayor concentración de legalizadas de {_mes(c)} está en {etiqueta_moda} de gestión ({entero(conteos[moda])}, {porcentaje(conteos[moda] / total, 1)}); "
        f"{entero(dentro)} ({porcentaje(dentro / total, 1)}) caben en el plazo de {plazo_en_texto(c)} y {entero(total - dentro)} lo pasan, de las cuales "
        f"{entero(tarde_mucho)} tardaron más de {limite + 5} días hábiles. La línea es el acumulado: cuántas legalizadas se resolvieron en ese número de días o menos."
    )


def oportunidad_categoria(c: Calculo, grupos: Grupos, clase: str) -> str:
    con_fecha = [(k, v) for k, v in grupos if v.legalizadas_con_fecha >= 100]
    if len(con_fecha) < 2:
        k, v = grupos[0]
        return f"{mayuscula_inicial(k.bajo)} reúne casi todas las legalizadas del mes: {entero(v.a_tiempo)} a tiempo de {entero(v.legalizadas_con_fecha)} ({porcentaje(v.oportunidad)})."
    mejor = max(con_fecha, key=lambda kv: kv[1].oportunidad or 0)
    peor = min(con_fecha, key=lambda kv: kv[1].oportunidad or 0)
    k0, v0 = grupos[0]
    frase = (
        f"Cada barra apila las legalizadas de {'una' if clase == 'metodologia' else 'un'} {_singular(clase)}: a tiempo en azul y extemporáneas en rojo, con el total y "
        f"su oportunidad al final. {mayuscula_inicial(k0.bajo)}, {'la' if clase == 'metodologia' else 'el'} de mayor volumen, tuvo {porcentaje(v0.oportunidad)} "
        f"({entero(v0.a_tiempo)} de {entero(v0.legalizadas_con_fecha)})"
    )
    if mejor[0].id != peor[0].id:
        frase += (
            f"; entre {'las' if clase == 'metodologia' else 'los'} de al menos cien legalizadas, la oportunidad más alta fue la de {mejor[0].bajo} "
            f"({porcentaje(mejor[1].oportunidad)}) y la más baja la de {peor[0].bajo} ({porcentaje(peor[1].oportunidad)}, "
            f"{decimal(peor[1].promedio_dias_habiles_legalizadas, 1)} días hábiles en promedio)"
        )
    return frase + "."


# --- 5.6 resultado ----------------------------------------------------------------------------------------------


def tasa_dos_anios(c: Calculo) -> str:
    anio, anio_ant = c.anio, c.anio - 1
    actual = {int(p[5:7]): m.tasa_legalizacion for p, m in c.serie_anio if m.tasa_legalizacion is not None}
    anterior = {int(p[5:7]): m.tasa_legalizacion for p, m in c.serie_anio_anterior if m.tasa_legalizacion is not None}
    mejor = max(actual.items(), key=lambda kv: kv[1])
    peor = min(actual.items(), key=lambda kv: kv[1])
    frase = (
        f"La tasa de legalización, las legalizadas sobre las legalizadas más las canceladas, fue más alta en {nombre_mes(f'{anio}-{mejor[0]:02d}-01')} ({porcentaje(mejor[1])}) "
        f"y más baja en {nombre_mes(f'{anio}-{peor[0]:02d}-01')} ({porcentaje(peor[1])}) de {anio}"
    )
    if c.mes_numero in anterior and c.mes_numero in actual:
        frase += f"; {_mes(c)} quedó {puntos(actual[c.mes_numero] - anterior[c.mes_numero])} frente a {_mes(c)} de {anio_ant} ({porcentaje(anterior[c.mes_numero])})"
    return (
        frase
        + ". Los documentos en curso no entran en la tasa, así que la de los meses recientes puede subir cuando terminen."
    )


def resultado_categoria(c: Calculo, grupos: Grupos, clase: str) -> str:
    k0, v0 = grupos[0]
    con_resultado = [(k, v) for k, v in grupos if v.con_resultado >= 100]
    frase = (
        f"Cada barra apila el resultado de {'una' if clase == 'metodologia' else 'un'} {_singular(clase)}: legalizadas en azul, canceladas en rojo y en curso en amarillo. "
        f"{mayuscula_inicial(k0.bajo)} tuvo {entero(v0.legalizadas)} legalizadas, {entero(v0.canceladas)} canceladas y {entero(v0.en_curso)} en curso "
        f"({porcentaje(v0.tasa_legalizacion)} de tasa de legalización)"
    )
    if len(con_resultado) >= 2:
        peor = min(con_resultado, key=lambda kv: kv[1].tasa_legalizacion or 0)
        if peor[0].id != k0.id:
            frase += f"; la tasa más baja entre {'las' if clase == 'metodologia' else 'los'} de al menos cien con resultado fue la de {peor[0].bajo} ({porcentaje(peor[1].tasa_legalizacion)})"
    mas_curso = max(grupos, key=lambda kv: kv[1].participacion_en_curso or 0)
    frase += f". Lo en curso pesa más en {mas_curso[0].bajo} ({porcentaje(mas_curso[1].participacion_en_curso, 1)} de sus radicadas)."
    return frase


# --- 5.7 tiempos --------------------------------------------------------------------------------------------------


def dias_por_mes(c: Calculo) -> str:
    serie = [(p, m) for p, m in c.serie_anio if m.promedio_dias is not None]
    mas = max(serie, key=lambda pm: pm[1].promedio_dias or 0)
    menos = min(serie, key=lambda pm: pm[1].promedio_dias or 0)
    m = c.mes
    return (
        f"Los documentos con resultado radicados en {_mes(c)} tardaron en promedio {decimal(m.promedio_dias, 1)} días calendario y {decimal(m.promedio_dias_habiles, 1)} días "
        f"hábiles hasta su resultado. En {c.anio} el mes más lento fue {nombre_mes(mas[0])} ({decimal(mas[1].promedio_dias, 1)} días calendario) y el más rápido "
        f"{nombre_mes(menos[0])} ({decimal(menos[1].promedio_dias, 1)}). Las dos líneas se separan por los fines de semana y festivos; la de días hábiles es la que mide la gestión."
    )


def tabla_tiempos(c: Calculo) -> str:
    m = c.mes
    return (
        f"En {_mes(c)}, el {porcentaje(m.hasta_cinco_dias, 1)} de los {entero(m.con_dias)} documentos con resultado se resolvió en cinco días calendario o menos y el "
        f"{porcentaje(m.mas_de_quince_dias, 1)} tardó más de quince. Las dos colas resumen la distribución: la primera dice cuánto se resuelve rápido; la segunda, cuánto se "
        "queda atrás."
    )


def rangos_por_mes(c: Calculo) -> str:
    m = c.mes
    total = m.con_dias or 1
    mayor = max(range(len(m.rangos)), key=lambda i: m.rangos[i])
    return (
        f"Cada columna reparte al 100 % los documentos con resultado de su mes por rangos de días calendario, de los más rápidos abajo a los más lentos arriba. En "
        f"{_mes(c)} el rango más frecuente fue el de {NOMBRES_RANGOS[mayor].lower()} ({porcentaje(m.rangos[mayor] / total, 1)}); los de más de quince días suman el "
        f"{porcentaje(m.mas_de_quince_dias, 1)}. Cuando la parte roja crece, los tiempos se alargan aunque el promedio se mueva poco."
    )


def etapas(c: Calculo) -> str:
    serie = c.serie_anio
    mas_comp = max(serie, key=lambda pm: pm[1].tasa_complementacion or 0)
    mas_val = max(serie, key=lambda pm: pm[1].tasa_validacion_ies or 0)
    m = c.mes
    return (
        f"En {_mes(c)}, el {porcentaje(m.tasa_complementacion, 1)} de los documentos radicados pasó por complementación y el {porcentaje(m.tasa_validacion_ies, 1)} por "
        f"validación con la IES. En {c.anio} la complementación pesó más en {nombre_mes(mas_comp[0])} ({porcentaje(mas_comp[1].tasa_complementacion, 1)}) y la validación "
        f"con la IES en {nombre_mes(mas_val[0])} ({porcentaje(mas_val[1].tasa_validacion_ies, 1)}). Las dos etapas alargan el trámite: un mes con más validación suele traer "
        "más documentos en curso al corte."
    )


def dias_categoria(c: Calculo, grupos: Grupos) -> str:
    con_dias = [(k, v) for k, v in grupos if v.con_dias >= 100]
    if not con_dias:
        con_dias = grupos
    lento = max(con_dias, key=lambda kv: kv[1].promedio_dias_habiles or 0)
    rapido = min(con_dias, key=lambda kv: kv[1].promedio_dias_habiles or 0)
    k0, v0 = grupos[0]
    frase = f"{mayuscula_inicial(k0.bajo)}, la metodología de mayor volumen, tardó {decimal(v0.promedio_dias, 1)} días calendario y {decimal(v0.promedio_dias_habiles, 1)} hábiles en promedio"
    if lento[0].id != rapido[0].id:
        frase += (
            f"; entre las de al menos cien documentos con resultado, la más lenta fue {lento[0].bajo} ({decimal(lento[1].promedio_dias_habiles, 1)} días hábiles) y la "
            f"más rápida {rapido[0].bajo} ({decimal(rapido[1].promedio_dias_habiles, 1)})"
        )
    return frase + ". Las barras van de la metodología de mayor a la de menor volumen."


# --- 5.8 y 5.9 categorías -----------------------------------------------------------------------------------------


def pareto_categoria(c: Calculo, grupos: Grupos, clase: str) -> str:
    n = c.cuantas_para_pareto(grupos)
    nombres = [k.bajo for k, _ in grupos[:n]]
    acumulado = sum(c.participacion(v) or 0 for _, v in grupos[:n])
    femenino = clase == "metodologia"
    frase = (
        f"{mayuscula_inicial(numero_en_palabras(n, femenino=femenino))} de {'las' if femenino else 'los'} {numero_en_palabras(len(grupos), femenino=femenino)} "
        f"{_plural(clase)} ({lista_en_prosa(nombres)}) {'explica' if n == 1 else 'explican'} el {porcentaje(acumulado, 1)} de las radicadas de {_mes(c)}, por encima de "
        f"la guía del {porcentaje(PARETO, 0)}"
    )
    resto = len(grupos) - n
    if resto > 0:
        frase += f"; {'las' if femenino else 'los'} {'otra' if resto == 1 else 'otros' if not femenino else 'otras'} {numero_en_palabras(resto, femenino=femenino)} {'reúne' if resto == 1 else 'reúnen'} el {porcentaje(1 - acumulado, 1)} restante"
    return frase + ". La línea es la participación acumulada de mayor a menor."


def categoria_dos_anios(c: Calculo, grupos: Grupos, anteriores: dict[int, Medidas], clase: str) -> str:
    anio, anio_ant = c.anio, c.anio - 1
    con_par = [(k, v) for k, v in grupos if k.id in anteriores and anteriores[k.id].radicadas]
    femenino = clase == "metodologia"
    if not con_par:
        return f"{'Ninguna' if femenino else 'Ningún'} {_singular(clase)} tiene datos en los mismos meses de {anio_ant}: no hay con qué comparar el acumulado de {anio}."
    crecen = [(k, v) for k, v in con_par if v.radicadas > anteriores[k.id].radicadas]
    caen = [(k, v) for k, v in con_par if v.radicadas < anteriores[k.id].radicadas]
    frase = ("Con el mismo mes" if c.meses_acumulado == 1 else "Con los mismos meses") + " en los dos años, "
    partes = []
    if crecen:
        partes.append(
            f"{'creció' if len(crecen) == 1 else 'crecieron'} {lista_en_prosa([f'{k.bajo} ({variacion(v.radicadas, anteriores[k.id].radicadas)})' for k, v in crecen[:5]])}"
        )
    if caen:
        partes.append(
            f"{'bajó' if len(caen) == 1 else 'bajaron'} {lista_en_prosa([f'{k.bajo} ({variacion(v.radicadas, anteriores[k.id].radicadas)})' for k, v in caen[:5]])}"
        )
    frase += "; ".join(partes)
    nuevos = [k for k, v in grupos if k.id not in anteriores or not anteriores[k.id].radicadas]
    if nuevos:
        frase += f". {mayuscula_inicial(lista_en_prosa([k.bajo for k in nuevos[:5]]))} no {'tenía' if len(nuevos) == 1 else 'tenían'} datos en esos meses de {anio_ant}"
    return frase + "."


def barras_documentos(c: Calculo) -> str:
    docs = c.documentos_mes
    k0, v0 = docs[0]
    frase = f"{mayuscula_inicial(k0.bajo)} es el tipo de documento más radicado en {_mes(c)}: {entero(v0.radicadas)} ({porcentaje(c.participacion(v0), 1)})"
    if len(docs) > 2:
        k1, v1 = docs[1]
        k2, v2 = docs[2]
        tres = sum(c.participacion(v) or 0 for _, v in docs[:3])
        frase += f"; con {k1.bajo} ({entero(v1.radicadas)}) y {k2.bajo} ({entero(v2.radicadas)}) reúne el {porcentaje(tres, 1)} del mes"
    if len(docs) > 15:
        frase += f". Se muestran los quince de mayor volumen de {numero_en_palabras(len(docs), femenino=False)} con datos; la tabla del anexo trae el resto"
    return frase + "."


def treemap_documentos(c: Calculo, maximo: int) -> str:
    docs = c.documentos_mes
    k0, v0 = docs[0]
    otros = docs[maximo:]
    frase = f"Cada tipo de documento ocupa un área proporcional a sus radicadas: {k0.bajo} cubre el {porcentaje(c.participacion(v0), 1)} del cuadro"
    if otros:
        parte = sum(c.participacion(v) or 0 for _, v in otros)
        frase += f"; los {numero_en_palabras(len(otros), femenino=False)} tipos de menor volumen van juntos en «Otros», con el {porcentaje(parte, 1)}"
    return frase + ". La participación dice cuánto pesa cada tipo en el mes, no cuánto crece."


def anexo(c: Calculo) -> str:
    return (
        f"Una fila por mes de {c.anio} con los documentos radicados en cada metodología y el total; la última fila acumula el año. Después, el resultado y la "
        "oportunidad de cada mes. Son las cifras con las que se dibujaron los gráficos de este informe."
    )
