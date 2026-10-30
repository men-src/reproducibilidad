"""La redacción del Informe de Trámites: párrafos en tercera persona, lenguaje neutro y claro, que salen de las cifras
del mes con reglas explícitas. Resumen ejecutivo, hallazgos de portada, objetivos, metodología, glosario,
observaciones, recomendaciones y conclusiones. Nada se escribe a mano para un mes concreto: todo vale para cualquier
mes, y lo que no existe en un mes (un tipo sin datos, un año anterior que no hay) no se promete."""

from __future__ import annotations

from men_platform.publicaciones.datos_tramites import DEFINICIONES, NOMBRES, PARETO, Calculo, Serie, cuantos_para
from men_platform.publicaciones.redaccion_pqrsdf import Textos
from men_platform.publicaciones.senales import CANTIDAD, frase_senal, serie_hasta
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
    tramo_del_anio,
    variacion,
    variacion_relativa,
)

DESVIO_PROMEDIO = 0.10  # un mes a más del 10 % de su promedio mensual merece observación
SALTO_VOLUMEN = 0.15  # variación relativa que se considera un cambio fuerte de un mes al otro, o frente al año anterior
SALTO_ACUMULADO = 0.10
SALTO_TIPO = 0.20  # un tipo que cambia más del 20 % frente a su mes anterior
UMBRAL_TIPO = 50  # trámites mínimos en el mes anterior para juzgar el salto de un tipo
CONCENTRACION = 0.5  # el tipo principal concentra más de la mitad


def _bajo(s: Serie) -> str:
    return s.nombre.lower() if s.tramite is None or s.tramite.fuente != "pqrs" else s.nombre


def _hasta(tipos: list[Serie]) -> str:
    """«certificados de existencia y certificados de programa hasta noviembre de 2025; convalidaciones de básica
    hasta julio de 2024»: los tipos sin datos agrupados por su último mes con datos, del más reciente al más antiguo."""
    grupos: dict[str, list[str]] = {}
    for s in tipos:
        grupos.setdefault(s.ultimo_periodo or "", []).append(_bajo(s))
    partes = [f"{lista_en_prosa(nombres)} hasta {mes_y_anio(p)}" for p, nombres in sorted(grupos.items(), reverse=True)]
    if len(partes) == 1:
        return f"su último mes con datos es {mes_y_anio(next(iter(grupos)))}"
    return "; ".join(partes)


def _frente(s: Serie, c: Calculo) -> str:
    """«frente a agosto» o «frente al mes anterior con datos (noviembre de 2025)»."""
    if s.periodo_anterior is None:
        return ""
    if s.periodo_anterior == c.periodo_anterior_str():
        return f"frente a {nombre_mes(s.periodo_anterior)}"
    return f"frente al mes anterior con datos ({mes_y_anio(s.periodo_anterior)})"


