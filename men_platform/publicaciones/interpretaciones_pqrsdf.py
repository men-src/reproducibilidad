"""La interpretación de cada gráfico y de cada tabla del Informe General de PQRSDF: un párrafo corto, en tercera persona,
que dice qué muestra la pieza y qué significa para la entidad. Todo sale de las cifras del mes."""

from __future__ import annotations

from men_platform.publicaciones.datos_pqrsdf import Calculo, Totales
from men_platform.publicaciones.texto_es import (
    capitalizar,
    con_articulo,
    decimal,
    entero,
    lista_en_prosa,
    mayuscula_inicial,
    mes_y_anio,
    mes_y_anio_siguiente,
    nombre_mes,
    nombre_propio,
    numero_en_palabras,
    porcentaje,
    puntos,
    puntos_sin_signo,
    tramo_del_anio,
    variacion,
)


def _volumen(actual: int, anterior: int | None) -> str:
    """«8,76 % mayor» o «3,10 % menor», para seguir a «un volumen»."""
    if not anterior:
        return "sin comparación"
    v = (actual - anterior) / anterior
    if abs(v) < 0.00005:
        return "igual"
    return f"{decimal(abs(v) * 100, 2)} % {'mayor' if v > 0 else 'menor'}"


def _mas_menos(a: float, b: float) -> str:
    return "más" if a > b else ("menos" if a < b else "igual")


def _sube_baja(delta: float | None, sube: str = "subió", baja: str = "bajó", igual: str = "se mantuvo") -> str:
    if delta is None or abs(delta) < 0.00005:
        return igual
    return sube if delta > 0 else baja


def _encima_debajo(valor: float, referencia: float) -> str:
    return "por encima" if valor > referencia else ("por debajo" if valor < referencia else "al nivel")


def _promedio_oportunidad(serie: list[tuple[str, Totales]]) -> float | None:
    radicados = sum(t.radicados for _, t in serie)
    return sum(t.a_tiempo for _, t in serie) / radicados if radicados else None


def _parte(valor: int, total: int) -> float | None:
    return valor / total if total else None


# --- 4.1 estado al corte --------------------------------------------------------------------------------------------


def estados_grafico(c: Calculo) -> str:
    m = c.mes
    cerradas_ext = max(0, m.extemporaneas - m.abiertas_vencidas)
    de_cien = [
        round((x / m.radicados) * 100) if m.radicados else 0 for x in (m.a_tiempo, cerradas_ext, m.abiertas_vencidas)
    ]
    return (
        f"De cada cien PQRSDF gestionadas en {mes_y_anio(c.periodo)}, {de_cien[0]} se respondieron dentro del plazo, {de_cien[1]} se cerraron "
        f"después del vencimiento y {de_cien[2]} eran extemporáneas que seguían abiertas al corte. La franja azul es la oportunidad del mes y la roja, la brecha; "
        "la tabla separa, dentro de esa brecha, lo que ya se cerró después del plazo de lo que seguía abierto al corte."
    )


def estados_tabla(c: Calculo) -> str:
    m = c.mes
    if m.abiertas_vencidas:
        parte = _parte(m.abiertas_vencidas, m.extemporaneas)
        cola = (
            f"De esas extemporáneas, {entero(m.abiertas_vencidas)} ({porcentaje(parte, 1)}) seguían abiertas al corte: ya cuentan como respuestas fuera "
            "de plazo y cada día que siguen sin cerrarse elevan el retraso promedio del mes."
        )
    else:
        cola = "Al corte todas las extemporáneas estaban cerradas, de modo que la cifra del mes es definitiva."
    return (
        f"En cifras, las {entero(m.a_tiempo)} respuestas a tiempo ({porcentaje(m.oportunidad)}) son el resultado del mes y las "
        f"{entero(m.extemporaneas)} extemporáneas ({porcentaje(m.tasa_extemporaneas)}) la brecha. {cola}"
    )


