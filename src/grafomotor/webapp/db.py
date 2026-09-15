"""
Persistencia de sesiones evaluadas (SQLite, ver sección 9 del contexto del proyecto).

Una fila por sesión (un niño, una aplicación de la prueba). El informe completo
(markdown + panel técnico + figuras) se guarda como JSON: es la salida ya calculada
por el pipeline, no hace falta un esquema relacional más fino para esta etapa.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sesiones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id        TEXT NOT NULL,
    nombre_nino     TEXT,
    edad_meses      INTEGER NOT NULL,
    fecha           TEXT NOT NULL,
    pd_total        INTEGER NOT NULL,
    nivel           TEXT NOT NULL,
    accion          TEXT NOT NULL,
    resultado_json  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sesiones_child ON sesiones(child_id);
"""


@contextmanager
def _conectar(db_path: str | Path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def iniciar_db(db_path: str | Path) -> None:
    with _conectar(db_path) as con:
        con.executescript(_SCHEMA)


def guardar_sesion(db_path: str | Path, resultado: dict) -> int:
    """Guarda el resultado completo de evaluar_sesion() y devuelve el id asignado."""
    tecnico = resultado["panel_tecnico"]["resumen"]
    with _conectar(db_path) as con:
        cur = con.execute(
            """INSERT INTO sesiones
               (child_id, nombre_nino, edad_meses, fecha, pd_total, nivel, accion, resultado_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                resultado["child_id"],
                resultado.get("nombre_nino"),
                resultado["edad_meses"],
                datetime.now(timezone.utc).isoformat(),
                tecnico.get("PD", 0),
                tecnico.get("nivel", ""),
                resultado["accion"],
                json.dumps(resultado, ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)


def listar_sesiones(db_path: str | Path) -> list[dict]:
    with _conectar(db_path) as con:
        filas = con.execute(
            """SELECT id, child_id, nombre_nino, edad_meses, fecha, pd_total, nivel, accion
               FROM sesiones ORDER BY fecha DESC"""
        ).fetchall()
        return [dict(f) for f in filas]


def obtener_sesion(db_path: str | Path, sesion_id: int) -> dict | None:
    with _conectar(db_path) as con:
        fila = con.execute(
            "SELECT id, fecha, resultado_json FROM sesiones WHERE id = ?", (sesion_id,)
        ).fetchone()
        if fila is None:
            return None
        resultado = json.loads(fila["resultado_json"])
        resultado["id"] = fila["id"]
        resultado["fecha"] = fila["fecha"]
        return resultado


def actualizar_resultado(db_path: str | Path, sesion_id: int, resultado: dict) -> None:
    """Sobrescribe el resultado completo de una sesión (tras una corrección manual),
    incluyendo las columnas resumen que usa listar_sesiones() para el historial."""
    tecnico = resultado["panel_tecnico"]["resumen"]
    with _conectar(db_path) as con:
        con.execute(
            """UPDATE sesiones
               SET pd_total = ?, nivel = ?, accion = ?, resultado_json = ?
               WHERE id = ?""",
            (
                tecnico.get("PD", 0),
                tecnico.get("nivel", ""),
                resultado["accion"],
                json.dumps(resultado, ensure_ascii=False),
                sesion_id,
            ),
        )