def resumen(c: Calculo) -> list[str]:
    t = c.total
    m, ant, mismo = t.mes or 0, t.mes_anterior, t.mismo_mes_anterior
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    tipos = c.tipos_del_mes
    parrafos: list[str] = []

    # 1. el total del mes y sus comparaciones
    frase = (
        f"En {mes} el Ministerio de Educación Nacional gestionó {entero(m)} trámites de "
        f"{numero_en_palabras(len(tipos), femenino=False)} tipos a través de la Subdirección de Relacionamiento con la Ciudadanía"
    )
    comparaciones = []
    if ant:
        comparaciones.append(f"{variacion(m, ant)} frente a {nombre_mes(t.periodo_anterior)} ({entero(ant)})")
    if mismo:
        comparaciones.append(f"{variacion(m, mismo)} frente a {nombre_mes(c.periodo)} de {anio_ant} ({entero(mismo)})")
    if comparaciones:
        frase += ": " + " y ".join(comparaciones)
    promedio = t.promedio_mensual
    if promedio and len(t.serie_anio) >= 2:
        lado = "por encima" if m >= promedio else "por debajo"
        senal = frase_senal(serie_hasta(t.serie_13, c.periodo, float), lambda v: entero(round(v)), CANTIDAD)
        frase += f". El mes quedó {lado} del promedio mensual de {anio} ({decimal(promedio, 1)} trámites), {variacion(m, promedio)}{senal}"
    parrafos.append(frase + ".")

    # 2. el reparto por tipo
    principal = tipos[0]
    frase = (
        f"{mayuscula_inicial(_bajo(principal))} fue el trámite principal, con {entero(principal.mes)} "
        f"({porcentaje(c.participacion(principal), 1)} del total)"
    )
    if len(tipos) > 1:
        otros = [f"{_bajo(s)} {entero(s.mes)} ({porcentaje(c.participacion(s), 1)})" for s in tipos[1:4]]
        frase += f"; {'le siguió' if len(otros) == 1 else 'le siguieron'} {lista_en_prosa(otros)}"
    n = cuantos_para([s.mes or 0 for s in tipos])
    if len(tipos) > 2:
        frase += (
            f". {mayuscula_inicial(numero_en_palabras(n, femenino=False))} {'tipo explica' if n == 1 else 'tipos explican'} el "
            f"{porcentaje(PARETO, 0)} del volumen del mes"
        )
    parrafos.append(frase + ".")

    # 3. qué cambió por tipo frente al mes anterior
    if ant:
        con_par = [s for s in tipos if s.mes_anterior and s.mes_anterior >= UMBRAL_TIPO]
        suben = sorted(
            [s for s in con_par if (s.mes or 0) > s.mes_anterior],
            key=lambda s: -(variacion_relativa(s.mes, s.mes_anterior) or 0),
        )
        bajan = sorted(
            [s for s in con_par if (s.mes or 0) < s.mes_anterior],
            key=lambda s: variacion_relativa(s.mes, s.mes_anterior) or 0,
        )
        partes = []
        if suben:
            partes.append(
                f"{'subió' if len(suben) == 1 else 'subieron'} "
                f"{lista_en_prosa([f'{_bajo(s)} ({variacion(s.mes, s.mes_anterior)})' for s in suben[:3]])}"
            )
        if bajan:
            partes.append(
                f"{'bajó' if len(bajan) == 1 else 'bajaron'} "
                f"{lista_en_prosa([f'{_bajo(s)} ({variacion(s.mes, s.mes_anterior)})' for s in bajan[:3]])}"
            )
        if partes:
            parrafos.append(f"Frente a {nombre_mes(t.periodo_anterior)}, {'; '.join(partes)}.")

    # 4. el año (con un solo mes en el año, el acumulado es el mes y ya se dijo)
    frases = []
    if t.meses_acumulado >= 2:
        mayor, menor = t.mes_mayor, t.mes_menor
        frase = f"{entre_tramo(c.periodo)} de {anio} se gestionaron {entero(t.acumulado)} trámites"
        if t.acumulado_anterior:
            frase += (
                f", {variacion(t.acumulado, t.acumulado_anterior)} frente a los mismos meses de {anio_ant} "
                f"({entero(t.acumulado_anterior)})"
            )
        if mayor and menor and mayor[0] != menor[0]:
            frase += (
                f"; el mes más alto fue {nombre_mes(mayor[0])} ({entero(mayor[1])}) y el más bajo {nombre_mes(menor[0])} "
                f"({entero(menor[1])})"
            )
        frases.append(frase)
    descontinuados = [s for s in c.tipos if s.ultimo_periodo and s.ultimo_periodo < c.periodo]
    if descontinuados:
        frases.append(
            f"{mayuscula_inicial(lista_en_prosa([_bajo(s) for s in descontinuados]))} no "
            f"{'tiene' if len(descontinuados) == 1 else 'tienen'} datos en {nombre_mes(c.periodo)}: {_hasta(descontinuados)}"
        )
    if frases:
        parrafos.append(". ".join(frases) + ".")
    return parrafos


