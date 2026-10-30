"""La narrativa bajo cada gráfico y cada tabla del Informe de Trámites: lo que muestra la pieza, dicho con las cifras
del mes, en tercera persona y sin rótulo. Cada función recibe el cálculo o la serie de un tipo y devuelve un párrafo;
nada se escribe a mano para un mes concreto. Cuando la serie cruza dos años (los últimos trece meses con datos), los
meses se nombran con su año para que no haya dos «enero»."""

from __future__ import annotations

from men_platform.publicaciones.datos_tramites import PARETO, Calculo, Serie, cuantos_para
from men_platform.publicaciones.texto_es import (
    decimal,
    entero,
    lista_en_prosa,
    mayuscula_inicial,
    mes_y_anio,
    nombre_mes,
    numero_en_palabras,
    porcentaje,
    variacion,
)


def _mes(c: Calculo) -> str:
    return nombre_mes(c.periodo)


def _etiqueta(p: str, serie: list) -> str:
    """«enero» si toda la serie es del mismo año; «enero de 2024» si cruza años."""
    return nombre_mes(p) if len({q[:4] for q, _ in serie}) <= 1 else mes_y_anio(p)


def _bajo(s: Serie) -> str:
    return s.nombre.lower() if s.tramite is None or s.tramite.fuente != "pqrs" else s.nombre


def _cuantos(n: int) -> str:
    """«ninguno», «uno», «dos»… «diez» o la cifra, para contar meses dentro de una frase."""
    if n == 0:
        return "ninguno"
    if n == 1:
        return "uno"
    return numero_en_palabras(n, femenino=False)


def _serie_texto(s: Serie) -> list[tuple[str, int]]:
    return s.serie_anio if len(s.serie_anio) >= 2 else s.serie_13


# --- 5.1 resumen del mes ----------------------------------------------------------------------------------------


def tabla_tipos(c: Calculo) -> str:
    tipos = c.tipos_del_mes
    total = c.total.mes or 0
    mayor = tipos[0]
    frase = (
        f"La tabla reparte los {entero(total)} trámites de {_mes(c)} entre los {numero_en_palabras(len(tipos), femenino=False)} "
        f"tipos con datos: {_bajo(mayor)} es el principal, con {entero(mayor.mes)} ({porcentaje(c.participacion(mayor), 1)} del total)"
    )
    if len(tipos) > 1:
        segundo = tipos[1]
        frase += f", seguido de {_bajo(segundo)} ({entero(segundo.mes)}, {porcentaje(c.participacion(segundo), 1)})"
        menor = tipos[-1]
        frase += f"; el de menor volumen fue {_bajo(menor)}, con {entero(menor.mes)}"
    frase += (
        ". El acumulado suma las participaciones de mayor a menor y el promedio mensual es el de cada tipo sobre sus meses con datos "
        f"de {c.anio}, para saber si el mes estuvo por encima o por debajo de lo habitual."
    )
    return frase


def barras_tipos(c: Calculo) -> str:
    tipos = c.tipos_del_mes
    mayor = tipos[0]
    frase = (
        f"Las barras ponen en escala lo que la tabla dice en cifras: {_bajo(mayor)} sumó {entero(mayor.mes)} trámites"
    )
    if len(tipos) > 1:
        segundo = tipos[1]
        veces = (mayor.mes or 0) / segundo.mes if segundo.mes else None
        frase += f", {decimal(veces, 1)} veces los del segundo tipo ({_bajo(segundo)})" if veces else ""
    arriba = [s for s in tipos if s.promedio_mensual and (s.mes or 0) > s.promedio_mensual]
    if arriba and len(tipos) > 1:
        frase += (
            f". {mayuscula_inicial(lista_en_prosa([_bajo(s) for s in arriba]))} "
            f"{'quedó' if len(arriba) == 1 else 'quedaron'} por encima de su promedio mensual de {c.anio}"
        )
    return frase + "."


def treemap(c: Calculo) -> str:
    tipos = c.tipos_del_mes
    mayor = tipos[0]
    dos = sum(c.participacion(s) or 0 for s in tipos[:2])
    frase = (
        f"Cada tipo ocupa un área proporcional a su volumen en {_mes(c)}: {_bajo(mayor)} cubre el "
        f"{porcentaje(c.participacion(mayor), 1)} del cuadro"
    )
    if len(tipos) > 1:
        frase += f" y, con {_bajo(tipos[1])}, el {porcentaje(dos, 1)}"
    pequenos = [s for s in tipos if (c.participacion(s) or 0) < 0.02]
    if pequenos:
        frase += f"; {lista_en_prosa([_bajo(s) for s in pequenos])} {'pesa' if len(pequenos) == 1 else 'pesan'} menos del 2 % cada uno"
    return frase + ". La participación dice cuánto pesa cada trámite en el mes, no cuánto crece."