def indicadores_tabla(c: Calculo) -> str:
    m, ant, mismo, acu, acu_ant = c.mes, c.mes_anterior, c.mismo_mes_anterior, c.acumulado, c.acumulado_anterior
    partes = []
    if ant:
        d = (m.oportunidad or 0) - (ant.oportunidad or 0)
        partes.append(
            f"Frente al mes anterior, el volumen gestionado {'creció' if m.radicados > ant.radicados else 'cayó'} {variacion(m.radicados, ant.radicados).lstrip('+−')} "
            f"y la oportunidad {_sube_baja(d)} {puntos_sin_signo(d)}"
        )
    if mismo:
        d = (m.oportunidad or 0) - (mismo.oportunidad or 0)
        partes.append(
            f"frente a {nombre_mes(c.periodo)} de {c.anio - 1}, la oportunidad {_sube_baja(d)} {puntos_sin_signo(d)} con un volumen {_volumen(m.radicados, mismo.radicados)}"
        )
    texto = "; ".join(partes) + "." if partes else ""
    if acu_ant:
        d = (acu.oportunidad or 0) - (acu_ant.oportunidad or 0)
        texto += (
            f" En el acumulado del año la oportunidad ({porcentaje(acu.oportunidad)}) está {decimal(abs(d) * 100, 2)} pp "
            f"{'por encima' if d >= 0 else 'por debajo'} de la del mismo tramo de {c.anio - 1}, así que el mes debe leerse junto con esa tendencia."
        )
    return texto


# --- 4.2 comparación con el mes anterior ----------------------------------------------------------------------------


def mes_anterior_tabla(c: Calculo) -> str:
    m, ant = c.mes, c.mes_anterior
    if not ant:
        return f"La comparación con el mes anterior empieza en el informe de {mes_y_anio_siguiente(c.periodo)}."
    mes_ant = nombre_mes(c.periodo_anterior_str())
    d_at, d_ext = m.a_tiempo - ant.a_tiempo, m.extemporaneas - ant.extemporaneas
    d_op = (m.oportunidad or 0) - (ant.oportunidad or 0)
    d_dias = (m.promedio_dias_gestion or 0) - (ant.promedio_dias_gestion or 0)
    return (
        f"En {mes_y_anio(c.periodo)} se gestionaron {entero(m.radicados)} PQRSDF, {entero(abs(m.radicados - ant.radicados))} "
        f"{_mas_menos(m.radicados, ant.radicados)} que en {mes_ant} ({variacion(m.radicados, ant.radicados)}). Las respuestas a tiempo "
        f"{'aumentaron' if d_at >= 0 else 'disminuyeron'} en {entero(abs(d_at))} y las extemporáneas {'aumentaron' if d_ext >= 0 else 'disminuyeron'} en "
        f"{entero(abs(d_ext))}, de modo que la oportunidad pasó de {porcentaje(ant.oportunidad)} a {porcentaje(m.oportunidad)} ({puntos(d_op)}). "
        f"El tiempo promedio de gestión {_sube_baja(d_dias, 'subió', 'bajó')} de {decimal(ant.promedio_dias_gestion, 1)} a {decimal(m.promedio_dias_gestion, 1)} días hábiles."
    )


def mes_anterior_grafico(c: Calculo) -> str:
    m, ant = c.mes, c.mes_anterior
    if not ant:
        return f"La comparación con el mes anterior empieza en el informe de {mes_y_anio_siguiente(c.periodo)}."
    mes_ant = nombre_mes(c.periodo_anterior_str())
    mejor = (m.oportunidad or 0) >= (ant.oportunidad or 0)
    return (
        f"Las barras de {nombre_mes(c.periodo)} {'superan' if m.radicados > ant.radicados else 'quedan por debajo de'} las de {mes_ant} en el total gestionado; "
        f"lo que importa es la proporción: la barra de extemporáneas {'pesa menos' if mejor else 'pesa más'} dentro del total que el mes anterior, "
        f"y por eso la oportunidad {'mejora' if mejor else 'empeora'}."
    )


