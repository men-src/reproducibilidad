"""La narrativa bajo cada gráfico y cada tabla del Informe de Canales de Atención: lo que muestra la pieza, dicho con
las cifras del mes, en tercera persona y sin rótulo. Cada función recibe el cálculo o la serie de un canal y devuelve
un párrafo; nada se escribe a mano para un mes concreto. Cuando la serie cruza dos años (los últimos trece meses con
datos), los meses se nombran con su año para que no haya dos «enero»."""

from __future__ import annotations

from men_platform.publicaciones.datos_canales import Calculo, SerieCanal
from men_platform.publicaciones.texto_es import (
    decimal,
    entero,
    lista_en_prosa,
    mayuscula_inicial,
    mes_y_anio,
    nombre_mes,
    numero_en_palabras,
    porcentaje,
    puntos,
    variacion,
)

ATIPICO = 3.0  # una variación mayor que 300 % delata un mes anterior atípico (casi sin datos)


def _mes(c: Calculo) -> str:
    return nombre_mes(c.periodo)


def _etiqueta(p: str, serie: list) -> str:
    """«enero» si toda la serie es del mismo año; «enero de 2024» si cruza años."""
    return nombre_mes(p) if len({q[:4] for q, _ in serie}) <= 1 else mes_y_anio(p)


def tabla_canales(c: Calculo) -> str:
    todos = c.todos
    con_datos = sorted([s for s in c.canales if s.mes], key=lambda s: -s.mes.recibidas)
    mayor = con_datos[0]
    frase = (
        f"La tabla reparte las {entero(todos.mes.recibidas)} interacciones de {_mes(c)} entre los canales con datos: {mayor.nombre.lower()} "
        f"es el de mayor volumen, con el {porcentaje(mayor.mes.recibidas / todos.mes.recibidas, 1)} del total"
    )
    if len(con_datos) > 1:
        menor = con_datos[-1]
        frase += f", y {menor.nombre.lower()} el de menor, con {entero(menor.mes.recibidas)}"
    frase += (
        ". Cada tipo de canal trae las medidas que su fuente permite: niveles en los de contacto, resolución en el chatbot, efectividad y "
        "tasa de no efectivas en la devolución de llamadas y el buzón de voz, y solo el total en la atención presencial; lo que no aplica "
        "va con guion."
    )
    return frase


def apiladas_por_canal(c: Calculo) -> str:
    serie = c.canal_por_mes
    totales = [(p, sum(t.recibidas for _, t in lista)) for p, lista in serie]
    mayor = max(totales, key=lambda x: x[1])
    menor = min(totales, key=lambda x: x[1])
    k = c.contacto
    frase = (
        f"Mes a mes en {c.anio}, el volumen total fue mayor en {nombre_mes(mayor[0])} ({entero(mayor[1])} interacciones) y menor en "
        f"{nombre_mes(menor[0])} ({entero(menor[1])}); {_mes(c)} cierra con {entero(c.todos.mes.recibidas)}"
    )
    if k.serie_anio:
        mejor = max(k.serie_anio, key=lambda pt: pt[1].nivel_atencion or 0)
        peor = min(k.serie_anio, key=lambda pt: pt[1].nivel_atencion or 0)
        frase += (
            f". La línea del nivel de atención de los canales de contacto fue más alta en {nombre_mes(mejor[0])} "
            f"({porcentaje(mejor[1].nivel_atencion)}) y más baja en {nombre_mes(peor[0])} ({porcentaje(peor[1].nivel_atencion)})"
        )
    return frase + "."


def niveles_mes_a_mes(c: Calculo) -> str:
    k = c.contacto
    serie = k.serie_anio
    if not serie:
        return "Los canales de contacto no tienen datos en el año del informe."
    at = [(p, t.nivel_atencion) for p, t in serie if t.nivel_atencion is not None]
    ns = [(p, t.nivel_servicio) for p, t in serie if t.nivel_servicio is not None]
    frase = (
        f"El nivel de atención de los canales de contacto se movió entre {porcentaje(min(v for _, v in at))} y "
        f"{porcentaje(max(v for _, v in at))} en {c.anio}"
    )
    if ns:
        peor = min(ns, key=lambda x: x[1])
        frase += (
            f"; el nivel de servicio, siempre por debajo del de atención porque exige contestar antes del tiempo objetivo, tocó su "
            f"mínimo en {nombre_mes(peor[0])} ({porcentaje(peor[1])})"
        )
    if k.mes:
        brecha = ((k.mes.nivel_atencion or 0) - (k.mes.nivel_servicio or 0)) * 100
        frase += f". En {_mes(c)} la distancia entre los dos niveles fue de {decimal(brecha, 2)} pp: lo que se atendió, pero con espera."
    return frase