def hallazgos(c: Calculo) -> list[str]:
    """Las cinco líneas de «En síntesis» de la portada, cortas para que quepan en una línea."""
    t = c.total
    tipos = c.tipos_del_mes
    lineas = [f"{entero(t.mes)} trámites gestionados en {numero_en_palabras(len(tipos), femenino=False)} tipos"]
    if t.mes_anterior:
        lineas[0] += f" ({variacion(t.mes, t.mes_anterior)} frente a {nombre_mes(t.periodo_anterior)})"
    principal = tipos[0]
    lineas.append(
        f"{principal.nombre}: {entero(principal.mes)}, el {porcentaje(c.participacion(principal), 1)} del total"
    )
    if t.promedio_mensual and len(t.serie_anio) >= 2:
        lado = "por encima" if (t.mes or 0) >= t.promedio_mensual else "por debajo"
        lineas.append(
            f"{variacion(t.mes, t.promedio_mensual)} {lado} del promedio mensual de {c.anio} ({decimal(t.promedio_mensual, 1)})"
        )
    if t.mismo_mes_anterior:
        lineas.append(
            f"{variacion(t.mes, t.mismo_mes_anterior)} frente a {nombre_mes(c.periodo)} de {c.anio - 1} ({entero(t.mismo_mes_anterior)})"
        )
    if t.meses_acumulado >= 2:
        linea = f"{entero(t.acumulado)} trámites acumulados en {c.anio}"
        if t.acumulado_anterior:
            linea += f", {variacion(t.acumulado, t.acumulado_anterior)} frente a {c.anio - 1}"
        lineas.append(linea)
    elif len(tipos) > 2:
        n = cuantos_para([s.mes or 0 for s in tipos])
        lineas.append(
            f"{mayuscula_inicial(numero_en_palabras(n, femenino=False))} {'tipo explica' if n == 1 else 'tipos explican'} el "
            f"{porcentaje(PARETO, 0)} del mes: {lista_en_prosa([_bajo(s) for s in tipos[:n]])}"
        )
    return lineas[:5]


def objetivos(c: Calculo) -> tuple[str, list[str]]:
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    general = (
        f"Presentar los trámites gestionados por el Ministerio de Educación Nacional en {mes}: cuántos fueron, de qué tipos y cómo se "
        "comparan con el promedio mensual, con el mes anterior y con el año anterior, para que la entidad conozca la carga de cada "
        "trámite y tome decisiones sobre su operación."
    )
    t = c.total
    partes = []
    if t.mes_anterior:
        partes.append(f"con {nombre_mes(t.periodo_anterior)}, el mes inmediatamente anterior")
    if t.mismo_mes_anterior:
        partes.append(f"con {nombre_mes(c.periodo)} de {anio_ant}")
    especificos = [
        f"Cuantificar los trámites gestionados en {mes}, en total y por tipo"
        + (f", y compararlos {lista_en_prosa(partes)}" if partes else "")
        + ".",
        f"Medir la participación de cada tipo de trámite en el mes y en lo corrido de {anio}, y cuántos tipos explican la mayor parte "
        "del volumen.",
        f"Describir la evolución mes a mes de {anio} frente al promedio mensual, a la media móvil"
        + (f" y a {anio_ant}" if any(s.serie_anio_anterior for s in c.tipos) else "")
        + ", en total y por tipo de trámite.",
        "Identificar los tipos y los meses con mayor y menor volumen y proponer acciones a la entidad.",
    ]
    return general, especificos