def cambio_dependencias_tabla(
    c: Calculo,
    mejoras: list[tuple[str, float, Totales, Totales]],
    retrocesos: list[tuple[str, float, Totales, Totales]],
) -> str:
    mes_ant = nombre_mes(c.periodo_anterior_str())
    partes = []
    if mejoras:
        partes.append(
            f"las mayores mejoras frente a {mes_ant} se dieron en {lista_en_prosa([f'{con_articulo(k)} ({puntos(d)})' for k, d, _, _ in mejoras[:3]])}"
        )
    if retrocesos:
        partes.append(
            f"los mayores retrocesos en {lista_en_prosa([f'{con_articulo(k)} ({puntos(d)})' for k, d, _, _ in retrocesos[:3]])}"
        )
    if not partes:
        return "Ninguna dependencia con volumen relevante cambió su oportunidad de forma apreciable frente al mes anterior."
    return (
        f"Entre las dependencias con volumen relevante en ambos meses, {'; '.join(partes)}. Un cambio grande en pocas dependencias explica buena "
        "parte del movimiento del indicador total, así que conviene mirar primero esas áreas."
    )


# --- 4.3 serie de trece meses ----------------------------------------------------------------------------------------


def serie_grafico(c: Calculo) -> str:
    serie = c.serie_13
    maximo = max(serie, key=lambda pt: pt[1].oportunidad or 0)
    minimo = min(serie, key=lambda pt: pt[1].oportunidad or 0)
    previos = [pt for pt in serie if pt[0] != c.periodo]
    promedio = _promedio_oportunidad(previos) or 0
    # racha: cuántos meses seguidos lleva subiendo o bajando
    valores = [t.oportunidad or 0 for _, t in serie]
    racha, direccion = 0, 0
    for i in range(len(valores) - 1, 0, -1):
        d = valores[i] - valores[i - 1]
        s = 1 if d > 0 else (-1 if d < 0 else 0)
        if racha == 0:
            direccion = s
        if s == 0 or s != direccion:
            break
        racha += 1
    racha_texto = ""
    if racha >= 2 and direccion != 0:
        racha_texto = f" El indicador lleva {numero_en_palabras(racha, False)} meses seguidos {'subiendo' if direccion > 0 else 'bajando'}."
    return (
        f"En los últimos trece meses la oportunidad se movió entre {porcentaje(minimo[1].oportunidad)} ({mes_y_anio(minimo[0])}) y "
        f"{porcentaje(maximo[1].oportunidad)} ({mes_y_anio(maximo[0])}). {nombre_mes(c.periodo).capitalize()} de {c.anio} se ubica "
        f"{_encima_debajo(c.mes.oportunidad or 0, promedio)} del promedio de los doce meses anteriores ({porcentaje(promedio)}).{racha_texto}"
    )


def serie_tabla(c: Calculo) -> str:
    serie = c.serie_13
    cambios = []
    for i in range(1, len(serie)):
        cambios.append((serie[i][0], (serie[i][1].oportunidad or 0) - (serie[i - 1][1].oportunidad or 0)))
    mayor = max(cambios, key=lambda x: abs(x[1]))
    mas_ext = max(serie, key=lambda pt: pt[1].extemporaneas)
    mas_vol = max(serie, key=lambda pt: pt[1].radicados)
    return (
        f"La variación mensual más fuerte del periodo fue la de {mes_y_anio(mayor[0])} ({puntos(mayor[1])}). El mes con más extemporáneas fue "
        f"{mes_y_anio(mas_ext[0])} ({entero(mas_ext[1].extemporaneas)}) y el de mayor volumen gestionado, {mes_y_anio(mas_vol[0])} "
        f"({entero(mas_vol[1].radicados)}). Volumen alto y oportunidad baja en el mismo mes señalan presión sobre la capacidad de respuesta."
    )


# --- 4.4 volumen del año ---------------------------------------------------------------------------------------------


def volumen_grafico(c: Calculo) -> str:
    serie = c.serie_anio
    mayor = max(serie, key=lambda pt: pt[1].radicados)
    menor = min(serie, key=lambda pt: pt[1].radicados)
    promedio = sum(t.radicados for _, t in serie) / len(serie)
    return (
        f"El mes de mayor volumen de {c.anio} fue {nombre_mes(mayor[0])} ({entero(mayor[1].radicados)} PQRSDF) y el de menor, {nombre_mes(menor[0])} "
        f"({entero(menor[1].radicados)}). {nombre_mes(c.periodo).capitalize()} ({entero(c.mes.radicados)}) está {_encima_debajo(c.mes.radicados, promedio)} "
        f"del promedio mensual del año ({entero(promedio)}). La parte roja de cada columna es lo que se respondió fuera de plazo."
    )


