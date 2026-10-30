"""La base común de los informes en PDF (D-73, D-74): las fuentes Inter, los estilos, el lienzo con «Página X de Y», la
plantilla con portada y páginas normales (cabecera, pie e índice) y el constructor con las piezas de la historia:
párrafos, títulos, gráficos, tablas, listas, tarjetas de resultados y glosario. Cada informe aporta su portada, sus
textos y sus secciones. Carta, Inter, la paleta de la plataforma; cada título y cada subtítulo empieza en una página
nueva (el primer subtítulo de una sección comparte la página con su título)."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as lienzo
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# PDF reproducibles (D-81): sin fecha de creación ni identificador aleatorio en el archivo, así dos generaciones desde la
# misma exportación dan los mismos bytes.
rl_config.invariant = 1

RECURSOS = Path(__file__).parent / "recursos"
AZUL = colors.HexColor("#1e5bbd")
NOCHE = colors.HexColor("#0c2543")
TINTA = colors.HexColor("#0f1d35")
GRIS = colors.HexColor("#4a5a78")
GRIS_TENUE = colors.HexColor("#7b89a6")
FILETE = colors.HexColor("#dde4ef")
PAPEL = colors.HexColor("#f3f6fa")
AMARILLO = colors.HexColor("#fecc0b")
ROJO = colors.HexColor("#cf1433")
BLANCO = colors.white

ANCHO_PAGINA, ALTO_PAGINA = letter
MARGEN = 2.2 * cm
# La portada: el bloque azul con el título empieza 5,2 cm bajo el margen y mide 9,2 cm. La miniatura de la tarjeta
# del informe en la pestaña Publicaciones recorta la portada desde arriba hasta el borde inferior de ese bloque.
ALTO_BLOQUE_PORTADA = 9.2 * cm
ALTO_MINIATURA = MARGEN + 5.2 * cm + ALTO_BLOQUE_PORTADA
ANCHO_UTIL = ANCHO_PAGINA - 2 * MARGEN

ENTIDAD = "Ministerio de Educación Nacional"
AREA = "Subdirección de Relacionamiento con la Ciudadanía"
PLATAFORMA = "Plataforma de Analítica de Datos"

_fuentes_listas = False


def registrar_fuentes() -> None:
    global _fuentes_listas  # noqa: PLW0603
    if _fuentes_listas:
        return
    carpeta = RECURSOS / "fuentes"
    for nombre, archivo in [
        ("Inter", "Inter-Regular.ttf"),
        ("Inter-Medium", "Inter-Medium.ttf"),
        ("Inter-SemiBold", "Inter-SemiBold.ttf"),
        ("Inter-Bold", "Inter-Bold.ttf"),
        ("Inter-Italic", "Inter-Italic.ttf"),
    ]:
        pdfmetrics.registerFont(TTFont(nombre, str(carpeta / archivo)))
    pdfmetrics.registerFontFamily(
        "Inter", normal="Inter", bold="Inter-Bold", italic="Inter-Italic", boldItalic="Inter-Bold"
    )
    _fuentes_listas = True


def estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "Cuerpo", fontName="Inter", fontSize=10, leading=15, textColor=TINTA, alignment=TA_JUSTIFY, spaceAfter=7
    )
    return {
        "Cuerpo": base,
        "CuerpoIzq": ParagraphStyle("CuerpoIzq", parent=base, alignment=TA_LEFT),
        "Titulo1": ParagraphStyle(
            "Titulo1", fontName="Inter-Bold", fontSize=24, leading=29, textColor=AZUL, spaceAfter=14, spaceBefore=0
        ),
        "Titulo2": ParagraphStyle(
            "Titulo2", fontName="Inter-SemiBold", fontSize=17, leading=22, textColor=NOCHE, spaceAfter=10, spaceBefore=6
        ),
        "TituloToc": ParagraphStyle(
            "TituloToc", fontName="Inter-Bold", fontSize=24, leading=29, textColor=AZUL, spaceAfter=14
        ),
        "Bajada": ParagraphStyle(
            "Bajada", parent=base, fontName="Inter", fontSize=10.5, leading=16, textColor=GRIS, spaceAfter=10
        ),
        "Interpretacion": ParagraphStyle("Interpretacion", parent=base, spaceBefore=2, spaceAfter=12),
        "Nota": ParagraphStyle(
            "Nota", parent=base, fontSize=8.5, leading=12, textColor=GRIS, alignment=TA_LEFT, spaceAfter=4
        ),
        "Leyenda": ParagraphStyle(
            "Leyenda",
            parent=base,
            fontName="Inter-Medium",
            fontSize=8.5,
            leading=12,
            textColor=GRIS,
            alignment=TA_LEFT,
            spaceBefore=2,
            spaceAfter=6,
        ),
        "Celda": ParagraphStyle("Celda", parent=base, fontSize=8.5, leading=11, alignment=TA_LEFT, spaceAfter=0),
        "CeldaDer": ParagraphStyle("CeldaDer", parent=base, fontSize=8.5, leading=11, alignment=TA_RIGHT, spaceAfter=0),
        "CeldaCab": ParagraphStyle(
            "CeldaCab",
            parent=base,
            fontName="Inter-SemiBold",
            fontSize=8.5,
            leading=11,
            textColor=BLANCO,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "CeldaCabDer": ParagraphStyle(
            "CeldaCabDer",
            parent=base,
            fontName="Inter-SemiBold",
            fontSize=8.5,
            leading=11,
            textColor=BLANCO,
            alignment=TA_RIGHT,
            spaceAfter=0,
        ),
        "TarjetaTitulo": ParagraphStyle(
            "TarjetaTitulo",
            fontName="Inter-Medium",
            fontSize=8,
            leading=10,
            textColor=GRIS,
            alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "TarjetaValor": ParagraphStyle(
            "TarjetaValor",
            fontName="Inter-Bold",
            fontSize=18,
            leading=22,
            textColor=AZUL,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "TarjetaNota": ParagraphStyle(
            "TarjetaNota", fontName="Inter", fontSize=7.1, leading=9.5, textColor=GRIS, alignment=TA_LEFT, spaceAfter=0
        ),
        "Toc0": ParagraphStyle(
            "Toc0", fontName="Inter-SemiBold", fontSize=10.5, leading=16, textColor=TINTA, spaceBefore=4
        ),
        "Toc1": ParagraphStyle("Toc1", fontName="Inter", fontSize=10, leading=14, textColor=GRIS, leftIndent=16),
        "Centro": ParagraphStyle("Centro", parent=base, alignment=TA_CENTER),
    }


def _franja_tricolor(canv: lienzo.Canvas, y: float) -> None:
    """La franja de la bandera (2:1:1), de borde a borde."""
    canv.setFillColor(AMARILLO)
    canv.rect(0, y, ANCHO_PAGINA / 2, 0.45 * cm, stroke=0, fill=1)
    canv.setFillColor(AZUL)
    canv.rect(ANCHO_PAGINA / 2, y, ANCHO_PAGINA / 4, 0.45 * cm, stroke=0, fill=1)
    canv.setFillColor(ROJO)
    canv.rect(3 * ANCHO_PAGINA / 4, y, ANCHO_PAGINA / 4, 0.45 * cm, stroke=0, fill=1)


def dibujar_cabecera_portada(
    canv: lienzo.Canvas,
    lineas_titulo: list[str],
    subtitulo: str,
    lineas_descripcion: list[str],
    pie_bloque: str | None,
) -> float:
    """La parte alta de la portada, común a los informes y a las portadas «En preparación» (D-74): las franjas
    tricolor arriba y abajo, el logo con solo el nombre de la entidad y el bloque azul con el título en dos líneas, el
    subtítulo (el mes) y la descripción. Devuelve la ordenada del borde inferior del bloque azul, hasta donde llega la
    miniatura de la pestaña Publicaciones."""
    for y in (ALTO_PAGINA - 0.45 * cm, 0):
        _franja_tricolor(canv, y)
    logo = ImageReader(str(RECURSOS / "logo_men.png"))
    canv.drawImage(logo, MARGEN, ALTO_PAGINA - MARGEN - 3.2 * cm, width=2.6 * cm, height=2.6 * cm, mask="auto")
    # solo el logo y la entidad, centrados entre sí (pedido del patrocinador, 2026-10-29): sin el área ni la plataforma
    canv.setFillColor(NOCHE)
    canv.setFont("Inter-SemiBold", 20)
    canv.drawString(MARGEN + 3.1 * cm, ALTO_PAGINA - MARGEN - 2.15 * cm, ENTIDAD)
    alto_bloque = ALTO_BLOQUE_PORTADA
    y_bloque = ALTO_PAGINA - ALTO_MINIATURA
    canv.setFillColor(AZUL)
    canv.rect(0, y_bloque, ANCHO_PAGINA, alto_bloque, stroke=0, fill=1)
    canv.setFillColor(BLANCO)
    canv.setFont("Inter-Bold", 36)
    for i, linea in enumerate(lineas_titulo[:2]):
        canv.drawString(MARGEN, y_bloque + alto_bloque - (2.4 + 1.5 * i) * cm, linea)
    canv.setFont("Inter-SemiBold", 22)
    canv.drawString(MARGEN, y_bloque + alto_bloque - 5.6 * cm, subtitulo)
    canv.setFont("Inter", 11.5)
    for i, linea in enumerate(lineas_descripcion[:2]):
        canv.drawString(MARGEN, y_bloque + alto_bloque - 6.9 * cm - i * 0.55 * cm, linea)
    if pie_bloque:
        canv.setFont("Inter-Medium", 10)
        canv.setFillColor(colors.HexColor("#d4e1f7"))
        canv.drawString(MARGEN, y_bloque + 0.8 * cm, pie_bloque)
    return y_bloque


@dataclass
class Portada:
    """Lo que cambia de un informe a otro en la portada."""

    lineas_titulo: list[str]
    mes: str  # «Septiembre de 2026»
    lineas_descripcion: list[str]
    fecha_corte: str  # fecha larga
    cifras: list[tuple[str, str]]  # tres (valor, rótulo)
    hallazgos: list[str]
    url: str
    # «Cifra provisional» cuando el mes todavía puede cambiar (D-81); va junto a la fecha de corte
    nota_corte: str | None = None


@dataclass
class Cabecera:
    """Lo que va en la cabecera y el pie de las páginas normales."""

    titulo_informe: str
    mes: str
    fecha_corte: str  # fecha larga


class Lienzo(lienzo.Canvas):
    """Lienzo que, al guardar, escribe «Página X de Y» en todas las páginas menos la portada."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self._estados: list[dict] = []

    def showPage(self) -> None:  # noqa: N802 - API de reportlab
        self._estados.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._estados)
        for estado in self._estados:
            self.__dict__.update(estado)
            if self._pageNumber > 1:
                self.setFont("Inter", 8)
                self.setFillColor(GRIS)
                self.drawRightString(ANCHO_PAGINA - MARGEN, 1.3 * cm, f"Página {self._pageNumber} de {total}")
            lienzo.Canvas.showPage(self)
        lienzo.Canvas.save(self)