def pareto(c: Calculo) -> str:
    tipos = c.tipos_del_mes
    n = cuantos_para([s.mes or 0 for s in tipos])
    nombres = [_bajo(s) for s in tipos[:n]]
    acumulado = sum(c.participacion(s) or 0 for s in tipos[:n])
    frase = (
        f"{mayuscula_inicial(numero_en_palabras(n, femenino=False))} de los {numero_en_palabras(len(tipos), femenino=False)} tipos "
        f"({lista_en_prosa(nombres)}) {'explica' if n == 1 else 'explican'} el {porcentaje(acumulado, 1)} de los trámites de {_mes(c)}, "
        f"por encima de la guía del {porcentaje(PARETO, 0)}"
    )
    resto = len(tipos) - n
    if resto > 0:
        frase += (
            f"; los otros {numero_en_palabras(resto, femenino=False)} reúnen el {porcentaje(1 - acumulado, 1)} restante"
        )
    return frase + ". La línea es la participación acumulada de mayor a menor."


# --- 5.2 comparación con el mes anterior ------------------------------------------------------------------------


def comparacion_mes_anterior(c: Calculo) -> str:
    t = c.total
    if t.mes_anterior is None or t.mes is None:
        return f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico: no hay un mes anterior con el cual comparar."
    subidas = []
    bajadas = []
    for s in c.tipos:
        if s.mes and s.mes_anterior and s.periodo_anterior == t.periodo_anterior:
            v = variacion(s.mes, s.mes_anterior)
            (subidas if s.mes >= s.mes_anterior else bajadas).append(f"{_bajo(s)} ({v})")
    frase = (
        f"Frente a {nombre_mes(t.periodo_anterior)}, el total general pasó de {entero(t.mes_anterior)} a {entero(t.mes)} "
        f"({variacion(t.mes, t.mes_anterior)})"
    )
    if subidas:
        frase += f"; subieron {lista_en_prosa(subidas)}"
    if bajadas:
        frase += f"; bajaron {lista_en_prosa(bajadas)}"
    sin_mes = [
        s for s in c.tipos if s.mes is None and s.mes_anterior is not None and s.periodo_anterior == t.periodo_anterior
    ]
    if sin_mes:
        frase += f". {mayuscula_inicial(lista_en_prosa([_bajo(s) for s in sin_mes]))} no registró trámites en {_mes(c)}"
    return frase + "."


# --- 5.3 evolución del año --------------------------------------------------------------------------------------


def total_por_mes(c: Calculo) -> str:
    t = c.total
    serie = t.serie_anio
    promedio = t.promedio_mensual or 0
    mayor, menor = t.mes_mayor, t.mes_menor
    arriba = [p for p, v in serie if v > promedio]
    frase = (
        f"En {c.anio} el total general fue mayor en {nombre_mes(mayor[0])} ({entero(mayor[1])} trámites) y menor en "
        f"{nombre_mes(menor[0])} ({entero(menor[1])}); el promedio mensual de los {numero_en_palabras(len(serie), femenino=False)} "
        f"meses con datos es de {decimal(promedio, 1)}"
    )
    if t.mes is not None:
        lado = "por encima" if t.mes >= promedio else "por debajo"
        frase += f" y {_mes(c)} quedó {lado} de él, con {entero(t.mes)} ({variacion(t.mes, promedio)})"
    cuantos = _cuantos(len(arriba))
    frase += f". {mayuscula_inicial(cuantos)} de los {_cuantos(len(serie))} meses {'superó' if len(arriba) == 1 else 'superaron'} el promedio."
    return frase


def apiladas_por_tipo(c: Calculo) -> str:
    serie = c.tipo_por_mes
    totales = [(p, sum(v for _, v in lista)) for p, lista in serie]
    mayor = max(totales, key=lambda x: x[1])
    menor = min(totales, key=lambda x: x[1])
    principal = c.tipos_del_anio[0]
    frase = (
        f"El tipo de mayor volumen del año va abajo: {_bajo(principal)} es la base de todas las columnas, con "
        f"{entero(principal.acumulado)} trámites en {c.anio} ({porcentaje(c.participacion_anio(principal), 1)} del acumulado). "
        f"El total fue más alto en {nombre_mes(mayor[0])} ({entero(mayor[1])}) y más bajo en {nombre_mes(menor[0])} ({entero(menor[1])})"
    )
    if principal.serie_anio:
        p_mayor = max(principal.serie_anio, key=lambda pv: pv[1])
        frase += f"; el mes más alto de {_bajo(principal)} fue {nombre_mes(p_mayor[0])} ({entero(p_mayor[1])})"
    return frase + "."


