"""Genera una api/v1 sintética con la misma estructura que publica la plataforma, para probar la regeneración de los PDF
sin red y sin datos reales (paquete de reproducibilidad, Fase 5).

uso: python generar_datos_sinteticos.py --salida datos_sinteticos/api/v1 [--plantilla plantilla_dimensiones.json]
         [--semilla 2026] [--meses 24]
Toma los catálogos de la plantilla (los ids y la estructura de dimensiones.json publicado), reemplaza los nombres de las
dependencias y de los ejes temáticos por nombres inventados y produce cubos con filas aleatorias pero coherentes (los
estados, los totales y las sumas por tramos cierran). Nada de lo que sale describe al Ministerio."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def escribir(ruta: Path, datos: object) -> str:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    ruta.write_text(texto, encoding="utf-8")
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def repartir(total: int, partes: int, azar: random.Random) -> list[int]:
    """`total` repartido en `partes` enteros no negativos."""
    if partes <= 0:
        return []
    cortes = sorted(azar.randint(0, total) for _ in range(partes - 1))
    return [b - a for a, b in zip([0, *cortes], [*cortes, total], strict=True)]


def periodos_sinteticos(ultimo: date, meses: int) -> list[dict]:
    salida = []
    anio, mes = ultimo.year, ultimo.month
    for _ in range(meses):
        salida.append(
            {
                "periodo": f"{anio:04d}-{mes:02d}-01",
                "anio": anio,
                "mes": mes,
                "nombre_mes": MESES[mes - 1],
                "anio_mes": f"{anio:04d}-{mes:02d}",
                "trimestre": (mes - 1) // 3 + 1,
            }
        )
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return sorted(salida, key=lambda p: p["periodo"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--salida", required=True)
    p.add_argument("--plantilla", default=str(AQUI / "datos_sinteticos" / "plantilla_dimensiones.json"))
    p.add_argument("--semilla", type=int, default=2026)
    p.add_argument("--meses", type=int, default=24)
    a = p.parse_args()
    azar = random.Random(a.semilla)  # noqa: S311 - datos de prueba
    salida = Path(a.salida)
    plantilla = json.loads(Path(a.plantilla).read_text(encoding="utf-8"))

    # --- dimensiones: la estructura de la plantilla, con nombres inventados donde el nombre identifica algo propio -------
    dims = copy.deepcopy(plantilla)
    ultimo = date.fromisoformat(plantilla["periodos"][-1]["periodo"])
    dims["periodos"] = periodos_sinteticos(ultimo, a.meses)
    dims["actualizacion_id"] = 1
    for n, d in enumerate(dims["dependencias"]):
        if d["id"] != 0:
            unidad = f"dependencia {n:02d}" if not d["es_grupo"] else f"grupo {n:02d}"
            d.update(
                {
                    "unidad": unidad,
                    "nombre_historico": unidad,
                    "grupo": unidad if d["es_grupo"] else "sin grupo",
                    "dependencia": d["dependencia"] if d["es_grupo"] else unidad,
                }
            )
    for n, e in enumerate(dims["ejes_tematicos"]):
        if e["id"] not in (0, -1):
            e["nombre"] = f"eje tematico {n:03d}"
    dims["parametros"] = {**plantilla.get("parametros", {}), "publicar_pronostico": "0"}
    periodos = [x["periodo"] for x in dims["periodos"]]
    dependencias = [d["sk"] for d in dims["dependencias"] if d["id"] != 0][:40]
    tipos = [t["id"] for t in dims["tipos_requerimiento"] if t["id"] != 0][:10]
    canales = [c["id"] for c in dims["canales"] if c["id"] != 0]
    ejes = [e["id"] for e in dims["ejes_tematicos"] if e["id"] not in (0, -1)][:60]
    huellas: dict[str, str] = {}
    archivos: list[str] = []

    def guardar(relativa: str, datos: object) -> None:
        huellas[f"api/v1/{relativa}"] = escribir(salida / relativa, datos)
        archivos.append(f"api/v1/{relativa}")

    guardar("dimensiones.json", dims)

    # --- PQRSDF por vencimiento y su cubo de ejes ------------------------------------------------------------------------
    def fila_pqrsdf(periodo: str, radicacion: bool) -> list:
        estado = azar.choices(
            [1, 2, 4] if not radicacion else [1, 2, 3, 4], weights=[80, 12, 8] if not radicacion else [70, 10, 12, 8]
        )[0]
        r = max(1, int(azar.lognormvariate(2.2, 1.0)))
        cerradas = r if estado in (1, 2) else 0
        a_tiempo = r if estado in (1, 3) else 0
        ext = r if estado in (2, 4) else 0
        gestion = sum(azar.randint(1, 15) for _ in range(r)) if cerradas else 0
        retraso = sum(azar.randint(1, 20) for _ in range(ext))
        fila = [
            periodo,
            azar.choice(dependencias),
            azar.choice(tipos),
            azar.choice(canales),
            estado,
            r,
            cerradas,
            a_tiempo,
            ext,
            gestion,
            retraso,
        ]
        if radicacion:
            gestionar_mes = azar.randint(0, r)
            return [*fila, gestionar_mes, azar.randint(gestionar_mes, r)]
        return [*fila, cerradas]

    vencimiento = [fila_pqrsdf(per, False) for per in periodos for _ in range(azar.randint(60, 120))]
    guardar(
        "vencimiento/cubo.json",
        {
            "base": "vencimiento",
            "actualizacion_id": 1,
            "columnas": [
                "periodo",
                "dependencia_sk",
                "tipo_requerimiento_id",
                "canal_id",
                "estado_oportunidad_id",
                "radicados",
                "cerradas",
                "a_tiempo",
                "extemporaneas",
                "dias_habiles_gestion",
                "dias_habiles_retraso",
                "con_respuesta",
            ],
            "filas": vencimiento,
        },
    )
    ejes_filas = []
    for f in vencimiento:
        partes = repartir(f[5], azar.randint(1, 3), azar)
        for parte in partes:
            if parte <= 0:
                continue
            factor = parte / f[5]
            ejes_filas.append(
                [
                    f[0],
                    f[1],
                    f[2],
                    f[4],
                    azar.choice(ejes),
                    parte,
                    round(f[6] * factor),
                    round(f[7] * factor),
                    round(f[8] * factor),
                ]
            )
    guardar(
        "vencimiento/cubo-ejes.json",
        {
            "base": "vencimiento",
            "actualizacion_id": 1,
            "columnas": [
                "periodo",
                "dependencia_sk",
                "tipo_requerimiento_id",
                "estado_oportunidad_id",
                "eje_tematico_sk",
                "radicados",
                "cerradas",
                "a_tiempo",
                "extemporaneas",
            ],
            "filas": ejes_filas,
        },
    )
    guardar(
        "vencimiento/pronostico.json",
        {"base": "vencimiento", "actualizacion_id": 1, "modelo": "sin pronostico (datos sinteticos)", "puntos": []},
    )
    radicacion = [fila_pqrsdf(per, True) for per in periodos for _ in range(azar.randint(50, 100))]
    guardar(
        "radicacion/cubo.json",
        {
            "base": "radicacion",
            "actualizacion_id": 1,
            "columnas": [
                "periodo",
                "dependencia_sk",
                "tipo_requerimiento_id",
                "canal_id",
                "estado_oportunidad_id",
                "radicados",
                "cerradas",
                "a_tiempo",
                "extemporaneas",
                "dias_habiles_gestion",
                "dias_habiles_retraso",
                "a_gestionar_en_mes",
                "a_gestionar_en_trimestre",
            ],
            "filas": radicacion,
        },
    )

    # --- canales de atención ------------------------------------------------------------------------------------------------
    canales_filas = []
    for per in periodos:
        for c in dims["canales_atencion"]:
            if c["id"] == 0 or (c.get("vigente_hasta") and c["vigente_hasta"] < per):
                continue
            if c["tipo"] == "contacto":
                rec = azar.randint(100, 8000)
                ate = azar.randint(int(rec * 0.9), rec)
                ns = azar.randint(int(ate * 0.8), ate)
                canales_filas.append([per, c["id"], rec, ate, ns, rec - ate, None, None, None])
            elif c["tipo"] == "chatbot":
                rec = azar.randint(500, 15000)
                resueltas = azar.randint(int(rec * 0.1), rec)
                canales_filas.append([per, c["id"], rec, None, None, None, int(rec * 1.2), resueltas, rec - resueltas])
            elif c["tipo"] == "callback":
                rec = azar.randint(50, 400)
                ate = azar.randint(int(rec * 0.8), rec)
                canales_filas.append([per, c["id"], rec, ate, None, rec - ate, None, None, None])
            else:
                rec = azar.randint(200, 1500)
                canales_filas.append([per, c["id"], rec, rec, None, None, None, None, None])
    guardar(
        "canales/cubo.json",
        {
            "base": "canales",
            "actualizacion_id": 1,
            "columnas": [
                "periodo",
                "canal_atencion_id",
                "recibidas",
                "atendidas",
                "en_nivel_servicio",
                "abandonadas",
                "preguntas",
                "preguntas_resueltas",
                "preguntas_no_resueltas",
            ],
            "filas": canales_filas,
        },
    )

    # --- trámites ---------------------------------------------------------------------------------------------------------------
    tramites = [t["id"] for t in dims["tramites"] if t["id"] != 0]
    guardar(
        "tramites/cubo.json",
        {
            "base": "tramites",
            "actualizacion_id": 1,
            "columnas": ["periodo", "tramite_id", "cantidad"],
            "filas": [[per, t, azar.randint(50, 20000)] for per in periodos for t in tramites],
        },
    )

    # --- legalizaciones: las sumas por tramos cierran con los documentos con días ------------------------------------------
    metodologias = [m["id"] for m in dims["legalizaciones_metodologias"] if m["id"] != 0]
    documentos = [t["id"] for t in dims["legalizaciones_tipos_documento"] if t["id"] != 0]
    legal = []
    for per in periodos:
        for met in metodologias:
            for doc in azar.sample(documentos, k=min(6, len(documentos))):
                for resultado in (1, 2, 3):
                    if azar.random() < 0.25:
                        continue
                    cantidad = max(1, int(azar.lognormvariate(3.0, 1.2))) if resultado == 1 else azar.randint(1, 40)
                    con_dias = cantidad if resultado in (1, 2) else 0
                    tramos_dias = repartir(con_dias, 7, azar)
                    tramos_habiles = repartir(con_dias, 17, azar)
                    dias_suma = sum(n * d for n, d in zip(tramos_dias, (1, 3, 5, 8, 13, 23, 45), strict=True))
                    habiles_suma = sum(n * d for n, d in zip(tramos_habiles, (*range(16), 20), strict=True))
                    legal.append(
                        [
                            per,
                            met,
                            doc,
                            resultado,
                            cantidad,
                            azar.randint(0, cantidad // 3),
                            azar.randint(0, cantidad // 4),
                            con_dias,
                            dias_suma,
                            habiles_suma,
                            *tramos_dias,
                            *tramos_habiles,
                        ]
                    )
    guardar(
        "legalizaciones/cubo.json",
        {
            "base": "legalizaciones",
            "actualizacion_id": 1,
            "columnas": [
                "periodo",
                "metodologia_id",
                "tipo_documento_id",
                "resultado_id",
                "cantidad",
                "con_complementacion",
                "con_validacion_ies",
                "con_dias",
                "dias_suma",
                "dias_habiles_suma",
                "dias_0_1",
                "dias_2_3",
                "dias_4_5",
                "dias_6_10",
                "dias_11_15",
                "dias_16_30",
                "dias_mas_30",
                *[f"habiles_{n}" for n in range(16)],
                "habiles_mas_15",
            ],
            "filas": legal,
        },
    )

    # --- resúmenes, revisiones y manifiesto --------------------------------------------------------------------------------
    ahora = datetime(ultimo.year, ultimo.month, 28, 12, 0, 0).isoformat()
    corte = f"{periodos[-1][:7]}-28"
    totales = {
        "vencimiento": sum(f[5] for f in vencimiento),
        "radicacion": sum(f[5] for f in radicacion),
        "canales": sum(f[2] or 0 for f in canales_filas),
        "tramites": sum(f[2] for f in []) or 0,
        "legalizaciones": sum(f[4] for f in legal),
    }
    bases = {}
    for base, total in totales.items():
        resumen = {
            "base": base,
            "actualizacion_id": 1,
            "publicado_en": ahora,
            "version_pipeline": "sintetico",
            "radicados": total,
            "periodo_minimo": periodos[0],
            "periodo_maximo": periodos[-1],
            "fecha_corte_maxima": corte,
            "madurez": [{"periodo": per, "estado": "definitiva", "motivo": "datos sinteticos"} for per in periodos],
        }
        bases[base] = resumen
        if base != "radicacion":
            guardar(f"{base}/resumen.json", resumen)
    guardar("revisiones.json", {"actualizacion_id": 1, "revisiones": []})
    manifiesto = {
        "generado_en": ahora,
        "actualizacion_id": 1,
        "publicado_en": ahora,
        "version_pipeline": "sintetico",
        "bases": bases,
        "archivos": archivos,
        "commit_git": None,
        "hash_reglas": hashlib.sha256(b"sintetico").hexdigest(),
        "huellas": huellas,
        "ingestiones": [],
        "exportacion_id": 0,
    }
    escribir(salida / "manifiesto.json", manifiesto)
    print(
        f"api sintetica en {salida}: {len(archivos) + 1} archivos, {len(periodos)} meses ({periodos[0][:7]} a {periodos[-1][:7]}), semilla {a.semilla}"
    )


if __name__ == "__main__":
    main()