def mezcla(c: Calculo) -> str:
    serie = c.canal_por_mes
    p, lista = serie[-1]
    total = sum(t.recibidas for _, t in lista) or 1
    partes = sorted(lista, key=lambda ct: -ct[1].recibidas)
    primero = partes[0]
    frase = f"En {nombre_mes(p)}, {primero[0].nombre.lower()} fue el {porcentaje(primero[1].recibidas / total, 1)} de todo lo recibido"
    p0, lista0 = serie[0]
    if p0 != p:
        total0 = sum(t.recibidas for _, t in lista0) or 1
        parte0 = next((t.recibidas / total0 for cn, t in lista0 if cn.id == primero[0].id), None)
        if parte0 is not None:
            frase += f", frente al {porcentaje(parte0, 1)} de {nombre_mes(p0)}"
    digitales = [ct for ct in partes if ct[0].tipo == "chatbot" or ct[0].id in (2, 3, 4)]
    if digitales:
        frase += (
            f"; los canales digitales (chat, llamada virtual, video llamada y chatbot) sumaron el "
            f"{porcentaje(sum(t.recibidas for _, t in digitales) / total, 1)}"
        )
    return (
        frase
        + ". La mezcla dice cuánto pesa cada canal, no cuánto crece: un canal puede ganar parte mientras todos bajan."
    )


def comparacion_mes_anterior(c: Calculo) -> str:
    todos = c.todos
    if not todos.mes_anterior:
        return f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico: no hay un mes anterior con el cual comparar."
    subidas = []
    bajadas = []
    for s in c.canales:
        if s.mes and s.mes_anterior and s.periodo_anterior == todos.periodo_anterior:
            v = variacion(s.mes.recibidas, s.mes_anterior.recibidas)
            (subidas if s.mes.recibidas >= s.mes_anterior.recibidas else bajadas).append(f"{s.nombre.lower()} ({v})")
    frase = (
        f"Frente a {nombre_mes(todos.periodo_anterior)}, el total pasó de {entero(todos.mes_anterior.recibidas)} a "
        f"{entero(todos.mes.recibidas)} ({variacion(todos.mes.recibidas, todos.mes_anterior.recibidas)})"
    )
    if subidas:
        frase += f"; subieron {lista_en_prosa(subidas)}"
    if bajadas:
        frase += f"; bajaron {lista_en_prosa(bajadas)}"
    return frase + "."


def comparacion_niveles(c: Calculo) -> str:
    k = c.contacto
    if not (k.mes and k.mes_anterior):
        return "Los canales de contacto no tienen dos meses seguidos con datos para comparar sus niveles."
    mes_ant = nombre_mes(k.periodo_anterior)
    mejoran = []
    empeoran = []
    for s in c.por_tipo("contacto"):
        if s.mes and s.mes_anterior and s.mes.nivel_atencion is not None and s.mes_anterior.nivel_atencion is not None:
            d = s.mes.nivel_atencion - s.mes_anterior.nivel_atencion
            if abs(d) >= 0.0005:
                (mejoran if d > 0 else empeoran).append(f"{s.nombre.lower()} ({puntos(d)})")
    d_at = (k.mes.nivel_atencion or 0) - (k.mes_anterior.nivel_atencion or 0)
    d_ns = (k.mes.nivel_servicio or 0) - (k.mes_anterior.nivel_servicio or 0)
    frase = (
        f"En el conjunto de los canales de contacto, el nivel de atención pasó de {porcentaje(k.mes_anterior.nivel_atencion)} en {mes_ant} a "
        f"{porcentaje(k.mes.nivel_atencion)} ({puntos(d_at)}) y el nivel de servicio de {porcentaje(k.mes_anterior.nivel_servicio)} a "
        f"{porcentaje(k.mes.nivel_servicio)} ({puntos(d_ns)})"
    )
    if mejoran:
        frase += f"; el nivel de atención mejoró en {lista_en_prosa(mejoran)}"
    if empeoran:
        frase += f"; bajó en {lista_en_prosa(empeoran)}"
    return frase + ". Las diferencias van en puntos porcentuales."


