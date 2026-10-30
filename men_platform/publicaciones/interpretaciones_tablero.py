"""La narrativa de las vistas que replican el tablero: mes a mes, variaciones, mapa de calor, medias móviles, dos años,
brechas, dependencias extemporáneas, requerimientos, Pareto de ejes y canales. Mismo tono que interpretaciones_pqrsdf."""

from __future__ import annotations

from men_platform.publicaciones.datos_pqrsdf import Calculo, Totales
from men_platform.publicaciones.texto_es import (
    capitalizar,
    con_articulo,
    decimal,
    entero,
    entre_tramo,
    lista_en_prosa,
    mayuscula_inicial,
    mes_y_anio,
    nombre_mes,
    nombre_propio,
    numero_en_palabras,
    porcentaje,
    puntos,
    variacion,
)

NOMBRES = {
    "radicados": "el total general",
    "a_tiempo": "el volumen a tiempo",
    "extemporaneas": "el volumen extemporáneo",
    "tasa_extemporaneas": "la tasa de extemporaneidad",
    "oportunidad": "la oportunidad",
}


def _valor(t: Totales, campo: str) -> float | None:
    return getattr(t, campo)


def _fmt(v: float | None, campo: str) -> str:
    if campo in ("oportunidad", "tasa_extemporaneas"):
        return porcentaje(v)
    return entero(v)


def _cambio(a: float | None, b: float | None, campo: str) -> str:
    if campo in ("oportunidad", "tasa_extemporaneas"):
        return puntos(None if a is None or b is None else a - b)
    return variacion(a, b)


def mes_a_mes(c: Calculo) -> str:
    serie = c.serie_anio
    mejor = max(serie, key=lambda pt: pt[1].oportunidad or 0)
    peor = min(serie, key=lambda pt: pt[1].oportunidad or 0)
    mayor = max(serie, key=lambda pt: pt[1].radicados)
    return (
        f"Mes a mes, {c.anio} muestra su mejor oportunidad en {nombre_mes(mejor[0])} ({porcentaje(mejor[1].oportunidad)}) y la peor en {nombre_mes(peor[0])} "
        f"({porcentaje(peor[1].oportunidad)}); el mes de mayor carga fue {nombre_mes(mayor[0])}, con {entero(mayor[1].radicados)} PQRSDF gestionadas. "
        f"{nombre_mes(c.periodo).capitalize()} cierra con {porcentaje(c.mes.oportunidad)} sobre {entero(c.mes.radicados)}: la línea del índice se lee junto con la "
        "altura de la columna, porque un mes de mucho volumen con buena oportunidad vale más que uno tranquilo."
    )


def variacion_mensual(c: Calculo, campo: str, menor_mejor: bool = False) -> str:
    serie = c.serie_13
    cambios = []
    for i in range(1, len(serie)):
        a, b = _valor(serie[i][1], campo), _valor(serie[i - 1][1], campo)
        if a is not None and b is not None:
            cambios.append(
                (serie[i][0], a - b if campo in ("oportunidad", "tasa_extemporaneas") else (a - b) / b if b else 0)
            )
    if not cambios:
        return "No hay meses consecutivos para comparar."
    sube = max(cambios, key=lambda x: x[1])
    baja = min(cambios, key=lambda x: x[1])
    ultimo = cambios[-1]
    nombre = NOMBRES[campo]
    pp = campo in ("oportunidad", "tasa_extemporaneas")
    fmt = (
        (lambda v: puntos(v))
        if pp
        else (lambda v: f"{'+' if v > 0 else '−' if v < 0 else ''}{decimal(abs(v) * 100, 1)} %")
    )
    mejora = (ultimo[1] < 0) if menor_mejor else (ultimo[1] > 0)
    return (
        f"De un mes al siguiente, {nombre} subió más en {mes_y_anio(sube[0])} ({fmt(sube[1])}) y bajó más en {mes_y_anio(baja[0])} ({fmt(baja[1])}). "
        f"En {nombre_mes(c.periodo)} la variación fue de {fmt(ultimo[1])}, {'una mejora' if mejora else 'un retroceso'} frente al mes inmediatamente anterior. "
        "Las barras del mismo color seguidas muestran rachas; los cambios de signo, meses que rompen la tendencia."
    )


