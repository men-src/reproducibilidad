"""La redacción del Informe de Canales de Atención: párrafos en tercera persona, lenguaje neutro y claro, que salen de
las cifras del mes con reglas explícitas. Resumen ejecutivo, hallazgos de portada, objetivos, metodología, glosario,
observaciones, recomendaciones y conclusiones. Nada se escribe a mano para un mes concreto: todo vale para cualquier
mes, y lo que no existe en un mes (un canal sin datos, un año anterior que no hay) no se promete."""

from __future__ import annotations

from men_platform.publicaciones.datos_canales import CONTACTO, Calculo, SerieCanal
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
    porcentaje,
    puntos,
    puntos_sin_signo,
    tramo_del_anio,
    variacion,
    variacion_relativa,
)

NIVEL_ATENCION_META = 0.95  # por debajo, el nivel de atención de un canal de contacto merece observación
ABANDONO_ALTO = 0.05
SERVICIO_BAJO = (
    0.90  # valor interno; lo reemplaza ref.parametro nivel_servicio_objetivo_canales cuando se defina (D-82, P-20)
)
EFECTIVIDAD_BAJA = 0.90
RESOLUCION_BAJA = 0.80
UMBRAL_RECIBIDAS = 50  # recibidas mínimas para juzgar el nivel de un canal en el mes
SALTO_VOLUMEN = 0.15  # variación relativa que se considera un cambio fuerte de un mes al otro
SALTO_ACUMULADO = 0.10
DESVIO_PROMEDIO = 0.20


