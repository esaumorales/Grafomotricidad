"""
API FastAPI para el Dashboard Docente.

  GET   /api/salud                              -> estado del servicio
  POST  /api/evaluar                             -> evalúa una sesión (fotos -> informe), la guarda
  GET   /api/sesiones                            -> historial (resumen)
  GET   /api/sesiones/{id}                       -> informe completo de una sesión guardada
  PATCH /api/sesiones/{id}/figuras/{figura_id}   -> corrección manual del docente
  GET   /api/imagenes/{child_id}/{figura_id}     -> foto subida por el docente (para comparar)
  GET   /api/plantillas/{figura_id}              -> plantilla de referencia (para comparar)

El resto de rutas sirve el build de React (frontend/dist). En desarrollo, el
frontend corre aparte con `npm run dev` y llama a esta API en localhost:8000
(CORS abierto sólo para ese origen).

Arranque:  python scripts/06_servir_web.py   (o  uvicorn grafomotor.webapp.main:app)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from grafomotor.webapp.schemas import CorregirFiguraIn, EvaluarOut, SesionResumen
from grafomotor.webapp.service import Servicio

app = FastAPI(title="Evaluación grafomotora infantil", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND_DIST = Path(__file__).parents[3] / "frontend" / "dist"

_servicio: Servicio | None = None


def servicio() -> Servicio:
    global _servicio
    if _servicio is None:
        _servicio = Servicio()
    return _servicio


@app.get("/api/salud")
def salud() -> dict:
    try:
        s = servicio()
        return {"ok": True, "modelo": s.manifiesto.get("git_hash"),
                "baremo": s.manifiesto.get("version_baremo")}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@app.post("/api/evaluar", response_model=EvaluarOut)
async def evaluar(
    child_id: str = Form(...),
    edad_meses: int = Form(...),
    nombre_nino: str | None = Form(None),
    figura_ids: str = Form(..., description="ids separados por coma, en el mismo orden que los archivos"),
    fotos: list[UploadFile] = File(...),
) -> EvaluarOut:
    ids = [x.strip() for x in figura_ids.split(",") if x.strip()]
    s = servicio()
    rutas: dict[str, str] = {}
    for fid, up in zip(ids, fotos):
        sufijo = Path(up.filename or "").suffix or ".jpg"
        destino = s.guardar_foto(child_id, fid, await up.read(), sufijo)
        rutas[fid] = str(destino)
    res = s.evaluar_sesion(child_id, edad_meses, rutas, nombre_nino)
    return EvaluarOut(**res)


@app.get("/api/sesiones", response_model=list[SesionResumen])
def listar_sesiones() -> list[SesionResumen]:
    return [SesionResumen(**r) for r in servicio().listar_sesiones()]


@app.get("/api/sesiones/{sesion_id}", response_model=EvaluarOut)
def obtener_sesion(sesion_id: int) -> EvaluarOut:
    res = servicio().obtener_sesion(sesion_id)
    if res is None:
        raise HTTPException(404, "sesión no encontrada")
    return EvaluarOut(**res)


@app.patch("/api/sesiones/{sesion_id}/figuras/{figura_id}", response_model=EvaluarOut)
def corregir_figura(sesion_id: int, figura_id: str, body: CorregirFiguraIn) -> EvaluarOut:
    res = servicio().corregir_figura(sesion_id, figura_id, body.puntaje_docente)
    if res is None:
        raise HTTPException(404, "sesión o figura no encontrada")
    return EvaluarOut(**res)


@app.get("/api/imagenes/{child_id}/{figura_id}")
def imagen_nino(child_id: str, figura_id: str) -> FileResponse:
    ruta = servicio().ruta_foto(child_id, figura_id)
    if ruta is None:
        raise HTTPException(404, "foto no encontrada")
    return FileResponse(ruta)


@app.get("/api/plantillas/{figura_id}")
def imagen_plantilla(figura_id: str) -> FileResponse:
    ruta = servicio().ruta_plantilla(figura_id)
    if ruta is None:
        raise HTTPException(404, "plantilla no encontrada")
    return FileResponse(ruta)


if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    def _sin_build() -> dict:
        return {
            "info": "El frontend aún no está compilado.",
            "como_compilarlo": "cd frontend && npm install && npm run build",
            "como_desarrollarlo": "cd frontend && npm install && npm run dev  (abre http://localhost:5173)",
        }
