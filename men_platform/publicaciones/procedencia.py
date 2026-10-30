"""La procedencia de lo que un PDF publica (Fase 3, D-81): de qué exportación salió, con qué commit y qué reglas, qué
huella tiene el cubo que leyó, si la cifra del mes es provisional o definitiva y qué revisiones la tocan.

Todo sale de los archivos de api/v1 que escribe `men-api exportar`: manifiesto.json (procedencia), <base>/resumen.json
(madurez) y revisiones.json. Cuando un informe se genera desde una carpeta sin esos archivos, los campos quedan vacíos y
la ficha técnica lo dice."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RevisionPublicada:
    fecha: str
    informe: str
    periodo_desde: str | None
    periodo_hasta: str | None
    motivo: str
    referencia: str | None
    magnitud: str | None


@dataclass
class Procedencia:
    actualizacion_id: int | None = None
    exportacion_id: int | None = None
    generado_en: str | None = None  # ISO, hora de Colombia
    commit_git: str | None = None
    hash_reglas: str | None = None
    huellas: dict[str, str] = field(default_factory=dict)
    ingestiones: int = 0
    madurez: dict[str, dict[str, tuple[str, str]]] = field(default_factory=dict)  # base → periodo → (estado, motivo)
    parametros: dict[str, str] = field(
        default_factory=dict
    )  # ref.parametro, tal como lo publica dimensiones.json (D-82)
    revisiones: list[RevisionPublicada] = field(default_factory=list)

    @property
    def disponible(self) -> bool:
        return self.exportacion_id is not None or self.commit_git is not None

    def huella(self, ruta: str) -> str | None:
        return self.huellas.get(ruta)

    def estado_cifra(self, base: str, periodo: str) -> tuple[str, str] | None:
        """(estado, motivo) de un mes de una base, o None si la exportación no trae madurez."""
        return self.madurez.get(base, {}).get(periodo[:10])

    def revisiones_de(self, informe: str, periodo: str) -> list[RevisionPublicada]:
        """Las revisiones del informe (o de todos) que tocan el mes dado."""
        mes = periodo[:10]
        salida = []
        for r in self.revisiones:
            if r.informe not in (informe, "todos"):
                continue
            desde = (r.periodo_desde or "0000-01-01")[:10]
            hasta = (r.periodo_hasta or "9999-12-31")[:10]
            if desde <= mes <= hasta:
                salida.append(r)
        return salida


def _leer(ruta: Path) -> dict | None:
    if not ruta.is_file():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def cargar(
    ruta_api: Path,
    bases: tuple[str, ...] = (
        "vencimiento",
        "radicacion",
        "canales",
        "tramites",
        "legalizaciones",
        "resoluciones",
        "comunicaciones",
    ),
) -> Procedencia:
    """Lee manifiesto.json, los resumen.json de las bases y revisiones.json; tolera que falten."""
    p = Procedencia()
    manifiesto = _leer(ruta_api / "manifiesto.json")
    if manifiesto:
        p.actualizacion_id = manifiesto.get("actualizacion_id")
        p.exportacion_id = manifiesto.get("exportacion_id")
        p.generado_en = manifiesto.get("generado_en")
        p.commit_git = manifiesto.get("commit_git")
        p.hash_reglas = manifiesto.get("hash_reglas") or None
        p.huellas = dict(manifiesto.get("huellas") or {})
        p.ingestiones = len(manifiesto.get("ingestiones") or [])
    dimensiones = _leer(ruta_api / "dimensiones.json")
    if dimensiones and isinstance(dimensiones.get("parametros"), dict):
        p.parametros = {str(k): str(v) for k, v in dimensiones["parametros"].items()}
    for base in bases:
        resumen = _leer(ruta_api / base / "resumen.json")
        if resumen and resumen.get("madurez"):
            p.madurez[base] = {m["periodo"][:10]: (m["estado"], m["motivo"]) for m in resumen["madurez"]}
    revisiones = _leer(ruta_api / "revisiones.json")
    if revisiones:
        p.revisiones = [
            RevisionPublicada(
                fecha=str(r.get("fecha", ""))[:10],
                informe=str(r.get("informe", "")),
                periodo_desde=r.get("periodo_desde"),
                periodo_hasta=r.get("periodo_hasta"),
                motivo=str(r.get("motivo", "")),
                referencia=r.get("referencia"),
                magnitud=r.get("magnitud"),
            )
            for r in revisiones.get("revisiones", [])
        ]
    return p


def corto(huella: str | None, largo: int = 12) -> str:
    return huella[:largo] if huella else "–"


def fecha_generacion(p: Procedencia) -> str:
    """La fecha que lleva la ficha como «Generado»: la de la exportación, para que dos generaciones desde la misma
    exportación den el mismo PDF; si la carpeta no trae manifiesto, la hora actual."""
    if p.generado_en:
        try:
            momento = datetime.fromisoformat(p.generado_en)
            return f"exportación del {momento:%d/%m/%Y %H:%M}"
        except ValueError:
            pass
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def nota_cifra(p: Procedencia, base: str, periodo: str) -> str | None:
    """«Cifra provisional» para la portada cuando el mes todavía puede cambiar; None si es definitiva o no se sabe."""
    estado = p.estado_cifra(base, periodo)
    return "Cifra provisional" if estado is not None and estado[0] == "provisional" else None


def filas_ficha(p: Procedencia, base: str, informe: str, periodo: str, ruta_cubo: str) -> list[list[str]]:
    """Las filas de procedencia para la ficha técnica de un PDF."""
    if not p.disponible:
        return [
            [
                "Procedencia",
                "La carpeta de agregados no trae manifiesto con procedencia (exportación anterior a la Fase 3)",
            ]
        ]
    filas = [
        ["Publicación del mart", f"{p.actualizacion_id}" if p.actualizacion_id is not None else "–"],
        ["Exportación archivada", f"{p.exportacion_id}" if p.exportacion_id is not None else "sin archivar"],
        ["Commit del código", corto(p.commit_git)],
        ["Huella de las reglas", corto(p.hash_reglas)],
        ["Huella del cubo", corto(p.huella(ruta_cubo))],
        ["Cargas vigentes", f"{p.ingestiones} archivos registrados en la auditoría"],
    ]
    estado = p.estado_cifra(base, periodo)
    if estado is not None:
        filas.append(["Estado de la cifra", f"{estado[0].capitalize()}: {estado[1]}"])
    revisiones = p.revisiones_de(informe, periodo)
    if revisiones:
        texto = "; ".join(
            f"{r.fecha}: {r.motivo}"
            + (f" ({r.referencia})" if r.referencia else "")
            + (f". {r.magnitud}" if r.magnitud else "")
            for r in revisiones
        )
        filas.append(["Revisiones que tocan el mes", texto])
    else:
        filas.append(["Revisiones que tocan el mes", "Ninguna registrada"])
    return filas