def mapa_calor(c: Calculo) -> str:
    celdas = [(a, m, v) for a, meses in c.matriz_oportunidad.items() for m, v in meses.items() if v is not None]
    mejor = max(celdas, key=lambda x: x[2])
    peor = min(celdas, key=lambda x: x[2])
    mismo_mes = sorted([(a, v) for a, m, v in celdas if m == c.mes_numero], key=lambda x: -x[1])
    puesto = next(i for i, (a, _) in enumerate(mismo_mes, start=1) if a == c.anio)
    fila_actual = [v for a, m, v in celdas if a == c.anio]
    fila_anterior = [v for a, m, v in celdas if a == c.anio - 1]
    prom_actual = sum(fila_actual) / len(fila_actual) if fila_actual else None
    prom_anterior = sum(fila_anterior) / len(fila_anterior) if fila_anterior else None
    if len(celdas) == 1:
        return (
            f"El histórico empieza en {mes_y_anio(c.periodo)}, así que el mapa tiene por ahora una sola celda ({porcentaje(mejor[2])}); "
            "cada mes nuevo agregará la suya."
        )
    texto = (
        f"{entre_tramo(c.periodo)} de cada año del histórico, el mejor mes fue {nombre_mes(f'{mejor[0]}-{mejor[1]:02d}-01')} de {mejor[0]} ({porcentaje(mejor[2])}) y el peor "
        f"{nombre_mes(f'{peor[0]}-{peor[1]:02d}-01')} de {peor[0]} ({porcentaje(peor[2])})."
    )
    if len(mismo_mes) == 1:
        texto += f" Es el primer {nombre_mes(c.periodo)} del histórico."
    else:
        texto += f" Entre los {numero_en_palabras(len(mismo_mes), False)} meses de {nombre_mes(c.periodo)} del histórico, el de {c.anio} ocupa el puesto {puesto}."
    if prom_actual is not None and prom_anterior is not None:
        texto += f" La fila de {c.anio} es, en promedio, {'más clara' if prom_actual < prom_anterior else 'más oscura'} que la de {c.anio - 1}: {porcentaje(prom_actual)} frente a {porcentaje(prom_anterior)}."
    return (
        texto
        + " Las celdas rojas marcan los meses que exigen explicación; las azules oscuras, los que vale la pena replicar."
    )


def media_movil(c: Calculo, campo: str) -> str:
    medias = {
        "oportunidad": c.media_movil_oportunidad,
        "radicados": c.media_movil_radicados,
        "a_tiempo": c.media_movil_a_tiempo,
        "extemporaneas": c.media_movil_extemporaneas,
    }[campo]
    actual = _valor(c.mes, campo)
    mm = medias.get(c.periodo)
    if actual is None or mm is None:
        return "No hay tres meses anteriores completos para calcular la media móvil."
    nombre = NOMBRES[campo]
    ultimos = [(p, _valor(t, campo), medias.get(p)) for p, t in c.serie_13[1:]]
    encima = sum(1 for _, v, m in ultimos if v is not None and m is not None and v > m)
    pp = campo == "oportunidad"
    dif = f"{puntos(actual - mm)}" if pp else variacion(actual, mm)
    return (
        f"La media móvil suaviza los saltos de un mes: compara cada mes con el promedio de los tres anteriores. En {nombre_mes(c.periodo)}, {nombre} fue de "
        f"{_fmt(actual, campo)} frente a una media móvil de {_fmt(mm, campo)} ({dif}); en {numero_en_palabras(encima, False)} de los últimos doce meses el valor real "
        f"quedó por encima de su media móvil. "
        + (
            "Estar por encima de la media móvil en oportunidad es una buena señal; en volumen extemporáneo, lo contrario."
            if campo in ("oportunidad", "extemporaneas")
            else "Un valor sostenido por encima de la media móvil indica una tendencia al alza y no un mes aislado."
        )
    )


def dos_anios_campo(c: Calculo, campo: str, menor_mejor: bool = False) -> str:
    anterior = {int(p[5:7]): t for p, t in c.serie_anio_anterior}
    pares = [
        (p, _valor(t, campo), _valor(anterior[int(p[5:7])], campo)) for p, t in c.serie_anio if int(p[5:7]) in anterior
    ]
    pares = [(p, a, b) for p, a, b in pares if a is not None and b is not None]
    nombre = NOMBRES[campo]
    if not pares:
        serie = [(p, _valor(t, campo)) for p, t in c.serie_anio if _valor(t, campo) is not None]
        if len(serie) <= 1:
            return (
                f"{mayuscula_inicial(mes_y_anio(c.periodo))} es el primer mes del histórico: {nombre} fue de {_fmt(serie[0][1], campo) if serie else '–'}; "
                f"desde {c.anio + 1} el gráfico tendrá la referencia del año anterior."
            )
        mayor = max(serie, key=lambda pv: pv[1])
        menor = min(serie, key=lambda pv: pv[1])
        return (
            f"El histórico empieza en {c.anio}, así que todavía no hay un año anterior como referencia. Entre enero y {nombre_mes(c.periodo)}, {nombre} "
            f"tuvo su máximo en {nombre_mes(mayor[0])} ({_fmt(mayor[1], campo)}) y su mínimo en {nombre_mes(menor[0])} ({_fmt(menor[1], campo)}); "
            f"desde {c.anio + 1} la línea amarilla mostrará el año anterior."
        )
    mejores = sum(1 for _, a, b in pares if ((a < b) if menor_mejor else (a > b)))
    mayor = max(pares, key=lambda x: abs(x[1] - x[2]))
    acu, acu_ant = c.acumulado, c.acumulado_anterior
    texto = (
        f"En {'ninguno' if mejores == 0 else numero_en_palabras(mejores, False)} de los {numero_en_palabras(len(pares), False)} meses comparables de {c.anio}, {nombre} fue "
        f"{'menor' if menor_mejor else 'mayor'} que en el mismo mes de {c.anio - 1}; la mayor diferencia se dio en {nombre_mes(mayor[0])} "
        f"({_fmt(mayor[1], campo)} frente a {_fmt(mayor[2], campo)}, {_cambio(mayor[1], mayor[2], campo)})."
    )
    if acu_ant:
        texto += f" En el acumulado del año, {nombre} suma {_fmt(_valor(acu, campo), campo)} frente a {_fmt(_valor(acu_ant, campo), campo)} del mismo tramo de {c.anio - 1} ({_cambio(_valor(acu, campo), _valor(acu_ant, campo), campo)})."
    return texto