def _dif(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def _sube_baja(delta: float | None, sube: str = "subió", baja: str = "bajó", igual: str = "se mantuvo") -> str:
    if delta is None or abs(delta) < 0.00005:
        return igual
    return sube if delta > 0 else baja


def _frente(s: SerieCanal, c: Calculo) -> str:
    """«frente a agosto» o «frente al mes anterior con datos (noviembre de 2025)»."""
    if s.periodo_anterior is None:
        return ""
    if s.periodo_anterior == c.periodo_anterior_str():
        return f"frente a {nombre_mes(s.periodo_anterior)}"
    return f"frente al mes anterior con datos ({mes_y_anio(s.periodo_anterior)})"


def _nombres_contacto() -> str:
    return lista_en_prosa([c.nombre.lower() for c in CONTACTO])


def resumen(c: Calculo) -> list[str]:
    todos, k = c.todos, c.contacto
    m, ant, mismo = todos.mes, todos.mes_anterior, todos.mismo_mes_anterior
    km, kant, kmismo = k.mes, k.mes_anterior, k.mismo_mes_anterior
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    parrafos: list[str] = []

    # 1. volumen total y reparto por canal
    con_datos = [s for s in c.canales if s.mes is not None]
    orden = sorted(con_datos, key=lambda s: -s.mes.recibidas)
    partes = [
        f"{'el chatbot' if s.canal.tipo == 'chatbot' else s.nombre.lower()} {entero(s.mes.recibidas)} ({porcentaje(s.mes.recibidas / m.recibidas, 1)})"
        for s in orden[:3]
    ]
    frase = (
        f"En {mes} los canales de atención del Ministerio de Educación Nacional recibieron {entero(m.recibidas)} interacciones "
        f"entre {len(con_datos)} canales con datos; los de mayor volumen fueron {lista_en_prosa(partes)}"
    )
    comparaciones = []
    if ant:
        comparaciones.append(
            f"{variacion(m.recibidas, ant.recibidas)} frente a {nombre_mes(todos.periodo_anterior)} ({entero(ant.recibidas)})"
        )
    if mismo:
        comparaciones.append(
            f"{variacion(m.recibidas, mismo.recibidas)} frente a {nombre_mes(c.periodo)} de {anio_ant} ({entero(mismo.recibidas)})"
        )
    frase += (". El total del mes " + " y ".join(comparaciones) if comparaciones else "") + "."
    parrafos.append(frase)

    # 2. niveles de los canales de contacto
    if km:
        frase = (
            f"Los cuatro canales de contacto ({_nombres_contacto()}) recibieron {entero(km.recibidas)} interacciones y atendieron "
            f"{entero(km.atendidas)}: un nivel de atención de {porcentaje(km.nivel_atencion)}, un nivel de servicio de "
            f"{porcentaje(km.nivel_servicio)} y un nivel de abandono de {porcentaje(km.nivel_abandono)}"
        )
        if kant:
            d = _dif(km.nivel_atencion, kant.nivel_atencion)
            ds = _dif(km.nivel_servicio, kant.nivel_servicio)
            senal = frase_senal(serie_hasta(k.serie_13, c.periodo, lambda x: x.nivel_atencion), porcentaje, PORCENTAJE)
            frase += (
                f". Frente a {nombre_mes(k.periodo_anterior)}, el nivel de atención {_sube_baja(d)} {puntos_sin_signo(d)} (de "
                f"{porcentaje(kant.nivel_atencion)} a {porcentaje(km.nivel_atencion)}){senal} y el nivel de servicio {_sube_baja(ds)} {puntos_sin_signo(ds)}"
            )
        if kmismo:
            d = _dif(km.nivel_atencion, kmismo.nivel_atencion)
            frase += (
                f"; frente a {nombre_mes(c.periodo)} de {anio_ant} ({porcentaje(kmismo.nivel_atencion)} de atención), "
                f"{_sube_baja(d)} {puntos_sin_signo(d)}"
            )
        parrafos.append(frase + ".")

        # 3. el reparto entre los canales de contacto y el mejor y peor nivel
        contacto = [s for s in c.por_tipo("contacto") if s.mes is not None]
        if contacto:
            mayor = max(contacto, key=lambda s: s.mes.recibidas)
            frase = (
                f"{mayor.nombre} concentró el {porcentaje(mayor.mes.recibidas / km.recibidas, 1)} de las interacciones de contacto "
                f"({entero(mayor.mes.recibidas)}, {porcentaje(mayor.mes.nivel_atencion)} atendidas)"
            )
            con_volumen = [s for s in contacto if s.mes.recibidas >= UMBRAL_RECIBIDAS]
            if len(con_volumen) >= 2:
                mejor = max(con_volumen, key=lambda s: s.mes.nivel_atencion or 0)
                peor = min(con_volumen, key=lambda s: s.mes.nivel_atencion or 0)
                if mejor is not peor:
                    frase += (
                        f"; entre los canales con al menos {UMBRAL_RECIBIDAS} interacciones, el mejor nivel de atención fue el de "
                        f"{mejor.nombre.lower()} ({porcentaje(mejor.mes.nivel_atencion)}) y el menor el de {peor.nombre.lower()} "
                        f"({porcentaje(peor.mes.nivel_atencion)}, con {entero(peor.mes.abandonadas)} abandonadas)"
                    )
            parrafos.append(frase + ".")

    # 4. chatbot, devolución, buzón y presencial
    frases = []
    bot = c.canal(5)
    if bot.mes:
        b = bot.mes
        frase = (
            f"El chatbot registró {entero(b.recibidas)} transacciones y {entero(b.preguntas)} conversaciones, con una resolución de "
            f"{porcentaje(b.resolucion)} ({entero(b.preguntas_resueltas)} resueltas sin pasar a un agente y {entero(b.preguntas_no_resueltas)} transferidas)"
        )
        if bot.mes_anterior:
            frase += f", {puntos(_dif(b.resolucion, bot.mes_anterior.resolucion))} {_frente(bot, c)}"
        frases.append(frase)
    for id_ in (6, 8):
        s = c.canal(id_)
        if s.mes:
            t = s.mes
            frases.append(
                f"{'La devolución de llamadas' if id_ == 6 else 'El buzón de voz'} recibió {entero(t.recibidas)} {s.canal.recibidas} y logró "
                f"{entero(t.atendidas)} llamadas efectivas, una efectividad de {porcentaje(t.efectividad)}"
                + (
                    f" ({puntos(_dif(t.efectividad, s.mes_anterior.efectividad))} {_frente(s, c)})"
                    if s.mes_anterior
                    else ""
                )
            )
    pres = c.canal(7)
    if pres.mes:
        frase = f"La atención presencial registró {entero(pres.mes.recibidas)} atenciones en ventanilla"
        if pres.mes_anterior:
            frase += f" ({variacion(pres.mes.recibidas, pres.mes_anterior.recibidas)} {_frente(pres, c)})"
        frase += f"; el promedio mensual de {anio} es de {decimal(pres.acumulado.promedio_mensual, 1)} atenciones"
        frases.append(frase)
    if frases:
        parrafos.append(". ".join(mayuscula_inicial(f) for f in frases) + ".")

    # 5. acumulado del año
    acu, acu_ant = todos.acumulado, todos.acumulado_anterior
    frase = f"{entre_tramo(c.periodo)} de {anio} los canales recibieron {entero(acu.recibidas)} interacciones"
    if acu_ant:
        frase += f", {variacion(acu.recibidas, acu_ant.recibidas)} frente a los mismos meses de {anio_ant} ({entero(acu_ant.recibidas)})"
    if k.acumulado.recibidas:
        frase += (
            f"; en los canales de contacto el nivel de atención acumulado es de {porcentaje(k.acumulado.nivel_atencion)} y el de servicio de "
            f"{porcentaje(k.acumulado.nivel_servicio)}"
        )
        if k.acumulado_anterior:
            d = _dif(k.acumulado.nivel_atencion, k.acumulado_anterior.nivel_atencion)
            frase += f" ({puntos(d)} de atención frente al mismo tramo de {anio_ant}, {porcentaje(k.acumulado_anterior.nivel_atencion)})"
    parrafos.append(frase + ".")
    return parrafos


def hallazgos(c: Calculo) -> list[str]:
    """Las cinco líneas de «En síntesis» de la portada, cortas para que quepan en una línea."""
    todos, k = c.todos, c.contacto
    m, km = todos.mes, k.mes
    lineas = [f"{entero(m.recibidas)} interacciones recibidas en {len([s for s in c.canales if s.mes])} canales"]
    if todos.mes_anterior:
        lineas[0] += (
            f" ({variacion(m.recibidas, todos.mes_anterior.recibidas)} frente a {nombre_mes(todos.periodo_anterior)})"
        )
    if km:
        atencion = f"{porcentaje(km.nivel_atencion)} de nivel de atención en los canales de contacto"
        if k.mes_anterior:
            atencion += f" ({puntos(_dif(km.nivel_atencion, k.mes_anterior.nivel_atencion))})"
        lineas.append(atencion)
        lineas.append(
            f"{porcentaje(km.nivel_servicio)} de nivel de servicio y {porcentaje(km.nivel_abandono)} de abandono"
        )
    bot = c.canal(5)
    if bot.mes:
        lineas.append(
            f"Chatbot: {entero(bot.mes.recibidas)} transacciones, {porcentaje(bot.mes.resolucion)} resueltas sin agente"
        )
    acu = todos.acumulado
    linea = f"{entero(acu.recibidas)} interacciones acumuladas en {c.anio}"
    if k.acumulado.recibidas:
        linea += f", {porcentaje(k.acumulado.nivel_atencion)} de atención"
    lineas.append(linea)
    return lineas[:5]


def objetivos(c: Calculo) -> tuple[str, list[str]]:
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    general = (
        f"Presentar los resultados de los canales de atención del Ministerio de Educación Nacional en {mes}: cuántas interacciones "
        "recibió cada canal, cuántas atendió y con qué niveles de atención, de servicio y de abandono, para que la entidad conozca el "
        "desempeño de su atención a la ciudadanía por canal y tome decisiones sobre su operación."
    )
    todos = c.todos
    partes = []
    if todos.mes_anterior:
        partes.append(f"con {nombre_mes(todos.periodo_anterior)}, el mes inmediatamente anterior")
    if todos.mismo_mes_anterior:
        partes.append(f"con {nombre_mes(c.periodo)} de {anio_ant}")
    especificos = [
        f"Cuantificar las interacciones recibidas y atendidas en cada canal en {mes}"
        + (f" y compararlas {lista_en_prosa(partes)}" if partes else "")
        + ".",
        "Medir los niveles de atención, de servicio y de abandono de los canales de contacto, la resolución del chatbot y la "
        "efectividad de la devolución de llamadas y del buzón de voz, con las fórmulas que usa el informe interactivo.",
        f"Describir la evolución mes a mes de {anio}"
        + (f" frente a {anio_ant}" if any(s.serie_anio_anterior for s in c.canales) else "")
        + ", la mezcla de canales y el comportamiento de cada canal en sus meses con datos.",
        "Identificar los canales y los meses con mejor y peor desempeño y proponer acciones a la entidad.",
    ]
    return general, especificos


def metodologia(c: Calculo) -> list[tuple[str, str]]:
    mes = mes_y_anio(c.periodo)
    anio, anio_ant = c.anio, c.anio - 1
    todos = c.todos
    tramo = tramo_del_anio(c.periodo)
    comparaciones = "El informe es mensual"
    if todos.mes_anterior:
        comparaciones += f": el mes se compara en primer lugar con el mes inmediatamente anterior ({nombre_mes(todos.periodo_anterior)}), canal por canal"
    if todos.mismo_mes_anterior or todos.acumulado_anterior:
        comparaciones += f"; después, con el mismo mes de {anio_ant} y con el acumulado de {tramo} de {anio} frente a los mismos meses de {anio_ant}"
    comparaciones += (
        ". Las variaciones de volumen se expresan en porcentaje y las de los niveles en puntos porcentuales (pp). Cuando un canal no "
        "tiene datos en el mes calendario anterior, se compara con su mes anterior con datos y el informe lo dice."
    )
    return [
        (
            "Fuentes",
            "Las tablas mensuales de la base del centro de contacto del Ministerio (una fila por mes y canal para la atención telefónica, "
            "el chat, la llamada virtual, la video llamada virtual, el chatbot y la devolución de llamadas), la tabla de trámites para la "
            "atención presencial y, desde agosto de 2026, el informe mensual de gestión del operador del centro de contacto, del que se "
            "transcriben los meses nuevos de todos los canales. Este informe lee los mismos agregados mensuales por canal que alimentan el "
            f"informe interactivo, con corte al {fecha_larga(c.fecha_corte)}.",
        ),
        (
            "Unidad de medida",
            "La interacción recibida en cada canal: las llamadas, chats, llamadas virtuales y video llamadas que llegan a los canales de "
            "contacto; las transacciones (conversaciones iniciadas) del chatbot; las solicitudes de llamada de la devolución de llamadas y "
            "los mensajes del buzón de voz; y las atenciones en ventanilla de la atención presencial. Cada interacción se cuenta en el mes "
            "en que la registró su fuente.",
        ),
        (
            "Fórmulas",
            "Nivel de atención: interacciones atendidas sobre recibidas. Nivel de servicio: interacciones contestadas antes del tiempo "
            "objetivo sobre recibidas. Nivel de abandono: interacciones que el ciudadano abandonó antes de ser atendido sobre recibidas. "
            "Resolución del chatbot: lo resuelto sin pasar a un agente sobre lo resuelto más lo transferido a un agente. Efectividad de la "
            "devolución de llamadas y del buzón de voz: llamadas efectivas sobre solicitudes (o mensajes). Son las mismas fórmulas del "
            "informe interactivo.",
        ),
        (
            "Alcance por canal",
            "Los tres niveles existen solo en los cuatro canales de contacto, que son los únicos con tiempo objetivo y abandono. El chatbot "
            "reporta transacciones, conversaciones y resolución; la devolución de llamadas y el buzón de voz, solicitudes, llamadas "
            "efectivas y no efectivas; la atención presencial, solo sus atenciones. Las cifras de todos los canales se suman únicamente para "
            "el volumen total; los niveles del conjunto son los de los canales de contacto.",
        ),
        (
            "Meses con datos",
            "Cada canal se mira en sus meses con datos: una fuente puede llegar hasta un mes distinto que otra y un canal puede no haber "
            "operado en algunos meses (el chatbot no tuvo servicio entre diciembre de 2025 y marzo de 2026; el buzón de voz existe desde "
            "febrero de 2026). Por eso las series de cada canal, sus promedios y sus "
            "comparaciones excluyen los meses sin datos en vez de mostrarlos como ceros.",
        ),
        ("Comparaciones", comparaciones),
        (
            "Procesamiento",
            f"Los agregados se publican en la plataforma con cada actualización de datos; este informe de {mes} se generó de forma "
            "automática a partir de ellos: las cifras, los gráficos y los textos salen de reglas fijas, iguales para todos los meses, y no se "
            "corrigen a mano; las inconsistencias de la fuente se publican tal como llegan.",
        ),
    ]


def glosario() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    terminos = [
        (
            "Abandonada",
            "Interacción que el ciudadano dejó antes de ser atendido por un agente; en la devolución de llamadas y el buzón de voz, llamada "
            "de vuelta en la que no se logró contactar al ciudadano.",
        ),
        (
            "Atendida",
            "Interacción contestada por un agente; en la devolución de llamadas y el buzón de voz, llamada de vuelta efectiva; en la "
            "atención presencial, ciudadano atendido en ventanilla.",
        ),
        (
            "Buzón de voz",
            "Canal en el que el ciudadano deja un mensaje cuando la línea no está disponible y la entidad lo llama después.",
        ),
        (
            "Canal de atención",
            "Medio por el que la ciudadanía se comunica con el Ministerio: atención telefónica, chat, llamada virtual, video llamada "
            "virtual, chatbot, devolución de llamadas, atención presencial y buzón de voz.",
        ),
        (
            "Canal de contacto",
            "Los canales con un agente en línea y tiempo objetivo de respuesta: atención telefónica, chat de atención al ciudadano, llamada "
            "virtual y video llamada virtual. Son los únicos con niveles de atención, de servicio y de abandono.",
        ),
        ("Chatbot", "Asistente automático que responde a la ciudadanía por chat; lo que no resuelve pasa a un agente."),
        (
            "Devolución de llamadas",
            "Canal en el que el ciudadano registra una solicitud (formulario) para que la entidad lo llame.",
        ),
        (
            "Efectividad",
            "Llamadas efectivas sobre solicitudes (devolución de llamadas) o sobre mensajes (buzón de voz).",
        ),
        (
            "Interacción",
            "Cada contacto de un ciudadano con un canal: una llamada, un chat, una transacción del chatbot, una solicitud de llamada, un "
            "mensaje o una atención presencial.",
        ),
        (
            "Media móvil simple",
            "Promedio de las interacciones recibidas en los tres meses anteriores con datos, sin el mes evaluado; sirve de referencia para "
            "saber si un mes está por encima o por debajo de su tendencia reciente.",
        ),
        ("Nivel de abandono", "Interacciones abandonadas sobre recibidas; subir es empeorar."),
        ("Nivel de atención", "Interacciones atendidas sobre recibidas."),
        ("Nivel de servicio", "Interacciones contestadas antes del tiempo objetivo sobre recibidas."),
        (
            "Recibida",
            "Interacción que llegó al canal en el mes: llamada, chat, llamada virtual, video llamada, transacción, solicitud, mensaje o "
            "atención.",
        ),
        (
            "Resolución",
            "En el chatbot, lo resuelto sin pasar a un agente sobre lo resuelto más lo transferido a un agente.",
        ),
        (
            "Tiempo objetivo",
            "Tiempo máximo de espera que fija la operación del centro de contacto para contestar una interacción; las contestadas antes de "
            "ese tiempo cuentan en el nivel de servicio.",
        ),
        ("Transacción", "En el chatbot, una conversación iniciada por un ciudadano."),
        (
            "Variación",
            "Cambio de una cifra frente a otra: en porcentaje para los volúmenes y en puntos porcentuales para los niveles.",
        ),
    ]
    siglas = [
        ("MEN", "Ministerio de Educación Nacional."),
        ("NS", "Nivel de servicio; las «transacciones NS» son las contestadas antes del tiempo objetivo."),
        ("pp", "Puntos porcentuales: diferencia aritmética entre dos porcentajes."),
        ("SRC", "Subdirección de Relacionamiento con la Ciudadanía, que publica este informe."),
    ]
    return terminos, siglas


def _peor_mes_contacto(c: Calculo) -> tuple[str, float, int] | None:
    """El mes del año con el nivel de atención más bajo de los canales de contacto, si es distinto del mes del informe."""
    serie = [(p, t) for p, t in c.contacto.serie_anio if t.nivel_atencion is not None]
    if len(serie) < 2:
        return None
    p, t = min(serie, key=lambda pt: pt[1].nivel_atencion)
    if p == c.periodo:
        return None
    return p, t.nivel_atencion, t.abandonadas


def observaciones(c: Calculo) -> list[str]:
    todos, k = c.todos, c.contacto
    mes = nombre_mes(c.periodo)
    anio = c.anio
    lineas: list[str] = []
    km = k.mes
    if km:
        if km.nivel_atencion is not None and km.nivel_atencion < NIVEL_ATENCION_META:
            lineas.append(
                f"El nivel de atención de los canales de contacto, {porcentaje(km.nivel_atencion)}, quedó por debajo del "
                f"{porcentaje(NIVEL_ATENCION_META, 0)}: {entero(km.abandonadas)} interacciones no llegaron a un agente."
            )
        else:
            lineas.append(
                f"Los canales de contacto atendieron {porcentaje(km.nivel_atencion)} de lo recibido en {mes}; solo {entero(km.abandonadas)} "
                f"de {entero(km.recibidas)} interacciones se abandonaron antes de ser atendidas."
            )
        if km.nivel_servicio is not None and km.nivel_servicio < SERVICIO_BAJO:
            lineas.append(
                f"El nivel de servicio del conjunto fue de {porcentaje(km.nivel_servicio)}: {entero(km.recibidas - km.en_nivel_servicio)} "
                "interacciones esperaron más del tiempo objetivo, aunque la mayoría se atendió."
            )
        if k.mes_anterior:
            d = _dif(km.nivel_atencion, k.mes_anterior.nivel_atencion)
            if d is not None and abs(d) >= 0.005:
                lineas.append(
                    f"El nivel de atención de contacto {_sube_baja(d)} {puntos_sin_signo(d)} frente a {nombre_mes(k.periodo_anterior)}, de "
                    f"{porcentaje(k.mes_anterior.nivel_atencion)} a {porcentaje(km.nivel_atencion)}."
                )
        if k.mismo_mes_anterior:
            d = _dif(km.nivel_atencion, k.mismo_mes_anterior.nivel_atencion)
            if d is not None and abs(d) >= 0.005:
                lineas.append(
                    f"Frente a {mes} de {anio - 1}, el nivel de atención de contacto {_sube_baja(d, 'está', 'está', 'está igual')} "
                    f"{puntos_sin_signo(d)} {'por encima' if d > 0 else 'por debajo'} ({porcentaje(k.mismo_mes_anterior.nivel_atencion)} entonces)."
                )
    peor = _peor_mes_contacto(c)
    if peor and peor[1] < SERVICIO_BAJO:
        lineas.append(
            f"El nivel de atención de contacto más bajo de {anio} fue el de {nombre_mes(peor[0])} ({porcentaje(peor[1])}, con {entero(peor[2])} "
            f"abandonadas); desde entonces se recuperó hasta {porcentaje(km.nivel_atencion) if km else '–'} en {mes}."
        )
    if k.acumulado.recibidas and k.acumulado.nivel_servicio is not None and k.acumulado.nivel_servicio < SERVICIO_BAJO:
        lineas.append(
            f"En lo corrido de {anio} el nivel de servicio acumulado de los canales de contacto es de {porcentaje(k.acumulado.nivel_servicio)}, "
            f"frente a un nivel de atención acumulado de {porcentaje(k.acumulado.nivel_atencion)}: la espera, no la falta de respuesta, es la brecha del año."
        )
    for s in c.por_tipo("contacto"):
        if s.mes is None or s.mes.recibidas < UMBRAL_RECIBIDAS:
            continue
        t = s.mes
        if t.nivel_abandono is not None and t.nivel_abandono >= ABANDONO_ALTO:
            lineas.append(
                f"{s.nombre} tuvo un nivel de abandono de {porcentaje(t.nivel_abandono)} ({entero(t.abandonadas)} de {entero(t.recibidas)}), por "
                "encima del 5 % que marca la revisión de la capacidad del canal."
            )
        if (
            t.nivel_servicio is not None
            and t.nivel_servicio < SERVICIO_BAJO
            and (t.nivel_atencion or 0) >= NIVEL_ATENCION_META
        ):
            lineas.append(
                f"En {s.nombre.lower()} se atendió {porcentaje(t.nivel_atencion)} pero solo {porcentaje(t.nivel_servicio)} dentro del tiempo "
                "objetivo: el canal responde, pero con espera."
            )
    contacto_con_abandonos = [s for s in c.por_tipo("contacto") if s.mes and s.mes.abandonadas > 0]
    if contacto_con_abandonos and km and km.abandonadas:
        mayor = max(contacto_con_abandonos, key=lambda s: s.mes.abandonadas)
        lineas.append(
            f"De las {entero(km.abandonadas)} interacciones abandonadas en los canales de contacto, {entero(mayor.mes.abandonadas)} "
            f"({porcentaje(mayor.mes.abandonadas / km.abandonadas, 1)}) fueron de {mayor.nombre.lower()}, el canal de mayor volumen."
        )
    for s in c.canales:
        if s.mes and s.mes_anterior and s.mes_anterior.recibidas >= UMBRAL_RECIBIDAS:
            v = variacion_relativa(s.mes.recibidas, s.mes_anterior.recibidas)
            if v is not None and abs(v) >= SALTO_VOLUMEN:
                lineas.append(
                    f"{s.nombre} {'creció' if v > 0 else 'cayó'} {porcentaje(abs(v), 1)} {_frente(s, c)}: de {entero(s.mes_anterior.recibidas)} a "
                    f"{entero(s.mes.recibidas)} {s.canal.recibidas}."
                )
    bot = c.canal(5)
    if bot.mes and bot.mes.resolucion is not None:
        if bot.mes.resolucion < RESOLUCION_BAJA:
            lineas.append(
                f"El chatbot resolvió sin agente solo {porcentaje(bot.mes.resolucion)} de lo que atendió: {entero(bot.mes.preguntas_no_resueltas)} "
                "chats pasaron a un agente."
            )
        else:
            lineas.append(
                f"El chatbot resolvió sin agente {porcentaje(bot.mes.resolucion)} de sus chats; {entero(bot.mes.preguntas_no_resueltas)} pasaron a un agente."
            )
    if bot.serie_anio and len(bot.serie_anio) < len(todos.serie_anio):
        lineas.append(
            f"El chatbot tiene datos en {len(bot.serie_anio)} de los {len(todos.serie_anio)} meses de {anio} con datos "
            f"({lista_en_prosa([nombre_mes(p) for p, _ in bot.serie_anio])}): los acumulados del año y la comparación con {anio - 1} lo subestiman."
        )
    for id_ in (6, 8):
        s = c.canal(id_)
        if s.mes and s.mes.recibidas >= 10 and s.mes.efectividad is not None and s.mes.efectividad < EFECTIVIDAD_BAJA:
            lineas.append(
                f"La efectividad de {s.nombre.lower()} fue de {porcentaje(s.mes.efectividad)}: en {entero(s.mes.abandonadas)} de "
                f"{entero(s.mes.recibidas)} {s.canal.recibidas} no se logró contactar al ciudadano."
            )
    pres = c.canal(7)
    if pres.mes and pres.acumulado.promedio_mensual:
        desvio = pres.mes.recibidas / pres.acumulado.promedio_mensual - 1
        if abs(desvio) >= DESVIO_PROMEDIO:
            lineas.append(
                f"La atención presencial de {mes} ({entero(pres.mes.recibidas)}) quedó {porcentaje(abs(desvio), 1)} "
                f"{'por encima' if desvio > 0 else 'por debajo'} del promedio mensual de {anio} ({decimal(pres.acumulado.promedio_mensual, 1)})."
            )
    sin_mes = [s for s in c.canales if s.mes is None]
    if sin_mes:
        lineas.append(
            f"{lista_en_prosa([s.nombre for s in sin_mes])} no {'tiene' if len(sin_mes) == 1 else 'tienen'} datos en {mes}: su último mes con datos es "
            f"{lista_en_prosa([mes_y_anio(s.ultimo_periodo) for s in sin_mes if s.ultimo_periodo])}."
        )
    if todos.mismo_mes_anterior:
        v = variacion_relativa(todos.mes.recibidas, todos.mismo_mes_anterior.recibidas)
        if v is not None and abs(v) >= SALTO_VOLUMEN:
            lineas.append(
                f"El volumen total del mes está {porcentaje(abs(v), 1)} {'por encima' if v > 0 else 'por debajo'} del de {mes} de {anio - 1} "
                f"({entero(todos.mismo_mes_anterior.recibidas)})."
            )
    if todos.acumulado_anterior:
        v = variacion_relativa(todos.acumulado.recibidas, todos.acumulado_anterior.recibidas)
        if v is not None and abs(v) >= SALTO_ACUMULADO:
            lineas.append(
                f"El acumulado de {tramo_del_anio(c.periodo)} de {anio} ({entero(todos.acumulado.recibidas)}) está {porcentaje(abs(v), 1)} "
                f"{'por encima' if v > 0 else 'por debajo'} del mismo tramo de {anio - 1} ({entero(todos.acumulado_anterior.recibidas)})."
            )
    return lineas[:10]


def recomendaciones(c: Calculo) -> list[str]:
    todos, k = c.todos, c.contacto
    km = k.mes
    anio = c.anio
    lineas: list[str] = []
    if km and km.nivel_atencion is not None and km.nivel_atencion < NIVEL_ATENCION_META:
        lineas.append(
            "Revisar la dotación de agentes en las franjas de mayor demanda de los canales de contacto, para que el nivel de atención "
            "vuelva a superar el 95 %."
        )
    if km and km.nivel_servicio is not None and km.nivel_servicio < SERVICIO_BAJO:
        lineas.append(
            "Acordar con el operador del centro de contacto un plan para reducir la espera: el nivel de servicio mide la rapidez, y bajó "
            "aunque la atención se mantuvo."
        )
    elif (
        k.acumulado.recibidas and k.acumulado.nivel_servicio is not None and k.acumulado.nivel_servicio < SERVICIO_BAJO
    ):
        lineas.append(
            f"Fijar con el operador una meta de nivel de servicio y seguirla mes a mes: el acumulado de {anio} "
            f"({porcentaje(k.acumulado.nivel_servicio)}) está por debajo del 90 % aunque los últimos meses lo superen."
        )
    peor = _peor_mes_contacto(c)
    if peor and peor[1] < SERVICIO_BAJO:
        lineas.append(
            f"Documentar con el operador qué ocurrió en {nombre_mes(peor[0])} de {anio} ({porcentaje(peor[1])} de atención, "
            f"{entero(peor[2])} abandonadas) y qué se corrigió, para que no se repita en los meses de mayor demanda."
        )
    altos = [
        s
        for s in c.por_tipo("contacto")
        if s.mes and s.mes.recibidas >= UMBRAL_RECIBIDAS and (s.mes.nivel_abandono or 0) >= ABANDONO_ALTO
    ]
    if altos:
        lineas.append(
            f"Analizar en {lista_en_prosa([s.nombre.lower() for s in altos])} en qué momento se abandonan las interacciones (espera, "
            "menú, horario) y ajustar la operación en esa franja."
        )
    bot = c.canal(5)
    if bot.mes and bot.mes.resolucion is not None and bot.mes.resolucion < RESOLUCION_BAJA:
        lineas.append(
            "Revisar las preguntas que el chatbot transfiere a un agente y ampliar sus respuestas, para que resuelva más sin pasar a una persona."
        )
    bajas = [
        s
        for id_ in (6, 8)
        for s in [c.canal(id_)]
        if s.mes and s.mes.recibidas >= 10 and (s.mes.efectividad or 0) < EFECTIVIDAD_BAJA
    ]
    if bajas:
        lineas.append(
            f"Reintentar en otro horario las llamadas no efectivas de {lista_en_prosa([s.nombre.lower() for s in bajas])} y confirmar los "
            "números de contacto al registrar la solicitud, para subir la efectividad por encima del 90 %."
        )
    if bot.serie_anio and len(bot.serie_anio) < len(todos.serie_anio):
        lineas.append(
            f"Completar en la plataforma los meses del chatbot que faltan en {anio} (en particular febrero y marzo de 2026, que están en informes "
            "anteriores del operador), para que los acumulados del año sean comparables."
        )
    lineas.append(
        "Mantener el seguimiento mensual canal por canal con este informe y el interactivo, y revisar con el operador los meses en que la "
        "fuente no cuadra (atendidas más abandonadas distinto de recibidas)."
    )
    lineas.append(
        "Confirmar con el área las fórmulas de los niveles y el tiempo objetivo del nivel de servicio, para que el informe mida lo que la "
        "operación gestiona."
    )
    return lineas[:7]


def conclusiones(c: Calculo) -> list[str]:
    todos, k = c.todos, c.contacto
    mes = mes_y_anio(c.periodo)
    anio = c.anio
    m, km = todos.mes, k.mes
    p1 = f"En {mes} los canales de atención del Ministerio recibieron {entero(m.recibidas)} interacciones"
    if todos.mes_anterior:
        p1 += f", {variacion(m.recibidas, todos.mes_anterior.recibidas)} frente a {nombre_mes(todos.periodo_anterior)}"
    if km:
        p1 += (
            f". Los canales de contacto atendieron {porcentaje(km.nivel_atencion)} de lo recibido y contestaron {porcentaje(km.nivel_servicio)} "
            f"dentro del tiempo objetivo, con un abandono de {porcentaje(km.nivel_abandono)}"
        )
    p1 += "."
    contacto = [s for s in c.por_tipo("contacto") if s.mes and s.mes.recibidas >= UMBRAL_RECIBIDAS]
    p2 = ""
    if contacto:
        mejor = max(contacto, key=lambda s: s.mes.nivel_atencion or 0)
        peor = min(contacto, key=lambda s: s.mes.nivel_atencion or 0)
        p2 = f"Por canal, {mejor.nombre.lower()} tuvo el mejor nivel de atención ({porcentaje(mejor.mes.nivel_atencion)})"
        if peor is not mejor:
            p2 += f" y {peor.nombre.lower()} el menor ({porcentaje(peor.mes.nivel_atencion)})"
        bot = c.canal(5)
        if bot.mes:
            p2 += f"; el chatbot resolvió sin agente {porcentaje(bot.mes.resolucion)} de sus chats"
        p2 += "."
    acu = todos.acumulado
    p3 = f"{entre_tramo(c.periodo)} de {anio} se recibieron {entero(acu.recibidas)} interacciones"
    if k.acumulado.recibidas:
        p3 += f", con un nivel de atención acumulado de {porcentaje(k.acumulado.nivel_atencion)} en los canales de contacto"
        if k.acumulado_anterior:
            d = _dif(k.acumulado.nivel_atencion, k.acumulado_anterior.nivel_atencion)
            p3 += f", {puntos(d)} frente al mismo tramo de {anio - 1}"
    p3 += ". El informe interactivo de la plataforma permite seguir cada canal mes a mes con las mismas cifras de este documento."
    return [p for p in (p1, p2, p3) if p]


def _aplicar_parametros(parametros: dict[str, str] | None) -> None:
    """El objetivo del nivel de servicio sale de ref.parametro cuando está definido (D-82); «sin definir» conserva el interno."""
    global SERVICIO_BAJO  # umbral del módulo: lo leen las observaciones y las recomendaciones
    SERVICIO_BAJO = parametro_numerico(parametros, "nivel_servicio_objetivo_canales", SERVICIO_BAJO)


def redactar(c: Calculo, parametros: dict[str, str] | None = None) -> Textos:
    _aplicar_parametros(parametros)
    general, especificos = objetivos(c)
    terminos, siglas = glosario()
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
