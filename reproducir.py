"""Regenera un informe en PDF de la Plataforma de Analítica de Datos del Ministerio de Educación Nacional desde los
agregados publicados y comprueba que sale el mismo archivo, byte a byte, que el publicado.

uso (en una máquina limpia, dentro del entorno del paquete):
    python reproducir.py --informe legalizaciones --mes 2026-09
    python reproducir.py --informe pqrsdf --mes 2026-09 --api datos_sinteticos/api/v1 --sin-comparar
    python reproducir.py --informe canales --mes 2026-09 --api https://men-src.github.io/canales-atencion/

Con --api apuntando a un sitio publicado (o sin --api) descarga los JSON de api/v1 que el informe necesita, genera el
PDF en --salida y lo compara con el PDF publicado en el sitio de su informe (--comparar acepta otra URL o un archivo). Con --api
apuntando a una carpeta usa esos datos tal cual (por ejemplo los sintéticos) y no compara salvo que se pida."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

INFORMES = {
    # informe: (sitio publicado, bases de api/v1 que lee, módulo de datos, módulo del informe, nombre del PDF)
    "pqrsdf": (
        "https://men-src.github.io/pqrsdf/",
        ("vencimiento", "radicacion"),
        "datos_pqrsdf",
        "informe_pqrsdf",
        "informe-general-pqrsdf-{mes}.pdf",
    ),
    "canales": (
        "https://men-src.github.io/canales-atencion/",
        ("canales",),
        "datos_canales",
        "informe_canales",
        "informe-canales-atencion-{mes}.pdf",
    ),
    "tramites": (
        "https://men-src.github.io/tramites/",
        ("tramites",),
        "datos_tramites",
        "informe_tramites",
        "informe-tramites-{mes}.pdf",
    ),
    "legalizaciones": (
        "https://men-src.github.io/legalizaciones/",
        ("legalizaciones",),
        "datos_legalizaciones",
        "informe_legalizaciones",
        "informe-legalizaciones-{mes}.pdf",
    ),
}
COMUNES = ("dimensiones.json", "manifiesto.json", "revisiones.json")
POR_BASE = {
    "vencimiento": ("cubo.json", "cubo-ejes.json", "pronostico.json", "resumen.json"),
    "radicacion": ("cubo.json",),
    "canales": ("cubo.json", "resumen.json"),
    "tramites": ("cubo.json", "resumen.json"),
    "legalizaciones": ("cubo.json", "resumen.json"),
}
# cada informe publica sus PDF en un sitio propio (D-116); hasta el 2026-11-10 vivían en la carpeta publicaciones/ del portal
SITIO_PDF = "https://men-src.github.io/publicaciones-{informe}/"


def huella(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def descargar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as respuesta:  # noqa: S310 - https de GitHub Pages o la URL que dio el usuario
        destino.write_bytes(respuesta.read())


def preparar_api(informe: str, origen: str, carpeta: Path) -> Path:
    """Deja en `carpeta` la api/v1 que el informe necesita: descargada del sitio o copiada de una carpeta local."""
    sitio, bases, *_ = INFORMES[informe]
    if not origen.startswith("http"):
        return Path(origen)
    base = origen if origen.endswith("/") else origen + "/"
    api = carpeta / "api" / "v1"
    for nombre in COMUNES:
        descargar(f"{base}api/v1/{nombre}", api / nombre)
    for b in bases:
        for nombre in POR_BASE[b]:
            descargar(f"{base}api/v1/{b}/{nombre}", api / b / nombre)
    return api


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--informe", required=True, choices=sorted(INFORMES))
    p.add_argument("--mes", required=True, help="AAAA-MM")
    p.add_argument(
        "--api", default=None, help="sitio publicado (URL) o carpeta api/v1; por defecto el sitio del informe"
    )
    p.add_argument("--salida", default="salida", help="carpeta donde queda el PDF regenerado y la api descargada")
    p.add_argument(
        "--comparar",
        default=None,
        help="PDF publicado (URL o archivo) con el que se compara; por defecto el del sitio de PDF del informe",
    )
    p.add_argument("--sin-comparar", action="store_true")
    a = p.parse_args()

    sitio, _, modulo_datos, modulo_informe, patron = INFORMES[a.informe]
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    api = preparar_api(a.informe, a.api or sitio, salida)
    manifiesto = (
        json.loads((api / "manifiesto.json").read_text(encoding="utf-8")) if (api / "manifiesto.json").exists() else {}
    )
    print(
        f"api: {api} · exportación {manifiesto.get('exportacion_id')} · commit {str(manifiesto.get('commit_git'))[:12]}"
    )

    datos = __import__(f"men_platform.publicaciones.{modulo_datos}", fromlist=["cargar", "calcular"])
    informe = __import__(f"men_platform.publicaciones.{modulo_informe}", fromlist=["generar"])
    from men_platform.publicaciones.procedencia import cargar as cargar_procedencia

    fuente = datos.cargar(api)
    calculo = datos.calcular(fuente, f"{a.mes}-01")
    pdf = salida / patron.format(mes=a.mes)
    informe.generar(calculo, pdf, procedencia=cargar_procedencia(api))
    propia = huella(pdf)
    print(f"PDF regenerado: {pdf} ({pdf.stat().st_size // 1024} KB) · SHA-256 {propia}")

    if a.sin_comparar or (a.api and not a.api.startswith("http") and not a.comparar):
        return 0
    referencia = a.comparar or SITIO_PDF.format(informe=a.informe) + patron.format(mes=a.mes)
    publicado = salida / ("publicado-" + patron.format(mes=a.mes))
    if referencia.startswith("http"):
        descargar(referencia, publicado)
    else:
        publicado = Path(referencia)
    ajena = huella(publicado)
    print(f"PDF publicado:  {referencia} · SHA-256 {ajena}")
    if propia == ajena:
        print("IGUALES: el PDF publicado se reproduce byte a byte desde los agregados publicados.")
        return 0
    print(
        "DIFIEREN: revise las versiones de las dependencias (requirements.txt) y que la api corresponda a la exportación del PDF."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