def brecha(c: Calculo, campo: str) -> str:
    serie = c.serie_anio
    partes = [(p, (getattr(t, campo) / t.radicados) if t.radicados else 0) for p, t in serie]
    mayor = max(partes, key=lambda x: x[1])
    menor = min(partes, key=lambda x: x[1])
    actual = partes[-1][1]
    if campo == "a_tiempo":
        return (
            f"La parte a tiempo del total general osciló en {c.anio} entre {porcentaje(menor[1], 1)} ({nombre_mes(menor[0])}) y {porcentaje(mayor[1], 1)} "
            f"({nombre_mes(mayor[0])}); en {nombre_mes(c.periodo)} fue de {porcentaje(actual, 1)}. La distancia entre la columna gris y la azul es lo que "
            "quedó fuera de plazo cada mes."
        )
    return (
        f"La tasa de extemporaneidad de {c.anio} se movió entre {porcentaje(menor[1], 1)} ({nombre_mes(menor[0])}) y {porcentaje(mayor[1], 1)} "
        f"({nombre_mes(mayor[0])}); en {nombre_mes(c.periodo)} fue de {porcentaje(actual, 1)}, es decir, {entero(c.mes.extemporaneas)} de las "
        f"{entero(c.mes.radicados)} gestionadas. Una tasa que baja mientras el total sube es la mejor combinación posible."
    )


def extemporaneas_dependencias(c: Calculo) -> str:
    m = c.mes
    deps = sorted(
        [(k, t) for k, t in c.por_dependencia if k != "sin dependencia" and t.extemporaneas],
        key=lambda kt: -kt[1].extemporaneas,
    )
    if not deps or not m.extemporaneas:
        return "No hay extemporáneas en el mes."
    top = deps[:3]
    parte = sum(t.extemporaneas for _, t in top) / m.extemporaneas
    mayor_tasa = max(
        [(k, t) for k, t in deps if t.radicados >= 50] or deps, key=lambda kt: kt[1].tasa_extemporaneas or 0
    )
    texto = (
        f"{lista_en_prosa([f'{con_articulo(k)} ({entero(t.extemporaneas)})' for k, t in top])} reúnen el {porcentaje(parte, 1)} de las extemporáneas del mes. "
        f"La tasa de extemporaneidad más alta entre las dependencias con volumen relevante es la de {con_articulo(mayor_tasa[0])} ({porcentaje(mayor_tasa[1].tasa_extemporaneas)})."
    )
    if m.abiertas_vencidas:
        abiertas = sorted(deps, key=lambda kt: -kt[1].abiertas_vencidas)[:2]
        texto += f" De las {entero(m.abiertas_vencidas)} extemporáneas que seguían abiertas al corte, las que más tienen son {lista_en_prosa([f'{con_articulo(k)} ({entero(t.abiertas_vencidas)})' for k, t in abiertas if t.abiertas_vencidas])}."
    return texto[0].upper() + texto[1:]


def grupos_extemporaneas(c: Calculo) -> str:
    grupos = sorted([g for g in c.por_grupo if g[1].extemporaneas], key=lambda g: -g[1].extemporaneas)[:3]
    if not grupos:
        return "Ningún grupo interno de trabajo tiene extemporáneas en el mes."
    k0, t0 = grupos[0]
    unidad, dependencia = k0.split("|", 1)
    return (
        f"Entre los grupos internos, {nombre_propio(unidad)} ({con_articulo(dependencia)}) concentra más extemporáneas: {entero(t0.extemporaneas)} de "
        f"{entero(t0.radicados)} gestionadas ({porcentaje(t0.tasa_extemporaneas)}). Bajar al nivel de grupo permite ubicar el equipo concreto donde se acumula el retraso."
    )