def metodologia(c: Calculo) -> list[tuple[str, str]]:
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    t = c.total
    tramo = tramo_del_anio(c.periodo)
    comparaciones = "El informe es mensual"
    if t.mes_anterior:
        comparaciones += f": el mes se compara en primer lugar con el mes inmediatamente anterior ({nombre_mes(t.periodo_anterior)}), tipo por tipo"
    if t.mismo_mes_anterior or t.acumulado_anterior:
        comparaciones += f"; después, con el mismo mes de {anio_ant}"
        if t.meses_acumulado >= 2:
            comparaciones += f" y con el acumulado de {tramo} de {anio} frente a los mismos meses de {anio_ant}"
    comparaciones += (
        ". Las variaciones se expresan en porcentaje. Cuando un tipo no tiene datos en el mes calendario anterior, se compara con su "
        "mes anterior con datos y el informe lo dice."
    )
    tipos = lista_en_prosa([_bajo(s) for s in c.tipos])
    return [
        (
            "Fuentes",
            "El consolidado mensual de trámites de la Subdirección de Relacionamiento con la Ciudadanía: un total por mes y tipo de "
            "trámite desde enero de 2023, que la plataforma relee en cada publicación, y los meses nuevos, que llegan en un archivo con "
            "la misma forma. Este informe lee los mismos agregados mensuales por tipo que alimentan el informe interactivo, con corte al "
            f"{fecha_larga(c.fecha_corte)}.",
        ),
        (
            "Unidad de medida",
            "El trámite gestionado: cada trámite que la Subdirección registró como atendido en el mes. La fuente solo trae cantidades, "
            "así que el informe mide volumen: no hay oportunidad, estados ni tiempos de gestión.",
        ),
        (
            "Tipos de trámite",
            f"Los tipos con datos en {anio}: {tipos}. Cada uno se describe en el glosario. Un tipo del catálogo sin datos en el año "
            "no se incluye en el informe.",
        ),
        (
            "Meses con datos",
            "No todos los tipos tienen datos todos los meses: un tipo puede haber empezado después de 2023 o no registrar trámites en "
            "algún mes. Cada tipo se mira en sus meses con datos: sus promedios, series y comparaciones excluyen los meses sin datos "
            "en vez de mostrarlos como ceros, y el informe dice desde y hasta cuándo tiene datos cada uno.",
        ),
        ("Comparaciones", comparaciones),
        (
            "Promedio y media móvil",
            f"El promedio mensual es el total de {tramo} de {anio} dividido por los meses con datos; sirve de referencia para saber si "
            "un mes está por encima o por debajo de lo habitual en el año. La media móvil simple es el promedio de los tres meses "
            "inmediatamente anteriores, sin el mes evaluado, y dice si el mes está por encima o por debajo de su tendencia reciente.",
        ),
        (
            "Procesamiento",
            f"Los agregados se publican en la plataforma con cada actualización de datos; este informe de {mes} se generó de forma "
            "automática a partir de ellos: las cifras, los gráficos y los textos salen de reglas fijas, iguales para todos los meses, y no se "
            "corrigen a mano; las inconsistencias de la fuente se publican tal como llegan.",
        ),
    ]


def glosario(c: Calculo) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    terminos = [
        ("Acumulado del año", "La suma de los trámites de los meses con datos del año, de enero al mes del informe."),
        (
            "Media móvil simple",
            "Promedio de los trámites de los tres meses inmediatamente anteriores, sin el mes evaluado; sirve de referencia para "
            "saber si un mes está por encima o por debajo de su tendencia reciente.",
        ),
        ("Mes más alto", "El mes del año con más trámites gestionados; el mes más bajo, el de menos."),
        (
            "Pareto",
            "Los tipos de trámite de mayor a menor volumen con su participación acumulada; la guía del 80 % señala cuántos tipos "
            "explican la mayor parte del volumen.",
        ),
        ("Participación", "La parte de un tipo de trámite en el total general del mes o del año, en porcentaje."),
        ("Promedio mensual", "El total general del año dividido por los meses con datos."),
        (
            "Tipo de trámite",
            "La clase de trámite con que la fuente clasifica cada total mensual; hay diez en el catálogo.",
        ),
        ("Total general", "Los trámites gestionados en el mes, de todos los tipos."),
        (
            "Trámite gestionado",
            "Cada trámite que la Subdirección registró como atendido en el mes; es la unidad de medida del informe.",
        ),
        (
            "Variación",
            "Cambio de una cifra frente a otra, en porcentaje: frente al mes anterior, al mismo mes del año anterior o al promedio.",
        ),
    ]
    # solo los tipos que aparecen en el informe
    terminos += [
        (NOMBRES[k], v) for k, v in DEFINICIONES.items() if any(s.tramite and s.tramite.fuente == k for s in c.tipos)
    ]
    terminos.sort(key=lambda par: par[0].lower())
    siglas = [
        ("MEN", "Ministerio de Educación Nacional."),
        ("PQRSDF", "Peticiones, quejas, reclamos, sugerencias, denuncias y felicitaciones."),
        ("SRC", "Subdirección de Relacionamiento con la Ciudadanía, que publica este informe."),
    ]
    return terminos, siglas


