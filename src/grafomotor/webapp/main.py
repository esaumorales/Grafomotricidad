"""
API FastAPI para el docente.

  GET  /            -> interfaz mínima (subir fotos de las figuras de un niño)
  POST /evaluar     -> devuelve el informe en lenguaje natural + panel técnico
  GET  /salud       -> estado

Arranque:  python scripts/06_servir_web.py   (o  uvicorn grafomotor.webapp.main:app)
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from grafomotor.webapp.schemas import EvaluarOut
from grafomotor.webapp.service import Servicio

app = FastAPI(title="Evaluación grafomotora infantil", version="0.1.0")

_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")

_servicio: Servicio | None = None


def servicio() -> Servicio:
    global _servicio
    if _servicio is None:
        _servicio = Servicio()
    return _servicio


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/salud")
def salud() -> dict:
    try:
        s = servicio()
        return {"ok": True, "modelo": s.manifiesto.get("git_hash"),
                "baremo": s.manifiesto.get("version_baremo")}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@app.post("/evaluar", response_model=EvaluarOut)
async def evaluar(
    child_id: str = Form(...),
    edad_meses: int = Form(...),
    nombre_nino: str | None = Form(None),
    figura_ids: str = Form(..., description="ids separados por coma, en el mismo orden que los archivos"),
    fotos: list[UploadFile] = File(...),
) -> EvaluarOut:
    ids = [x.strip() for x in figura_ids.split(",") if x.strip()]
    with tempfile.TemporaryDirectory() as td:
        rutas: dict[str, str] = {}
        for fid, up in zip(ids, fotos):
            dest = Path(td) / f"{fid}_{up.filename}"
            dest.write_bytes(await up.read())
            rutas[fid] = str(dest)
        res = servicio().evaluar_sesion(child_id, edad_meses, rutas, nombre_nino)
    return EvaluarOut(**res)