def requerimientos_burbujas(c: Calculo) -> str:
    tipos = [(k, t) for k, t in c.por_tipo if k != "sin homologar" and t.radicados >= 20]
    if not tipos:
        return "No hay tipos de requerimiento con volumen suficiente."
    arriba_derecha = [k for k, t in tipos if t.radicados >= 500 and (t.oportunidad or 0) >= 0.9]
    abajo = sorted(tipos, key=lambda kt: kt[1].oportunidad or 0)[:2]
    return (
        f"Las burbujas grandes y altas son los tipos que la entidad maneja bien y en volumen: {lista_en_prosa([capitalizar(k) for k in arriba_derecha]) if arriba_derecha else 'ninguno este mes'}. "
        f"Las que caen hacia abajo son los tipos con menor oportunidad: {lista_en_prosa([f'{capitalizar(k)} ({porcentaje(t.oportunidad)}, {entero(t.radicados)} gestionadas)' for k, t in abajo])}. "
        "Cuanto más a la derecha y más abajo esté una burbuja, más pesa en el resultado total."
    )


def requerimientos_flujos(c: Calculo) -> str:
    m = c.mes
    tipos = [(k, t) for k, t in c.por_tipo if t.radicados > 0][:10]
    mas_ext = max(tipos, key=lambda kt: kt[1].extemporaneas)
    parte = mas_ext[1].extemporaneas / m.extemporaneas if m.extemporaneas else 0
    return (
        f"Separar cada tipo en a tiempo y extemporáneas muestra de dónde sale la brecha: «{capitalizar(mas_ext[0])}» aporta {entero(mas_ext[1].extemporaneas)} "
        f"extemporáneas, el {porcentaje(parte, 1)} del total del mes. Un tipo con barra roja larga y volumen alto es prioridad; uno con barra roja larga y "
        "volumen pequeño pesa poco en el índice pero puede señalar un procedimiento que no cabe en el plazo."
    )


def ejes_pareto(c: Calculo) -> str:
    ejes = [(k, t.radicados) for k, t in c.por_eje if k != "sin eje tematico" and t.radicados > 0]
    total = sum(v for _, v in ejes) or 1
    suma, n80 = 0, 0
    for i, (_, v) in enumerate(ejes, start=1):
        suma += v
        if suma / total >= 0.8:
            n80 = i
            break
    return (
        f"De los {entero(len(ejes))} ejes con PQRSDF en el mes, los primeros {entero(n80)} reúnen el 80 % del volumen y el resto se reparte el 20 % restante. "
        "El Pareto dice dónde conviene estandarizar respuestas: los pocos asuntos que concentran la demanda."
    )


def canal_mezcla(c: Calculo) -> str:
    if not c.canal_por_mes:
        return "No hay canal registrado para los meses del año."
    primero, ultimo = c.canal_por_mes[0], c.canal_por_mes[-1]

    def parte(lista: list[tuple[str, Totales]], canal: str) -> float:
        total = sum(t.radicados for _, t in lista) or 1
        return sum(t.radicados for k, t in lista if k == canal) / total

    canales = sorted(
        {k for _, lista in c.canal_por_mes for k, _ in lista if k != "sin informacion"},
        key=lambda k: -parte(ultimo[1], k),
    )
    principal = canales[0]
    return (
        f"Por {capitalizar(principal).lower()} entra la mayor parte de las PQRSDF: {porcentaje(parte(ultimo[1], principal), 1)} en {nombre_mes(ultimo[0])} frente a "
        f"{porcentaje(parte(primero[1], principal), 1)} en {nombre_mes(primero[0])}. "
        + lista_en_prosa([f"{capitalizar(k).lower()} pesa {porcentaje(parte(ultimo[1], k), 1)}" for k in canales[1:]])
        + ". Un cambio en la mezcla cambia también la carga de radicación y direccionamiento."
    )


def canal_tipos(c: Calculo) -> str:
    if not c.tipos_por_canal:
        return "No hay canal registrado para el mes."
    filas = c.tipos_por_canal[:5]
    frases = []
    for tipo, canales in filas:
        total = sum(canales.values()) or 1
        canal, valor = max(canales.items(), key=lambda kv: kv[1])
        frases.append(
            f"{capitalizar(tipo).lower()} llega sobre todo por {capitalizar(canal).lower()} ({porcentaje(valor / total, 1)})"
        )
    return (
        "Cada tipo tiene su puerta de entrada habitual: "
        + lista_en_prosa(frases)
        + ". Conocerla ayuda a ubicar la revisión de la radicación donde más efecto tiene."
    )