def comparacion_otros(c: Calculo) -> str:
    partes = []
    for s in c.canales:
        if s.tipo not in ("chatbot", "callback") or not (s.mes and s.mes_anterior):
            continue
        campo, nombre = ("resolucion", "la resolución") if s.tipo == "chatbot" else ("efectividad", "la efectividad")
        de_quien = {5: "del chatbot", 6: "de la devolución de llamadas", 8: "del buzón de voz"}.get(
            s.canal.id, f"de {s.nombre.lower()}"
        )
        antes, ahora = getattr(s.mes_anterior, campo), getattr(s.mes, campo)
        if antes is None or ahora is None:
            continue
        partes.append(
            f"{nombre} {de_quien} pasó de {porcentaje(antes)} a {porcentaje(ahora)} ({puntos(ahora - antes)})"
        )
    if not partes:
        return "Ni el chatbot ni los canales de devolución tienen dos meses seguidos con datos para comparar."
    return (
        mayuscula_inicial(lista_en_prosa(partes))
        + ". La resolución es lo resuelto sin agente sobre lo resuelto más lo transferido; la efectividad, las llamadas efectivas sobre "
        "las solicitudes o los mensajes."
    )


# --- por canal ------------------------------------------------------------------------------------------------


def _serie_texto(s: SerieCanal) -> list:
    return s.serie_anio if len(s.serie_anio) >= 2 else s.serie_13