def observaciones(c: Calculo) -> list[str]:
    t = c.total
    mes = nombre_mes(c.periodo)
    anio = c.anio
    m = t.mes or 0
    tipos = c.tipos_del_mes
    lineas: list[str] = []
    promedio = t.promedio_mensual
    if promedio and len(t.serie_anio) >= 2:
        desvio = m / promedio - 1
        if abs(desvio) >= DESVIO_PROMEDIO:
            lineas.append(
                f"El total general de {mes} ({entero(m)}) quedó {porcentaje(abs(desvio), 1)} {'por encima' if desvio > 0 else 'por debajo'} "
                f"del promedio mensual de {anio} ({decimal(promedio, 1)})."
            )
        else:
            lineas.append(
                f"El total general de {mes} ({entero(m)}) se mantuvo cerca del promedio mensual de {anio} ({decimal(promedio, 1)}): "
                f"{variacion(m, promedio)}."
            )
    if t.mes_anterior:
        v = variacion_relativa(m, t.mes_anterior)
        if v is not None and abs(v) >= SALTO_VOLUMEN:
            lineas.append(
                f"El total {'creció' if v > 0 else 'cayó'} {porcentaje(abs(v), 1)} {_frente(t, c)}: de {entero(t.mes_anterior)} a {entero(m)} trámites."
            )
    if t.mismo_mes_anterior:
        v = variacion_relativa(m, t.mismo_mes_anterior)
        if v is not None and abs(v) >= SALTO_VOLUMEN:
            lineas.append(
                f"El volumen del mes está {porcentaje(abs(v), 1)} {'por encima' if v > 0 else 'por debajo'} del de {mes} de {anio - 1} "
                f"({entero(t.mismo_mes_anterior)})."
            )
    principal = tipos[0]
    parte = c.participacion(principal) or 0
    if parte >= CONCENTRACION:
        lineas.append(
            f"{mayuscula_inicial(_bajo(principal))} concentró el {porcentaje(parte, 1)} de los trámites del mes ({entero(principal.mes)}): "
            "lo que pase con ese trámite mueve el total general."
        )
    n = cuantos_para([s.mes or 0 for s in tipos])
    if len(tipos) > 2 and n < len(tipos):
        lineas.append(
            f"{mayuscula_inicial(numero_en_palabras(n, femenino=False))} de los {numero_en_palabras(len(tipos), femenino=False)} tipos con datos "
            f"({lista_en_prosa([_bajo(s) for s in tipos[:n]])}) {'explica' if n == 1 else 'explican'} el "
            f"{porcentaje(sum(c.participacion(s) or 0 for s in tipos[:n]), 1)} del volumen del mes."
        )
    for s in tipos:
        if s.mes_anterior and s.mes_anterior >= UMBRAL_TIPO:
            v = variacion_relativa(s.mes, s.mes_anterior)
            if v is not None and abs(v) >= SALTO_TIPO:
                lineas.append(
                    f"{mayuscula_inicial(_bajo(s))} {'creció' if v > 0 else 'cayó'} {porcentaje(abs(v), 1)} {_frente(s, c)}: de "
                    f"{entero(s.mes_anterior)} a {entero(s.mes)} trámites."
                )
    for s in tipos:
        mayor = s.mes_mayor
        if mayor and len(s.serie_anio) >= 3 and mayor[0] == c.periodo and (s.mes or 0) >= UMBRAL_TIPO:
            lineas.append(
                f"{mayuscula_inicial(_bajo(s))} tuvo en {mes} su mes más alto de {anio}, con {entero(s.mes)} trámites."
            )
    mayor, menor = t.mes_mayor, t.mes_menor
    if mayor and menor and mayor[0] != menor[0] and len(t.serie_anio) >= 3:
        lineas.append(
            f"En {anio} el mes más alto fue {nombre_mes(mayor[0])} ({entero(mayor[1])}) y el más bajo {nombre_mes(menor[0])} "
            f"({entero(menor[1])}): una diferencia de {entero(mayor[1] - menor[1])} trámites entre los dos."
        )
    descontinuados = [s for s in c.tipos if s.ultimo_periodo and s.ultimo_periodo < c.periodo]
    if descontinuados:
        lineas.append(
            f"{mayuscula_inicial(lista_en_prosa([_bajo(s) for s in descontinuados]))} no "
            f"{'tiene' if len(descontinuados) == 1 else 'tienen'} datos en {mes}: {_hasta(descontinuados)}."
        )
    if t.acumulado_anterior and t.meses_acumulado >= 2:
        v = variacion_relativa(t.acumulado, t.acumulado_anterior)
        if v is not None and abs(v) >= SALTO_ACUMULADO:
            lineas.append(
                f"El acumulado de {tramo_del_anio(c.periodo)} de {anio} ({entero(t.acumulado)}) está {porcentaje(abs(v), 1)} "
                f"{'por encima' if v > 0 else 'por debajo'} del mismo tramo de {anio - 1} ({entero(t.acumulado_anterior)})."
            )
    return lineas[:10]