def volumen_tabla(c: Calculo) -> str:
    acu = c.acumulado
    serie = sorted(c.serie_anio, key=lambda pt: -(pt[1].tasa_extemporaneas or 0))
    peores = serie[:2]
    return (
        f"Las extemporáneas de {tramo_del_anio(c.periodo)} suman {entero(acu.extemporaneas)}, el {porcentaje(acu.tasa_extemporaneas)} de lo gestionado. "
        f"Los meses con mayor tasa de extemporaneidad fueron {lista_en_prosa([f'{nombre_mes(p)} ({porcentaje(t.tasa_extemporaneas)})' for p, t in peores])}. "
        f"El tiempo promedio de gestión del año es de {decimal(acu.promedio_dias_gestion, 1)} días hábiles."
    )


# --- 4.5 comparación con el año anterior ----------------------------------------------------------------------------


def dos_anios_grafico(c: Calculo) -> str:
    anterior = {int(p[5:7]): t for p, t in c.serie_anio_anterior}
    pares = [(p, t, anterior.get(int(p[5:7]))) for p, t in c.serie_anio]
    pares = [(p, t, a) for p, t, a in pares if a]
    if not pares:
        serie = c.serie_anio
        if len(serie) == 1:
            return (
                f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico: la línea empieza aquí, con {porcentaje(serie[0][1].oportunidad)}; "
                f"cada mes nuevo agregará un punto y, desde {c.anio + 1}, la referencia del año anterior."
            )
        mejor = max(serie, key=lambda pt: pt[1].oportunidad or 0)
        peor = min(serie, key=lambda pt: pt[1].oportunidad or 0)
        return (
            f"El histórico empieza en {c.anio}, así que todavía no hay un año anterior como referencia. Entre enero y {nombre_mes(c.periodo)}, el mejor mes fue "
            f"{nombre_mes(mejor[0])} ({porcentaje(mejor[1].oportunidad)}) y el peor {nombre_mes(peor[0])} ({porcentaje(peor[1].oportunidad)}); desde {c.anio + 1} "
            "la línea amarilla mostrará el año anterior."
        )
    debajo = [
        (p, (t.oportunidad or 0) - (a.oportunidad or 0))
        for p, t, a in pares
        if (t.oportunidad or 0) < (a.oportunidad or 0)
    ]
    brecha = min(((p, (t.oportunidad or 0) - (a.oportunidad or 0)) for p, t, a in pares), key=lambda x: x[1])
    mejor = max(((p, (t.oportunidad or 0) - (a.oportunidad or 0)) for p, t, a in pares), key=lambda x: x[1])
    return (
        f"{numero_en_palabras(len(debajo), False).capitalize()} de los {numero_en_palabras(len(pares), False)} meses de {c.anio} con comparación quedaron por debajo del "
        f"mismo mes de {c.anio - 1}. La brecha más amplia fue en {nombre_mes(brecha[0])} ({puntos(brecha[1])}) y el mejor resultado relativo en "
        f"{nombre_mes(mejor[0])} ({puntos(mejor[1])}). La línea amarilla es la referencia del año anterior: cuando la azul la cruza hacia arriba, el mes mejora."
    )


def dos_anios_tabla(c: Calculo) -> str:
    acu, aa = c.acumulado, c.acumulado_anterior
    if not aa:
        return (
            f"El acumulado de {tramo_del_anio(c.periodo)} de {c.anio} es de {entero(acu.radicados)} PQRSDF gestionadas con una oportunidad de "
            f"{porcentaje(acu.oportunidad)}; el histórico empieza en {c.anio}, así que no hay un tramo anterior con el cual compararlo."
        )
    d = (acu.oportunidad or 0) - (aa.oportunidad or 0)
    return (
        f"En el acumulado, la entidad gestionó {entero(acu.radicados)} PQRSDF frente a {entero(aa.radicados)} en el mismo tramo de {c.anio - 1} "
        f"({variacion(acu.radicados, aa.radicados)}), con una oportunidad de {porcentaje(acu.oportunidad)} frente a {porcentaje(aa.oportunidad)} ({puntos(d)}). "
        + (
            "Más volumen con menor oportunidad indica que la demanda creció más rápido que la capacidad de respuesta."
            if d < 0 and acu.radicados > aa.radicados
            else "La entidad sostiene o mejora la oportunidad con el volumen de este año."
            if d >= 0
            else "El volumen bajó y aun así la oportunidad cayó, lo que apunta a causas distintas de la carga de trabajo."
        )
    )