def mezcla(c: Calculo) -> str:
    serie = c.tipo_por_mes
    p, lista = serie[-1]
    total = sum(v for _, v in lista) or 1
    partes = sorted(lista, key=lambda tv: -tv[1])
    primero = partes[0]
    frase = f"En {nombre_mes(p)}, {primero[0].nombre.lower() if primero[0].fuente != 'pqrs' else primero[0].nombre} fue el {porcentaje(primero[1] / total, 1)} de todos los trámites"
    p0, lista0 = serie[0]
    if p0 != p:
        total0 = sum(v for _, v in lista0) or 1
        parte0 = next((v / total0 for t, v in lista0 if t.id == primero[0].id), None)
        if parte0 is not None:
            frase += f", frente al {porcentaje(parte0, 1)} de {nombre_mes(p0)}"
    if len(partes) > 1:
        segundo = partes[1]
        frase += f"; {segundo[0].nombre.lower() if segundo[0].fuente != 'pqrs' else segundo[0].nombre} fue el {porcentaje(segundo[1] / total, 1)}"
    return (
        frase
        + ". La mezcla dice cuánto pesa cada tipo, no cuánto crece: un tipo puede ganar parte mientras todos bajan."
    )


# --- 5.4 volumen general ----------------------------------------------------------------------------------------


def dos_anios(s: Serie, c: Calculo) -> str:
    anio, anio_ant = c.anio, c.anio - 1
    actual = {int(p[5:7]): v for p, v in s.serie_anio}
    anterior = {int(p[5:7]): v for p, v in s.serie_anio_anterior}
    comunes = [m for m in actual if m in anterior]
    que = "trámites" if s.tramite is None else f"trámites de {_bajo(s)}"
    if not comunes:
        if not s.serie_anio:
            return f"{s.nombre} no tiene datos en {anio}."
        if len(s.serie_anio) == 1:
            p0, v0 = s.serie_anio[0]
            return f"No hay meses de {anio_ant} con datos para comparar; {anio} empieza con {nombre_mes(p0)}, con {entero(v0)} {que}."
        mayor = max(s.serie_anio, key=lambda pv: pv[1])
        return (
            f"No hay meses de {anio_ant} con datos para comparar; en {anio} el mes de más {que} fue {nombre_mes(mayor[0])} "
            f"({entero(mayor[1])})."
        )
    arriba = [m for m in comunes if actual[m] > anterior[m]]
    cuantos = _cuantos(len(arriba))
    verbo = "superó" if len(arriba) == 1 else "superaron"
    frase = (
        f"De los {_cuantos(len(comunes))} meses de {anio} con un par en {anio_ant}, {cuantos} {verbo} al año anterior"
    )
    mayor = max(comunes, key=lambda m: abs(actual[m] - anterior[m]))
    frase += (
        f"; la mayor diferencia fue en {nombre_mes(f'{anio}-{mayor:02d}-01')}: {entero(actual[mayor])} frente a "
        f"{entero(anterior[mayor])} ({variacion(actual[mayor], anterior[mayor])})"
    )
    mes_n = c.mes_numero
    if mes_n in actual and mes_n in anterior:
        frase += f". {mayuscula_inicial(_mes(c))} quedó {variacion(actual[mes_n], anterior[mes_n])} frente a {_mes(c)} de {anio_ant}"
    if s.acumulado_anterior and s.meses_acumulado >= 2:
        frase += (
            f"; el acumulado de los mismos meses pasó de {entero(s.acumulado_anterior)} a {entero(s.acumulado)} "
            f"({variacion(s.acumulado, s.acumulado_anterior)})"
        )
    return frase + "."


def variacion_mensual(s: Serie) -> str:
    serie = s.serie_13
    pares = [
        (serie[i][0], serie[i][1], serie[i - 1][1], serie[i - 1][0]) for i in range(1, len(serie)) if serie[i - 1][1]
    ]
    if not pares:
        return "No hay dos meses consecutivos con datos para medir la variación."
    mayor_sube = max(pares, key=lambda x: x[1] / x[2])
    mayor_baja = min(pares, key=lambda x: x[1] / x[2])
    frase = (
        f"La mayor subida de un mes al siguiente fue en {mes_y_anio(mayor_sube[0])} ({variacion(mayor_sube[1], mayor_sube[2])}) y la mayor "
        f"caída en {mes_y_anio(mayor_baja[0])} ({variacion(mayor_baja[1], mayor_baja[2])})"
    )
    ultimo = pares[-1]
    frase += (
        f". El último mes con datos varió {variacion(ultimo[1], ultimo[2])} frente al anterior. Cada barra compara el mes con el "
        "inmediatamente anterior; enero se compara con diciembre del año anterior."
    )
    return frase


