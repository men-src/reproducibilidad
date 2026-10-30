# Paquete de reproducibilidad · Plataforma de Analítica de Datos (Ministerio de Educación Nacional)

Este paquete permite a cualquier persona regenerar, en una máquina limpia, un informe en PDF de la plataforma a partir de los agregados que ya están publicados en los sitios de los informes, y comprobar que el archivo sale byte a byte igual al publicado en el portal (https://men-src.github.io/). También trae datos sintéticos para probar el flujo sin red y sin datos reales.

Lo que contiene:

- `men_platform/`: el código que genera los PDF (capa `publicaciones` y `estadistica`), con las fuentes Inter y el logo. No incluye ingestión, base de datos ni credenciales.
- `requirements.txt`: las versiones exactas de las dependencias con las que se generaron los PDF publicados. La reproducción byte a byte depende de ellas.
- `reproducir.py`: descarga los JSON de `api/v1`, genera el PDF y compara la huella SHA-256 con el publicado.
- `generar_datos_sinteticos.py` y `datos_sinteticos/`: una `api/v1` inventada con la misma estructura, para correr el flujo sin red.
- `VERSION.txt`: el commit y la fecha con que se armó el paquete.

## Máquina limpia, paso a paso (Windows, macOS o Linux)

1. Instale Python 3.13 y `uv` (https://docs.astral.sh/uv/).
2. En la carpeta del paquete:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv -r requirements.txt
```

3. Reproduzca un PDF publicado y compárelo:

```bash
.venv/Scripts/python reproducir.py --informe legalizaciones --mes 2026-09      # Windows
.venv/bin/python reproducir.py --informe legalizaciones --mes 2026-09          # macOS y Linux
```

La salida termina en `IGUALES` cuando la huella del PDF regenerado coincide con la del publicado. Informes disponibles: `pqrsdf`, `canales`, `tramites`, `legalizaciones`; el mes va como `AAAA-MM`.

4. Sin red, con los datos sintéticos:

```bash
.venv/Scripts/python reproducir.py --informe pqrsdf --mes 2026-09 --api datos_sinteticos/api/v1
```

## Qué garantiza y qué no

- El PDF publicado lleva en su ficha técnica la exportación, el commit, la huella de las reglas y la huella del cubo con que se generó (D-81). `reproducir.py` lee la misma exportación desde el sitio: si el sitio ya publicó una exportación posterior, el PDF del portal puede corresponder a la anterior; en ese caso pida la exportación archivada por `api/v1/publicaciones/<n>/...` de la API en vivo o espere la regeneración del PDF.
- La igualdad byte a byte se verificó en Windows con las versiones de `requirements.txt`. Otra plataforma o versiones distintas de matplotlib, reportlab o freetype pueden cambiar bytes de las imágenes sin cambiar ninguna cifra: en ese caso compare el contenido (texto y tablas) y no la huella.
- Los datos sintéticos no describen al Ministerio: sirven para probar el flujo, no para leer cifras.