# --- 4.6 a 4.11 distribuciones ----------------------------------------------------------------------------------------


def viceministerio_grafico(c: Calculo) -> str:
    filas = [(k, t) for k, t in c.por_viceministerio if k != "sin viceministerio" and t.radicados]
    if not filas:
        return "No hay viceministerio asociado a las PQRSDF del mes."
    mejor = max(filas, key=lambda kt: kt[1].oportunidad or 0)
    peor = min(filas, key=lambda kt: kt[1].oportunidad or 0)
    return (
        f"{nombre_propio(mejor[0])} tuvo la mayor oportunidad del mes ({porcentaje(mejor[1].oportunidad)}) y {nombre_propio(peor[0])} la menor "
        f"({porcentaje(peor[1].oportunidad)}), una distancia de {decimal(((mejor[1].oportunidad or 0) - (peor[1].oportunidad or 0)) * 100, 2)} pp entre las áreas de primer nivel."
    )


def viceministerio_tabla(c: Calculo) -> str:
    m = c.mes
    filas = [(k, t) for k, t in c.por_viceministerio if t.radicados]
    mayor = max(filas, key=lambda kt: kt[1].radicados)
    mas_ext = max(filas, key=lambda kt: kt[1].extemporaneas)
    return (
        f"{nombre_propio(mayor[0])} concentra el {porcentaje(_parte(mayor[1].radicados, m.radicados), 1)} del volumen gestionado y "
        f"{nombre_propio(mas_ext[0])} el {porcentaje(_parte(mas_ext[1].extemporaneas, m.extemporaneas), 1)} de las extemporáneas "
        f"({entero(mas_ext[1].extemporaneas)}); su tiempo promedio de gestión es de {decimal(mas_ext[1].promedio_dias_gestion, 1)} días hábiles."
    )