def recibidas_atendidas(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    mayor = max(serie, key=lambda pt: pt[1].recibidas)
    mejor = max(serie, key=lambda pt: pt[1].nivel_atencion or 0)
    peor = min(serie, key=lambda pt: pt[1].nivel_atencion or 0)
    m = s.mes
    frase = f"En {s.nombre.lower()}, el mes de más {s.canal.recibidas} fue {_etiqueta(mayor[0], serie)} ({entero(mayor[1].recibidas)})"
    if mejor[0] != peor[0]:
        frase += (
            f"; el nivel de atención fue más alto en {_etiqueta(mejor[0], serie)} ({porcentaje(mejor[1].nivel_atencion)}) y más bajo en "
            f"{_etiqueta(peor[0], serie)} ({porcentaje(peor[1].nivel_atencion)})"
        )
    if m:
        frase += (
            f". En {_etiqueta(c.periodo, serie)} se recibieron {entero(m.recibidas)} y se atendieron {entero(m.atendidas)} "
            f"({porcentaje(m.nivel_atencion)})"
        )
    elif s.ultimo_periodo:
        frase += f". El canal no tiene datos en {_mes(c)}; su último mes con datos es {mes_y_anio(s.ultimo_periodo)}"
    return frase + "."


def servicio(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    mejor = max(serie, key=lambda pt: pt[1].nivel_servicio or 0)
    peor = min(serie, key=lambda pt: pt[1].nivel_servicio or 0)
    frase = (
        f"Las transacciones NS son las contestadas antes del tiempo objetivo. El nivel de servicio de {s.nombre.lower()} fue más alto en "
        f"{_etiqueta(mejor[0], serie)} ({porcentaje(mejor[1].nivel_servicio)})"
    )
    if peor[0] != mejor[0]:
        frase += f" y más bajo en {_etiqueta(peor[0], serie)} ({porcentaje(peor[1].nivel_servicio)})"
    if s.mes:
        frase += (
            f"; en {_etiqueta(c.periodo, serie)}, {entero(s.mes.en_nivel_servicio)} de {entero(s.mes.recibidas)} "
            f"({porcentaje(s.mes.nivel_servicio)})"
        )
    return frase + "."


def niveles_canal(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    brechas = [(p, (t.nivel_atencion or 0) - (t.nivel_servicio or 0)) for p, t in serie]
    mayor = max(brechas, key=lambda x: x[1])
    frase = (
        "Las dos líneas se leen juntas: la distancia entre el nivel de atención y el de servicio es la parte que se atendió con espera. "
        f"En {s.nombre.lower()} esa distancia fue mayor en {_etiqueta(mayor[0], serie)} ({decimal(mayor[1] * 100, 2)} pp)"
    )
    if s.mes:
        brecha = ((s.mes.nivel_atencion or 0) - (s.mes.nivel_servicio or 0)) * 100
        if mayor[0] != c.periodo:
            frase += f" y en {_etiqueta(c.periodo, serie)} fue de {decimal(brecha, 2)} pp, con un abandono de {porcentaje(s.mes.nivel_abandono)}"
        else:
            frase += f", con un abandono de {porcentaje(s.mes.nivel_abandono)}"
    return frase + ". La tabla trae las cifras de cada mes."


def abandonos(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    mayor = max(serie, key=lambda pt: pt[1].abandonadas)
    peor = max(serie, key=lambda pt: pt[1].nivel_abandono or 0)
    total = sum(t.abandonadas for _, t in serie)
    tramo = "el año" if len(s.serie_anio) >= 2 else "los últimos meses con datos"
    frase = (
        f"En {s.nombre.lower()} se abandonaron {entero(total)} interacciones en {tramo}; el mes con más abandonos fue "
        f"{_etiqueta(mayor[0], serie)} ({entero(mayor[1].abandonadas)})"
    )
    if peor[0] != mayor[0]:
        frase += f" y el de mayor nivel de abandono {_etiqueta(peor[0], serie)} ({porcentaje(peor[1].nivel_abandono)})"
    if s.mes:
        frase += (
            f". En {_etiqueta(c.periodo, serie)}: {entero(s.mes.abandonadas)} abandonadas, {porcentaje(s.mes.nivel_abandono)}; "
            "aquí subir es empeorar"
        )
    return frase + "."


def dos_anios_recibidas(s: SerieCanal, c: Calculo) -> str:
    anio, anio_ant = c.anio, c.anio - 1
    actual = {int(p[5:7]): t.recibidas for p, t in s.serie_anio}
    anterior = {int(p[5:7]): t.recibidas for p, t in s.serie_anio_anterior}
    comunes = [m for m in actual if m in anterior]
    if not comunes:
        if not s.serie_anio:
            return f"{s.nombre} no tiene datos en {anio}."
        if len(s.serie_anio) == 1:
            p0, t0 = s.serie_anio[0]
            return (
                f"No hay meses de {anio_ant} con datos para comparar; {anio} empieza con {nombre_mes(p0)}, con {entero(t0.recibidas)} "
                f"{s.canal.recibidas}."
            )
        mayor = max(s.serie_anio, key=lambda pt: pt[1].recibidas)
        return (
            f"No hay meses de {anio_ant} con datos para comparar; en {anio} el mes de más {s.canal.recibidas} fue "
            f"{nombre_mes(mayor[0])} ({entero(mayor[1].recibidas)})."
        )
    arriba = [m for m in comunes if actual[m] > anterior[m]]
    cuantos = "ninguno" if not arriba else str(len(arriba))
    verbo = "superó" if len(arriba) == 1 else "superaron"
    frase = f"De los {len(comunes)} meses de {anio} con un par en {anio_ant}, {cuantos} {verbo} al año anterior"
    mayor = max(comunes, key=lambda m: abs(actual[m] - anterior[m]))
    frase += (
        f"; la mayor diferencia fue en {nombre_mes(f'{anio}-{mayor:02d}-01')}: {entero(actual[mayor])} frente a "
        f"{entero(anterior[mayor])} ({variacion(actual[mayor], anterior[mayor])})"
    )
    mes_n = c.mes_numero
    if mes_n in actual and mes_n in anterior:
        frase += f". {mayuscula_inicial(_mes(c))} quedó {variacion(actual[mes_n], anterior[mes_n])} frente a {_mes(c)} de {anio_ant}"
    return frase + "."


def variacion_mensual(s: SerieCanal) -> str:
    serie = s.serie_13
    pares = [
        (serie[i][0], serie[i][1].recibidas, serie[i - 1][1].recibidas, serie[i - 1][0])
        for i in range(1, len(serie))
        if serie[i - 1][1].recibidas
    ]
    if not pares:
        return "No hay dos meses consecutivos con datos para medir la variación."
    mayor_sube = max(pares, key=lambda x: x[1] / x[2])
    mayor_baja = min(pares, key=lambda x: x[1] / x[2])
    frase = (
        f"La mayor subida de un mes al siguiente fue en {mes_y_anio(mayor_sube[0])} ({variacion(mayor_sube[1], mayor_sube[2])}) y la mayor "
        f"caída en {mes_y_anio(mayor_baja[0])} ({variacion(mayor_baja[1], mayor_baja[2])})"
    )
    if mayor_sube[1] / mayor_sube[2] - 1 > ATIPICO:
        frase += (
            f"; esa subida se explica por un mes anterior atípico, {mes_y_anio(mayor_sube[3])}, con apenas {entero(mayor_sube[2])} "
            f"{s.canal.recibidas} en la fuente, y su barra va recortada para no aplastar a las demás"
        )
    ultimo = pares[-1]
    frase += (
        f". El último mes con datos varió {variacion(ultimo[1], ultimo[2])} frente al anterior con datos. Cada barra compara el mes con su "
        "mes anterior con datos del canal, así que los meses sin servicio no cuentan."
    )
    return frase


def media_movil(s: SerieCanal) -> str:
    serie = [(p, t.recibidas, s.media_movil.get(p)) for p, t in s.serie_13 if s.media_movil.get(p) is not None]
    if not serie:
        return "Todavía no hay tres meses anteriores con datos para calcular la media móvil."
    arriba = [x for x in serie if x[1] > x[2]]
    p, v, mm = serie[-1]
    frase = (
        f"De los {len(serie)} meses con media móvil, {len(arriba)} quedaron por encima de ella. En {mes_y_anio(p)}, {entero(v)} "
        f"{s.canal.recibidas} frente a una media de {entero(round(mm))} de los tres meses anteriores ({variacion(v, mm)})"
    )
    return (
        frase
        + ". La media móvil suaviza los picos y dice si el mes está por encima o por debajo de su tendencia reciente."
    )


NIVELES = {
    "nivel_atencion": ("el nivel de atención", False),
    "nivel_servicio": ("el nivel de servicio", False),
    "nivel_abandono": ("el nivel de abandono", True),
    "resolucion": ("la resolución", False),
    "efectividad": ("la efectividad", False),
}


def nivel_anual(s: SerieCanal, c: Calculo, campo: str) -> str:
    nombre, menor_mejor = NIVELES[campo]
    anio, anio_ant = c.anio, c.anio - 1
    actual = {int(p[5:7]): getattr(t, campo) for p, t in s.serie_anio if getattr(t, campo) is not None}
    anterior = {int(p[5:7]): getattr(t, campo) for p, t in s.serie_anio_anterior if getattr(t, campo) is not None}
    comunes = [m for m in actual if m in anterior]
    if not comunes:
        if not actual:
            return f"{s.nombre} no tiene {nombre} en {anio}."
        if len(actual) == 1:
            ((m, v),) = actual.items()
            return (
                f"No hay meses de {anio_ant} con datos para comparar; {anio} empieza con {nombre_mes(f'{anio}-{m:02d}-01')}, con "
                f"{nombre} de {s.nombre.lower()} en {porcentaje(v)}."
            )
        mejor = max(actual.items(), key=lambda kv: kv[1] * (-1 if menor_mejor else 1))
        return (
            f"No hay meses de {anio_ant} para comparar; en {anio} {nombre} de {s.nombre.lower()} fue {'más bajo' if menor_mejor else 'más alto'} "
            f"en {nombre_mes(f'{anio}-{mejor[0]:02d}-01')} ({porcentaje(mejor[1])})."
        )
    mejores = [m for m in comunes if (actual[m] < anterior[m]) == menor_mejor and actual[m] != anterior[m]]
    cuantos = (
        "ninguno"
        if not mejores
        else numero_en_palabras(len(mejores), femenino=False)
        if len(mejores) <= 10
        else str(len(mejores))
    )
    frase = f"En {cuantos} de los {len(comunes)} meses comparables, {nombre} de {anio} fue mejor que el de {anio_ant}"
    mayor = max(comunes, key=lambda m: abs(actual[m] - anterior[m]))
    frase += (
        f"; la mayor diferencia fue en {nombre_mes(f'{anio}-{mayor:02d}-01')}: {porcentaje(actual[mayor])} frente a "
        f"{porcentaje(anterior[mayor])} ({puntos(actual[mayor] - anterior[mayor])})"
    )
    mes_n = c.mes_numero
    if mes_n in actual and mes_n in anterior:
        frase += f". En {_mes(c)}: {porcentaje(actual[mes_n])} frente a {porcentaje(anterior[mes_n])} ({puntos(actual[mes_n] - anterior[mes_n])})"
    if menor_mejor:
        frase += "; aquí bajar es mejorar"
    return frase + "."


def chatbot_transacciones(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    mayor = max(serie, key=lambda pt: pt[1].recibidas)
    frase = (
        f"El chatbot tuvo más transacciones en {_etiqueta(mayor[0], serie)} ({entero(mayor[1].recibidas)}, con {entero(mayor[1].preguntas)} "
        "conversaciones)"
    )
    if s.mes:
        frase += (
            f"; en {_etiqueta(c.periodo, serie)} fueron {entero(s.mes.recibidas)} transacciones y {entero(s.mes.preguntas)} conversaciones, "
            f"con una resolución de {porcentaje(s.mes.resolucion)}"
        )
    return (
        frase
        + ". El bot anterior funcionó hasta noviembre de 2025 y el nuevo está cargado desde abril de 2026; los meses sin servicio no aparecen."
    )


def chatbot_resueltas(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    mejor = max(serie, key=lambda pt: pt[1].resolucion or 0)
    peor = min(serie, key=lambda pt: pt[1].resolucion or 0)
    frase = f"La resolución fue más alta en {_etiqueta(mejor[0], serie)} ({porcentaje(mejor[1].resolucion)})"
    if peor[0] != mejor[0]:
        frase += f" y más baja en {_etiqueta(peor[0], serie)} ({porcentaje(peor[1].resolucion)})"
    if s.mes:
        frase += (
            f". En {_etiqueta(c.periodo, serie)}, {entero(s.mes.preguntas_resueltas)} chats se resolvieron sin agente y "
            f"{entero(s.mes.preguntas_no_resueltas)} pasaron a uno"
        )
    return frase + "."


def callback_efectivas(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    mayor = max(serie, key=lambda pt: pt[1].recibidas)
    mejor = max(serie, key=lambda pt: pt[1].efectividad or 0)
    frase = (
        f"{s.nombre} tuvo más {s.canal.recibidas} en {_etiqueta(mayor[0], serie)} ({entero(mayor[1].recibidas)}) y su mejor efectividad en "
        f"{_etiqueta(mejor[0], serie)} ({porcentaje(mejor[1].efectividad)})"
    )
    if s.mes:
        frase += (
            f"; en {_etiqueta(c.periodo, serie)} se lograron {entero(s.mes.atendidas)} llamadas efectivas de {entero(s.mes.recibidas)} "
            f"({porcentaje(s.mes.efectividad)})"
        )
    return frase + ". La fuente de este canal no trae transacciones NS, así que no hay nivel de servicio."


def callback_no_efectivas(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    peor = max(serie, key=lambda pt: pt[1].nivel_abandono or 0)
    total = sum(t.abandonadas for _, t in serie)
    tramo = "el año" if len(s.serie_anio) >= 2 else "los últimos meses con datos"
    frase = (
        f"En {tramo} hubo {entero(total)} llamadas no efectivas en {s.nombre.lower()}; la tasa fue más alta en {_etiqueta(peor[0], serie)} "
        f"({porcentaje(peor[1].nivel_abandono)})"
    )
    if s.mes:
        frase += (
            f" y en {_etiqueta(c.periodo, serie)} fue de {porcentaje(s.mes.nivel_abandono)} ({entero(s.mes.abandonadas)} de "
            f"{entero(s.mes.recibidas)})"
        )
    return frase + "; aquí subir es empeorar."


def presencial(s: SerieCanal, c: Calculo) -> str:
    serie = _serie_texto(s)
    mayor = max(serie, key=lambda pt: pt[1].recibidas)
    menor = min(serie, key=lambda pt: pt[1].recibidas)
    frase = (
        f"La atención presencial tuvo su mes más alto en {_etiqueta(mayor[0], serie)} ({entero(mayor[1].recibidas)} atenciones) y el más "
        f"bajo en {_etiqueta(menor[0], serie)} ({entero(menor[1].recibidas)})"
    )
    if s.acumulado.meses:
        frase += f"; el promedio mensual de {c.anio} es de {decimal(s.acumulado.promedio_mensual, 1)}"
    if s.mes:
        lado = "por encima" if s.mes.recibidas >= (s.acumulado.promedio_mensual or 0) else "por debajo"
        frase += f" y {_etiqueta(c.periodo, serie)} quedó {lado} de él con {entero(s.mes.recibidas)}"
    return frase + "."


def anexo(c: Calculo) -> str:
    return (
        f"Una fila por canal con lo recibido en cada mes de {c.anio} y el acumulado; la fila de total suma todos los canales. Son las "
        "cifras con las que se dibujaron los gráficos de este informe."
    )