def recomendaciones(c: Calculo) -> list[str]:
    t = c.total
    anio = c.anio
    tipos = c.tipos_del_mes
    lineas: list[str] = []
    if t.mes_anterior:
        v = variacion_relativa(t.mes, t.mes_anterior)
        if v is not None and v <= -SALTO_VOLUMEN:
            lineas.append(
                f"Revisar con las áreas si la caída del total {_frente(t, c)} responde a la estacionalidad del servicio o a un cambio en el "
                "registro, para no leer como menor demanda lo que es un rezago de carga."
            )
        elif v is not None and v >= SALTO_VOLUMEN:
            lineas.append(
                f"Prever la capacidad de atención para los meses siguientes: el total creció {porcentaje(v, 1)} {_frente(t, c)} y, si se "
                "sostiene, la carga del equipo cambia."
            )
    crecen = [
        s
        for s in tipos
        if s.mes_anterior
        and s.mes_anterior >= UMBRAL_TIPO
        and (variacion_relativa(s.mes, s.mes_anterior) or 0) >= SALTO_TIPO
    ]
    if crecen:
        lineas.append(
            f"Ajustar la dotación de {lista_en_prosa([_bajo(s) for s in crecen])}, que {'creció' if len(crecen) == 1 else 'crecieron'} más "
            "del 20 % frente al mes anterior, para que el tiempo de respuesta no se resienta."
        )
    principal = tipos[0]
    if (c.participacion(principal) or 0) >= CONCENTRACION:
        lineas.append(
            f"Seguir {_bajo(principal)} con un indicador propio de capacidad y tiempos, porque concentra más de la mitad de los trámites y "
            "define el total general."
        )
    descontinuados = [s for s in c.tipos if s.ultimo_periodo and s.ultimo_periodo < c.periodo]
    if descontinuados:
        lineas.append(
            f"Confirmar con las áreas si {lista_en_prosa([_bajo(s) for s in descontinuados])} "
            f"{'dejó' if len(descontinuados) == 1 else 'dejaron'} de gestionarse o solo de registrarse, y cerrar o reactivar su serie en la fuente."
        )
    if t.promedio_mensual and len(t.serie_anio) >= 2:
        mayor, menor = t.mes_mayor, t.mes_menor
        if mayor and menor and menor[1] and mayor[1] / menor[1] - 1 >= 0.5:
            lineas.append(
                f"Planear la operación de {anio + 1} con la estacionalidad de {anio}: entre el mes más bajo ({nombre_mes(menor[0])}) y el "
                f"más alto ({nombre_mes(mayor[0])}) hubo una diferencia de {porcentaje(mayor[1] / menor[1] - 1, 1)}."
            )
    lineas.append(
        "Mantener el seguimiento mensual por tipo de trámite con este informe y el interactivo, y registrar los meses nuevos con la misma "
        "forma de la fuente (tipo, mes y cantidad) para que la serie siga siendo comparable."
    )
    lineas.append(
        "Acordar con las áreas una definición única de cada tipo de trámite y de lo que cuenta como trámite gestionado, para que lo "
        "medido sea lo mismo mes a mes."
    )
    return lineas[:7]