def dependencias_grafico(c: Calculo) -> str:
    top = [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"][:10]
    if not top:
        return "No hay dependencias con PQRSDF en el mes."
    mejor = max(top, key=lambda kt: kt[1].oportunidad or 0)
    peor = min(top, key=lambda kt: kt[1].oportunidad or 0)
    al_cien = [nombre_propio(k) for k, t in top if (t.oportunidad or 0) >= 0.9995]
    return (
        f"Entre las diez dependencias de mayor volumen, la mayor oportunidad fue la de {con_articulo(mejor[0])} ({porcentaje(mejor[1].oportunidad)}) y la menor "
        f"la de {con_articulo(peor[0])} ({porcentaje(peor[1].oportunidad)}). "
        + (f"{lista_en_prosa(al_cien)} respondieron a tiempo la totalidad de sus PQRSDF. " if al_cien else "")
        + "Las barras más cortas con volumen alto son las que más pesan en el resultado de la entidad."
    )


def dependencias_tabla(c: Calculo) -> str:
    m = c.mes
    top = [(k, t) for k, t in c.por_dependencia if k != "sin dependencia"][:15]
    acumulado = dict(c.por_dependencia_acumulado)
    parte = _parte(sum(t.radicados for _, t in top), m.radicados)
    mejoran = [
        nombre_propio(k)
        for k, t in top
        if k in acumulado and (t.oportunidad or 0) > (acumulado[k].oportunidad or 0) + 0.02
    ]
    empeoran = [
        nombre_propio(k)
        for k, t in top
        if k in acumulado and (t.oportunidad or 0) < (acumulado[k].oportunidad or 0) - 0.02
    ]
    texto = f"Estas quince dependencias reúnen el {porcentaje(parte, 1)} de lo gestionado en el mes entre {c.total_dependencias_con_radicados} con radicados. "
    if mejoran:
        texto += f"Frente a su propio acumulado del año, mejoran en el mes {lista_en_prosa(mejoran[:4])}. "
    if empeoran:
        texto += f"Quedan por debajo de su acumulado {lista_en_prosa(empeoran[:4])}. "
    return (
        texto
        + "Leer el mes junto con el acumulado del año permite distinguir un mes atípico de una situación sostenida."
    )


def grupos_tabla(c: Calculo) -> str:
    m = c.mes
    grupos = c.por_grupo[:12]
    if not grupos:
        return "El archivo del mes no asigna PQRSDF a grupos internos de trabajo."
    k0, t0 = grupos[0]
    unidad, dependencia = k0.split("|", 1)
    altos = [g for g in grupos if (g[1].oportunidad or 0) >= 0.9]
    peor = min(grupos, key=lambda g: g[1].oportunidad or 0)
    return (
        f"{nombre_propio(unidad)} ({con_articulo(dependencia)}) es el grupo con más PQRSDF gestionadas: {entero(t0.radicados)}, el "
        f"{porcentaje(_parte(t0.radicados, m.radicados), 1)} del mes, con {porcentaje(t0.oportunidad)} a tiempo. {numero_en_palabras(len(altos), False).capitalize()} de los "
        f"{numero_en_palabras(len(grupos), False)} grupos listados superan el 90 % de oportunidad; el de menor oportunidad es {nombre_propio(peor[0].split('|')[0])} "
        f"({porcentaje(peor[1].oportunidad)})."
    )


def tipos_grafico(c: Calculo) -> str:
    m = c.mes
    tipos = [(k, t) for k, t in c.por_tipo if t.radicados]
    top3 = tipos[:3]
    parte = _parte(sum(t.radicados for _, t in top3), m.radicados)
    return (
        f"{lista_en_prosa([capitalizar(k) for k, _ in top3])} reúnen el {porcentaje(parte, 1)} de las PQRSDF gestionadas; el resto de tipos tiene volúmenes "
        "pequeños y su oportunidad debe leerse con cautela, porque pocas respuestas cambian mucho el porcentaje."
    )


def tipos_tabla(c: Calculo) -> str:
    m = c.mes
    tipos = [(k, t) for k, t in c.por_tipo if t.radicados >= 50 and k != "sin homologar"]
    if not tipos:
        return "Ningún tipo de requerimiento alcanza un volumen relevante en el mes."
    peor = min(tipos, key=lambda kt: kt[1].oportunidad or 0)
    mejor = max(tipos, key=lambda kt: kt[1].oportunidad or 0)
    acumulado = dict(c.por_tipo_acumulado)
    ac = acumulado.get(peor[0])
    cola = ""
    if ac:
        cola = f" Su oportunidad acumulada en el año es de {porcentaje(ac.oportunidad)}, así que {'el mes confirma una dificultad sostenida' if (ac.oportunidad or 0) < 0.8 else 'el mes es peor que su propio promedio del año'}."
    return (
        f"Entre los tipos con al menos cincuenta PQRSDF, el de menor oportunidad fue «{capitalizar(peor[0])}» ({porcentaje(peor[1].oportunidad)} sobre "
        f"{entero(peor[1].radicados)}) y el de mayor, «{capitalizar(mejor[0])}» ({porcentaje(mejor[1].oportunidad)}); la oportunidad total del mes fue de "
        f"{porcentaje(m.oportunidad)}.{cola}"
    )


def canal_grafico(c: Calculo) -> str:
    canales = [(k, t) for k, t in (c.por_canal or []) if t.radicados]
    if len(canales) < 2:
        return "Solo un canal tiene PQRSDF en el mes."
    mejor = max(canales, key=lambda kt: kt[1].oportunidad or 0)
    peor = min(canales, key=lambda kt: kt[1].oportunidad or 0)
    return (
        f"Las PQRSDF que ingresaron por {capitalizar(mejor[0]).lower()} tuvieron la mayor oportunidad ({porcentaje(mejor[1].oportunidad)}) y las de "
        f"{capitalizar(peor[0]).lower()} la menor ({porcentaje(peor[1].oportunidad)}). El canal de entrada condiciona el direccionamiento y por eso puede explicar parte de la diferencia."
    )


def canal_tabla(c: Calculo) -> str:
    m = c.mes
    canales = [(k, t) for k, t in (c.por_canal or []) if t.radicados]
    if not canales:
        return "No hay canal registrado para las PQRSDF del mes."
    mayor = max(canales, key=lambda kt: kt[1].radicados)
    mas_ext = max(canales, key=lambda kt: kt[1].extemporaneas)
    return (
        f"Por {capitalizar(mayor[0]).lower()} entró el {porcentaje(_parte(mayor[1].radicados, m.radicados), 1)} de lo gestionado y por "
        f"{capitalizar(mas_ext[0]).lower()} llegó el {porcentaje(_parte(mas_ext[1].extemporaneas, m.extemporaneas), 1)} de las extemporáneas "
        f"({entero(mas_ext[1].extemporaneas)}), con {decimal(mas_ext[1].promedio_dias_gestion, 1)} días hábiles de gestión en promedio."
    )


def ejes_grafico(c: Calculo) -> str:
    m = c.mes
    ejes = [(k, t) for k, t in c.por_eje if k != "sin eje tematico" and t.radicados]
    if not ejes:
        return "El mes no trae ejes temáticos."
    top = ejes[:3]
    parte = _parte(sum(t.radicados for _, t in top), m.radicados)
    return (
        f"Los tres ejes de mayor volumen, {lista_en_prosa([f'«{capitalizar(k)}»' for k, _ in top])}, reúnen el {porcentaje(parte, 1)} de las PQRSDF "
        f"gestionadas, entre {entero(len(ejes))} ejes con radicados en el mes. La lista larga de asuntos con pocos casos es la norma; los diez de la gráfica "
        "muestran dónde se concentra la demanda."
    )


def ejes_tabla(c: Calculo) -> str:
    ejes = [(k, t) for k, t in c.por_eje if k != "sin eje tematico" and t.radicados][:15]
    if not ejes:
        return "El mes no trae ejes temáticos."
    mas_ext = sorted(ejes, key=lambda kt: -kt[1].extemporaneas)[:2]
    peor = min([e for e in ejes if e[1].radicados >= 100] or ejes, key=lambda kt: kt[1].oportunidad or 0)
    return (
        f"Entre estos quince ejes, los que más extemporáneas acumulan son {lista_en_prosa([f'«{capitalizar(k)}» ({entero(t.extemporaneas)})' for k, t in mas_ext])}; "
        f"el de menor oportunidad con volumen relevante es «{capitalizar(peor[0])}» ({porcentaje(peor[1].oportunidad)}). Un eje con muchas extemporáneas "
        "suele corresponder a un trámite o consulta que exige más tiempo del que da el plazo legal."
    )


# --- 4.12 tiempos ---------------------------------------------------------------------------------------------------------


def tiempos_grafico(c: Calculo) -> str:
    serie = c.serie_13
    mayor = max(serie, key=lambda pt: pt[1].promedio_dias_gestion or 0)
    menor = min(serie, key=lambda pt: pt[1].promedio_dias_gestion or 0)
    m = c.mes
    return (
        f"El tiempo promedio de gestión osciló entre {decimal(menor[1].promedio_dias_gestion, 1)} días hábiles ({mes_y_anio(menor[0])}) y "
        f"{decimal(mayor[1].promedio_dias_gestion, 1)} ({mes_y_anio(mayor[0])}); en {nombre_mes(c.periodo)} fue de {decimal(m.promedio_dias_gestion, 1)}. "
        f"La línea roja, el retraso promedio de las extemporáneas, cerró el mes en {decimal(m.promedio_dias_retraso, 1)} días hábiles: cuanto más se separa "
        "de la azul, más tarde se atiende lo que ya venció."
    )


def tiempos_tabla(c: Calculo) -> str:
    serie = c.serie_13
    m, acu = c.mes, c.acumulado
    mayor_retraso = max(serie, key=lambda pt: pt[1].promedio_dias_retraso or 0)
    d = (m.promedio_dias_retraso or 0) - (acu.promedio_dias_retraso or 0)
    return (
        f"El mayor retraso promedio del periodo fue el de {mes_y_anio(mayor_retraso[0])} ({decimal(mayor_retraso[1].promedio_dias_retraso, 1)} días hábiles). "
        f"El de {nombre_mes(c.periodo)} ({decimal(m.promedio_dias_retraso, 1)}) está {decimal(abs(d), 1)} días {'por encima' if d > 0 else 'por debajo'} del promedio "
        f"del año ({decimal(acu.promedio_dias_retraso, 1)}). Un retraso promedio de pocos días indica que la mayoría de las extemporáneas se cierran poco "
        "después del plazo; cuando supera las dos semanas, hay casos que se quedan sin atención."
    )


# --- 4.13 pronóstico y 4.14 histórico ---------------------------------------------------------------------------------------


def pronostico_grafico(c: Calculo) -> str:
    con_real = [(p, r, v) for p, r, v in c.pronostico if r is not None]
    if not con_real:
        return "No hay meses con dato real para contrastar con el pronóstico."
    debajo = sum(1 for _, r, v in con_real if r < v)
    mayor = max(con_real, key=lambda x: abs(x[1] - x[2]))
    return (
        f"La línea real quedó por debajo de la pronosticada en {numero_en_palabras(debajo, False)} de los {numero_en_palabras(len(con_real), False)} meses con dato; "
        f"la mayor diferencia fue en {nombre_mes(mayor[0])} ({puntos(mayor[1] - mayor[2])}). "
        + (
            "Un pronóstico que se incumple de forma sistemática indica que el comportamiento del año cambió frente al histórico con que se ajustó el modelo."
            if debajo >= max(3, len(con_real) * 2 // 3)
            else "Las diferencias se reparten en ambos sentidos, de modo que el modelo sigue describiendo bien el comportamiento del año."
        )
    )


def pronostico_tabla(c: Calculo) -> str:
    con_real = [(p, r, v) for p, r, v in c.pronostico if r is not None]
    if not con_real:
        return "No hay meses con dato real para contrastar con el pronóstico."
    p, r, v = con_real[-1]
    promedio = sum(r - v for _, r, v in con_real) / len(con_real)
    return (
        f"En {nombre_mes(p)} el modelo esperaba {porcentaje(v)} y el resultado fue {porcentaje(r)} ({puntos(r - v)}); la diferencia promedio del año es de "
        f"{puntos(promedio)}. El pronóstico sirve como meta de referencia mensual: la distancia a él mide cuánto falta para volver al comportamiento esperado."
    )


def historico_tabla(c: Calculo) -> str:
    anios = c.historico_anual
    completos = [(k, t) for k, t in anios if k != str(c.anio)]
    mejor = max(anios, key=lambda kt: kt[1].oportunidad or 0)
    texto = f"El mejor año del histórico fue {mejor[0]} ({porcentaje(mejor[1].oportunidad)})"
    if completos:
        ultimo = completos[-1]
        d = (c.acumulado.oportunidad or 0) - (ultimo[1].oportunidad or 0)
        texto += (
            f" y {c.anio}, hasta {nombre_mes(c.periodo)}, va {decimal(abs(d) * 100, 2)} pp {'por encima' if d >= 0 else 'por debajo'} del cierre de {ultimo[0]} "
            f"({porcentaje(ultimo[1].oportunidad)})"
        )
    return (
        texto
        + ". El volumen anual muestra la escala de la demanda que atiende la entidad y la oportunidad, cuánta de esa demanda se responde en plazo."
    )


def historico_grafico(c: Calculo) -> str:
    anios = c.historico_anual
    valores = [(k, t.oportunidad or 0) for k, t in anios]
    caidas = sum(1 for i in range(1, len(valores)) if valores[i][1] < valores[i - 1][1])
    return (
        f"Las barras muestran {numero_en_palabras(len(valores), False)} años; en {numero_en_palabras(caidas, False)} de las comparaciones año a año la oportunidad bajó. "
        f"El año en curso aparece con datos parciales hasta {nombre_mes(c.periodo)}, por lo que su barra puede cambiar con los meses que faltan."
    )