class Documento(BaseDocTemplate):
    """Plantilla con portada y páginas normales; avisa al índice de cada título y subtítulo."""

    def __init__(self, archivo: str, portada: Portada, cabecera: Cabecera, **kwargs) -> None:  # noqa: ANN003
        super().__init__(
            archivo,
            pagesize=letter,
            leftMargin=MARGEN,
            rightMargin=MARGEN,
            topMargin=MARGEN + 0.4 * cm,
            bottomMargin=MARGEN,
            **kwargs,
        )
        self.portada = portada
        self.cabecera = cabecera
        marco = Frame(
            MARGEN,
            MARGEN,
            ANCHO_UTIL,
            ALTO_PAGINA - 2 * MARGEN - 0.4 * cm,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        marco_portada = Frame(
            MARGEN,
            MARGEN,
            ANCHO_UTIL,
            ALTO_PAGINA - 2 * MARGEN,
            id="portada",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(
            [
                PageTemplate(id="Portada", frames=[marco_portada], onPage=self._portada),
                PageTemplate(id="Normal", frames=[marco], onPage=self._pagina),
            ]
        )

    def afterFlowable(self, flowable) -> None:  # noqa: ANN001, N802 - API de reportlab
        if isinstance(flowable, Paragraph) and flowable.style.name in ("Titulo1", "Titulo2"):
            nivel = 0 if flowable.style.name == "Titulo1" else 1
            texto = flowable.getPlainText()
            # la clave debe ser la misma en cada pasada de multiBuild, si no el índice nunca se estabiliza
            clave = f"titulo-{nivel}-{texto[:40]}".replace(" ", "-")
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=nivel, closed=False)
            self.notify("TOCEntry", (nivel, texto, self.page, clave))

    def _portada(self, canv: lienzo.Canvas, _doc: BaseDocTemplate) -> None:
        p = self.portada
        canv.saveState()
        datos_al = f"Datos al {p.fecha_corte}" + (f"  ·  {p.nota_corte}" if p.nota_corte else "")
        y_bloque = dibujar_cabecera_portada(canv, p.lineas_titulo, p.mes, p.lineas_descripcion, datos_al)
        # las cifras del mes, en tres columnas
        y_cifras = y_bloque - 2.3 * cm
        ancho_col = ANCHO_UTIL / 3
        for i, (valor, rotulo) in enumerate(p.cifras[:3]):
            x = MARGEN + i * ancho_col
            canv.setFillColor(AZUL)
            canv.setFont("Inter-Bold", 26)
            canv.drawString(x, y_cifras, valor)
            canv.setFillColor(GRIS)
            canv.setFont("Inter", 9.5)
            canv.drawString(x, y_cifras - 0.6 * cm, rotulo)
        canv.setStrokeColor(FILETE)
        canv.setLineWidth(0.8)
        canv.line(MARGEN, y_cifras - 1.3 * cm, ANCHO_PAGINA - MARGEN, y_cifras - 1.3 * cm)
        # los hallazgos
        canv.setFillColor(NOCHE)
        canv.setFont("Inter-SemiBold", 10.5)
        canv.drawString(MARGEN, y_cifras - 2.3 * cm, "En síntesis")
        canv.setFont("Inter", 10)
        canv.setFillColor(TINTA)
        for i, hallazgo in enumerate(p.hallazgos[:5]):
            canv.drawString(MARGEN + 0.4 * cm, y_cifras - 3.0 * cm - i * 0.58 * cm, f"•  {hallazgo}")
        # pie de portada
        canv.setFont("Inter", 8.5)
        canv.setFillColor(GRIS)
        # si el área, la ciudad y la dirección no caben en una línea, la ciudad se omite
        izquierda = f"{AREA}  ·  Bogotá D. C., Colombia"
        if canv.stringWidth(izquierda, "Inter", 8.5) + canv.stringWidth(p.url, "Inter", 8.5) + 0.6 * cm > ANCHO_UTIL:
            izquierda = AREA
        canv.drawString(MARGEN, 1.4 * cm, izquierda)
        canv.drawRightString(ANCHO_PAGINA - MARGEN, 1.4 * cm, p.url)
        canv.restoreState()

    def _pagina(self, canv: lienzo.Canvas, _doc: BaseDocTemplate) -> None:
        c = self.cabecera
        canv.saveState()
        canv.setFont("Inter-Medium", 8)
        canv.setFillColor(GRIS)
        canv.drawString(MARGEN, ALTO_PAGINA - MARGEN + 0.25 * cm, f"{c.titulo_informe}  ·  {c.mes}")
        canv.drawRightString(ANCHO_PAGINA - MARGEN, ALTO_PAGINA - MARGEN + 0.25 * cm, ENTIDAD)
        canv.setStrokeColor(FILETE)
        canv.setLineWidth(0.6)
        canv.line(MARGEN, ALTO_PAGINA - MARGEN, ANCHO_PAGINA - MARGEN, ALTO_PAGINA - MARGEN)
        canv.line(MARGEN, 1.75 * cm, ANCHO_PAGINA - MARGEN, 1.75 * cm)
        canv.setFont("Inter", 8)
        canv.drawString(MARGEN, 1.3 * cm, f"{AREA}  ·  Datos al {c.fecha_corte}")
        canv.restoreState()


class Constructor:
    """Arma la historia del documento llevando la cuenta de gráficos y tablas; cada informe hereda y agrega sus secciones."""

    def __init__(self) -> None:
        self.estilos = estilos()
        self.historia: list = []
        self.graficos = 0
        self.tablas = 0
        self.ultimo_fue_titulo1 = False

    # --- piezas -----------------------------------------------------------------------------------------------
    def p(self, texto: str, estilo: str = "Cuerpo") -> None:
        self.historia.append(Paragraph(texto, self.estilos[estilo]))

    def interpretacion(self, texto: str) -> None:
        """La lectura de la pieza que la precede (gráfico o tabla)."""
        self.historia.append(Paragraph(escape(texto), self.estilos["Interpretacion"]))

    def titulo1(self, texto: str) -> None:
        self.historia.append(PageBreak())
        self.historia.append(Paragraph(escape(texto), self.estilos["Titulo1"]))
        self.ultimo_fue_titulo1 = True

    def titulo2(self, texto: str, bajada: str | None = None) -> None:
        # cada subtítulo empieza en una página nueva; el primero de una sección comparte la página con su título
        if not self.ultimo_fue_titulo1:
            self.historia.append(PageBreak())
        self.ultimo_fue_titulo1 = False
        self.historia.append(Paragraph(escape(texto), self.estilos["Titulo2"]))
        if bajada:
            self.p(escape(bajada), "Bajada")

    def espacio(self, alto: float = 0.3) -> None:
        self.historia.append(Spacer(1, alto * cm))

    def indice(self) -> None:
        """La página de la tabla de contenido, después de la portada."""
        h = self.historia
        h.append(NextPageTemplate("Normal"))
        h.append(PageBreak())
        h.append(Paragraph("Tabla de contenido", self.estilos["TituloToc"]))
        toc = TableOfContents()
        toc.levelStyles = [self.estilos["Toc0"], self.estilos["Toc1"]]
        toc.dotsMinLevel = 0
        h.append(toc)

    def grafico(self, png: bytes, leyenda: str, lectura: str, ancho: float = ANCHO_UTIL) -> None:
        self.graficos += 1
        lector = ImageReader(io.BytesIO(png))
        w, h = lector.getSize()
        alto = ancho * h / w
        maximo = 10.5 * cm
        if alto > maximo:
            ancho, alto = ancho * maximo / alto, maximo
        imagen = Image(io.BytesIO(png), width=ancho, height=alto)
        imagen.hAlign = "LEFT"
        self.historia.append(
            KeepTogether([imagen, Paragraph(f"Gráfico {self.graficos}. {escape(leyenda)}", self.estilos["Leyenda"])])
        )
        self.interpretacion(lectura)

    def tabla(
        self,
        leyenda: str,
        encabezados: list[str],
        filas: list[list[str]],
        anchos: list[float],
        lectura: str | None = None,
        numericas: set[int] | None = None,
        resaltar: int | None = None,
        compacta: bool = False,
    ) -> None:
        """Tabla con leyenda arriba e interpretación abajo; `numericas` son las columnas a la derecha; `resaltar` una fila en negrita; `compacta`, menos relleno lateral para tablas de muchas columnas."""
        self.tablas += 1
        numericas = numericas or set()
        e = self.estilos
        cab = [
            Paragraph(escape(h), e["CeldaCabDer" if i in numericas else "CeldaCab"]) for i, h in enumerate(encabezados)
        ]
        cuerpo = []
        for r, fila in enumerate(filas):
            celdas = []
            for i, valor in enumerate(fila):
                texto = escape(str(valor))
                if resaltar is not None and r == resaltar:
                    texto = f"<b>{texto}</b>"
                celdas.append(Paragraph(texto, e["CeldaDer" if i in numericas else "Celda"]))
            cuerpo.append(celdas)
        total = sum(anchos)
        anchos_pt = [ANCHO_UTIL * a / total for a in anchos]
        t = Table([cab, *cuerpo], colWidths=anchos_pt, repeatRows=1, hAlign="LEFT")
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, AZUL),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, FILETE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5 if compacta else 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 if compacta else 5),
        ]
        for r in range(1, len(cuerpo) + 1):
            if r % 2 == 0:
                estilo.append(("BACKGROUND", (0, r), (-1, r), PAPEL))
        if resaltar is not None:
            estilo.append(("BACKGROUND", (0, resaltar + 1), (-1, resaltar + 1), colors.HexColor("#ecf2fb")))
        t.setStyle(TableStyle(estilo))
        leyenda_p = Paragraph(f"Tabla {self.tablas}. {escape(leyenda)}", e["Leyenda"])
        if len(filas) <= 12:
            self.historia.append(KeepTogether([leyenda_p, t]))
        else:
            self.historia.append(leyenda_p)
            self.historia.append(t)
        self.espacio(0.15)
        if lectura:
            self.interpretacion(lectura)

    def lista(self, elementos: list[str], numerada: bool = False) -> None:
        items = [ListItem(Paragraph(escape(x), self.estilos["Cuerpo"]), leftIndent=14) for x in elementos]
        self.historia.append(
            ListFlowable(
                items,
                bulletType="1" if numerada else "bullet",
                start="1" if numerada else None,
                bulletFontName="Inter",
                bulletFontSize=9,
                leftIndent=14,
                bulletColor=AZUL,
            )
        )
        self.espacio(0.2)

    def tarjeta(self, titulo: str, valor: str, lineas: list[str]) -> list:
        """Una tarjeta de resultados: el rótulo, el valor en grande y las líneas de comparación."""
        e = self.estilos
        return [
            Paragraph(escape(titulo), e["TarjetaTitulo"]),
            Paragraph(escape(valor), e["TarjetaValor"]),
            *[Paragraph(escape(x), e["TarjetaNota"]) for x in lineas],
        ]

    def tarjetas(self, leyenda: str, tarjetas: list[list], por_fila: int = 4) -> None:
        """Las tarjetas de resultados en filas de `por_fila`, sobre papel con un filete azul arriba."""
        filas = [tarjetas[i : i + por_fila] for i in range(0, len(tarjetas), por_fila)]
        hueco = 0.25 * cm
        ancho = (ANCHO_UTIL - hueco * (por_fila - 1)) / por_fila
        # columnas de separación en blanco entre tarjetas; la última fila se completa con celdas vacías
        filas_con_huecos = []
        for fila in filas:
            fila = [*fila, *([""] * (por_fila - len(fila)))]
            filas_con_huecos.append([celda for par in zip(fila, [""] * len(fila), strict=True) for celda in par][:-1])
        anchos = [ancho if i % 2 == 0 else hueco for i in range(2 * por_fila - 1)]
        t = Table(filas_con_huecos, colWidths=anchos, hAlign="LEFT")
        estilo = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        for r, fila in enumerate(filas):
            for i in range(0, 2 * len(fila) - 1, 2):
                estilo.append(("BACKGROUND", (i, r), (i, r), PAPEL))
                estilo.append(("LINEABOVE", (i, r), (i, r), 2, AZUL))
        t.setStyle(TableStyle(estilo))
        self.historia.append(KeepTogether([Paragraph(escape(leyenda), self.estilos["Leyenda"]), t]))
        self.historia.append(Spacer(1, 0.25 * cm))

    def glosario(self, numero: int, terminos: list[tuple[str, str]], siglas: list[tuple[str, str]]) -> None:
        self.titulo1(f"{numero}. Glosario de términos y siglas")
        self.p(
            "Los términos con que se escriben las cifras de este informe y las siglas que aparecen en él, en orden alfabético.",
            "Bajada",
        )
        self.tabla("Términos", ["Término", "Definición"], [[a, b] for a, b in terminos], [1.6, 4.4])
        self.tabla("Siglas", ["Sigla", "Significado"], [[a, b] for a, b in siglas], [1, 5])


def generar_pdf(destino: Path, portada: Portada, cabecera: Cabecera, historia: list, titulo: str, asunto: str) -> Path:
    """Escribe el PDF en `destino` con la portada, la cabecera y la historia dadas, y devuelve su ruta."""
    registrar_fuentes()
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc = Documento(
        str(destino), portada, cabecera, title=titulo, author=f"{ENTIDAD} · {AREA}", subject=asunto, creator=PLATAFORMA
    )
    doc.multiBuild(historia, canvasmaker=Lienzo)
    return destino