def media_movil(s: Serie) -> str:
    serie = [(p, v, s.media_movil.get(p)) for p, v in s.serie_13 if s.media_movil.get(p) is not None]
    if not serie:
        return "Todavía no hay tres meses anteriores con datos para calcular la media móvil."
    arriba = [x for x in serie if x[1] > x[2]]
    p, v, mm = serie[-1]
    frase = (
        f"De los {_cuantos(len(serie))} meses con media móvil, {_cuantos(len(arriba))} {'quedó' if len(arriba) == 1 else 'quedaron'} por encima de ella. En {mes_y_anio(p)}, {entero(v)} "
        f"trámites frente a una media de {entero(round(mm))} de los tres meses anteriores ({variacion(v, mm)})"
    )
    return (
        frase
        + ". La media móvil suaviza los picos y dice si el mes está por encima o por debajo de su tendencia reciente."
    )


# --- 5.5 cada tipo frente al año anterior -----------------------------------------------------------------------


def tipos_dos_anios(c: Calculo) -> str:
    anio, anio_ant = c.anio, c.anio - 1
    tipos = [s for s in c.tipos_del_anio if s.acumulado_anterior]
    if not tipos:
        return f"Ningún tipo de trámite tiene datos en los mismos meses de {anio_ant}: no hay con qué comparar el acumulado de {anio}."
    crecen = sorted([s for s in tipos if s.acumulado > (s.acumulado_anterior or 0)], key=lambda s: -s.acumulado)
    caen = sorted([s for s in tipos if s.acumulado < (s.acumulado_anterior or 0)], key=lambda s: -s.acumulado)
    frase = ("Con el mismo mes" if c.total.meses_acumulado == 1 else "Con los mismos meses") + " en los dos años, "
    if crecen:
        frase += (
            f"{'creció' if len(crecen) == 1 else 'crecieron'} "
            f"{lista_en_prosa([f'{_bajo(s)} ({variacion(s.acumulado, s.acumulado_anterior)})' for s in crecen])}"
        )
    if caen:
        frase += ("; " if crecen else "") + (
            f"{'bajó' if len(caen) == 1 else 'bajaron'} "
            f"{lista_en_prosa([f'{_bajo(s)} ({variacion(s.acumulado, s.acumulado_anterior)})' for s in caen])}"
        )
    nuevos = [s for s in c.tipos_del_anio if not s.acumulado_anterior]
    if nuevos:
        frase += f". {mayuscula_inicial(lista_en_prosa([_bajo(s) for s in nuevos]))} no {'tenía' if len(nuevos) == 1 else 'tenían'} datos en esos meses de {anio_ant}"
    return frase + "."


# --- por tipo ---------------------------------------------------------------------------------------------------


def tipo_mes_a_mes(s: Serie, c: Calculo) -> str:
    serie = _serie_texto(s)
    mayor = max(serie, key=lambda pv: pv[1])
    menor = min(serie, key=lambda pv: pv[1])
    es_anio = len(s.serie_anio) >= 2
    promedio = s.promedio_mensual if es_anio else (sum(v for _, v in serie) / len(serie) if serie else None)
    frase = (
        f"{mayuscula_inicial(_bajo(s))} tuvo su mes más alto en {_etiqueta(mayor[0], serie)} ({entero(mayor[1])}) y el más bajo en "
        f"{_etiqueta(menor[0], serie)} ({entero(menor[1])})"
    )
    if promedio:
        frase += (
            f"; el promedio mensual {'de ' + str(c.anio) if es_anio else 'de esos meses'} es de {decimal(promedio, 1)}"
        )
    if s.mes is not None and promedio:
        lado = "por encima" if s.mes >= promedio else "por debajo"
        frase += (
            f" y {_etiqueta(c.periodo, serie)} quedó {lado} de él con {entero(s.mes)} ({variacion(s.mes, promedio)})"
        )
    elif s.ultimo_periodo and s.ultimo_periodo < c.periodo:
        frase += f". El tipo no tiene datos en {_mes(c)}; su último mes con datos es {mes_y_anio(s.ultimo_periodo)}"
    return frase + "."


def anexo(c: Calculo) -> str:
    return (
        f"Una fila por mes de {c.anio} con lo gestionado en cada tipo de trámite y el total general; la última fila acumula el "
        "año. Son las cifras con las que se dibujaron los gráficos de este informe."
    )