def conclusiones(c: Calculo) -> list[str]:
    t = c.total
    mes = mes_y_anio(c.periodo)
    anio = c.anio
    m = t.mes or 0
    tipos = c.tipos_del_mes
    p1 = f"En {mes} el Ministerio gestionó {entero(m)} trámites"
    if t.mes_anterior:
        p1 += f", {variacion(m, t.mes_anterior)} frente a {nombre_mes(t.periodo_anterior)}"
    if t.mismo_mes_anterior:
        p1 += f" y {variacion(m, t.mismo_mes_anterior)} frente a {mes.split(' de ')[0]} de {anio - 1}"
    if t.promedio_mensual and len(t.serie_anio) >= 2:
        lado = "por encima" if m >= t.promedio_mensual else "por debajo"
        p1 += f"; el mes quedó {lado} del promedio mensual de {anio} ({decimal(t.promedio_mensual, 1)})"
    p1 += "."
    principal = tipos[0]
    p2 = f"Por tipo, {_bajo(principal)} fue el trámite principal ({entero(principal.mes)}, {porcentaje(c.participacion(principal), 1)} del total)"
    con_par = [s for s in tipos if s.mes_anterior and s.mes_anterior >= UMBRAL_TIPO]
    if con_par:
        mas = max(con_par, key=lambda s: variacion_relativa(s.mes, s.mes_anterior) or 0)
        menos = min(con_par, key=lambda s: variacion_relativa(s.mes, s.mes_anterior) or 0)
        if mas is not menos:
            p2 += (
                f"; el que más creció {_frente(mas, c)} fue {_bajo(mas)} ({variacion(mas.mes, mas.mes_anterior)}) y el que más bajó, "
                f"{_bajo(menos)} ({variacion(menos.mes, menos.mes_anterior)})"
            )
    p2 += "."
    p3 = ""
    if t.meses_acumulado >= 2:
        p3 = f"{entre_tramo(c.periodo)} de {anio} se gestionaron {entero(t.acumulado)} trámites"
        if t.acumulado_anterior:
            p3 += f", {variacion(t.acumulado, t.acumulado_anterior)} frente al mismo tramo de {anio - 1}"
        p3 += ". "
    p3 += "El informe interactivo de la plataforma permite seguir cada tipo de trámite mes a mes con las mismas cifras de este documento."
    return [p1, p2, p3]


def redactar(c: Calculo, parametros: dict[str, str] | None = None) -> Textos:
    del parametros  # los umbrales de trámites siguen siendo internos (P-36); la firma es la misma de los otros informes
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
