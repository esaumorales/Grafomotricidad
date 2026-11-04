"""
API FastAPI para el Dashboard Docente.

  GET   /api/salud                              -> estado del servicio
  POST  /api/evaluar                             -> evalúa una sesión (15 fotos de figuras -> informe), la guarda
  POST  /api/evaluar-hojas                       -> igual, pero con las 3 fotos de las hojas (recorta solo)
  GET   /api/sesiones                            -> historial (resumen)
  GET   /api/ninos/{child_id}/sesiones           -> evaluaciones de un niño en el tiempo
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

import json

from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from grafomotor.webapp.frontend import FrontendSPA

from grafomotor.config import REPO_ROOT, load_config
from grafomotor.webapp import db
from grafomotor.scoring.edad import edad_en_meses, edad_valida
from grafomotor.webapp.schemas import CorregirFiguraIn, EvaluarOut, SesionResumen
from grafomotor.webapp.service import ErrorHoja, Servicio

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
        try:
            _servicio = Servicio()
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=503,
                detail="La evaluación no está disponible: faltan archivos del paquete privado "
                       "(modelo, plantillas o baremos). Instala el paquete antes de evaluar.",
            ) from e
    return _servicio


def base_sesiones() -> Path:
    """El historial puede consultarse aunque el modelo no esté instalado."""
    ruta = load_config().ruta("db")
    db.iniciar_db(ruta)
    return ruta


def _edad(edad_meses: int | None, fecha_nacimiento: str | None, fecha_evaluacion: str | None):
    """(edad en meses, fecha de evaluación ISO o None). La edad sale de las dos fechas (AAAA-MM-DD);
    `edad_meses` directo solo se acepta si no vienen fechas."""
    if fecha_nacimiento and fecha_evaluacion:
        try:
            edad = edad_en_meses(date.fromisoformat(fecha_nacimiento), date.fromisoformat(fecha_evaluacion))
        except ValueError as e:
            raise HTTPException(422, f"Fechas no válidas: {e}") from None
    elif edad_meses is not None:
        edad, fecha_evaluacion = edad_meses, None
    else:
        raise HTTPException(422, "Indica la fecha de nacimiento y la fecha de la evaluación.")
    if not edad_valida(edad):
        raise HTTPException(422, f"La edad calculada ({edad // 12} años {edad % 12} meses) está fuera del "
                                 "rango de la prueba: de 3 años a 6 años y 6 meses.")
    return edad, fecha_evaluacion


@app.get("/api/salud")
def salud() -> dict:
    try:
        s = servicio()
        return {"ok": True, "modelo": s.manifiesto.get("git_hash"),
                "baremo": s.manifiesto.get("version_baremo")}
    except HTTPException as e:
        return {"ok": False, "error": e.detail}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/evaluar", response_model=EvaluarOut)
async def evaluar(
    child_id: str = Form(...),
    edad_meses: int | None = Form(None),
    fecha_nacimiento: str | None = Form(None, description="AAAA-MM-DD"),
    fecha_evaluacion: str | None = Form(None, description="AAAA-MM-DD"),
    nombre_nino: str | None = Form(None),
    figura_ids: str = Form(
        ..., description="ids separados por coma, en el mismo orden que los archivos"),
    fotos: list[UploadFile] = File(...),
) -> EvaluarOut:
    edad, f_eval = _edad(edad_meses, fecha_nacimiento, fecha_evaluacion)
    ids = [x.strip() for x in figura_ids.split(",") if x.strip()]
    if len(ids) != len(fotos):
        raise HTTPException(400, f"llegaron {len(fotos)} fotos pero {len(ids)} ids de figura")
    s = servicio()
    rutas: dict[str, str] = {}
    for fid, up in zip(ids, fotos, strict=True):
        sufijo = Path(up.filename or "").suffix or ".jpg"
        destino = s.guardar_foto(child_id, fid, await up.read(), sufijo)
        rutas[fid] = str(destino)
    res = s.evaluar_sesion(child_id, edad, rutas, nombre_nino, fecha_evaluacion=f_eval, fecha_nacimiento=fecha_nacimiento)
    return EvaluarOut(**res)


@app.post("/api/evaluar-hojas", response_model=EvaluarOut)
async def evaluar_hojas(
    child_id: str = Form(...),
    edad_meses: int | None = Form(None),
    fecha_nacimiento: str | None = Form(None, description="AAAA-MM-DD"),
    fecha_evaluacion: str | None = Form(None, description="AAAA-MM-DD"),
    nombre_nino: str | None = Form(None),
    hojas: list[UploadFile] = File(..., description="las 3 fotos de las hojas, en cualquier orden"),
) -> EvaluarOut:
    edad, f_eval = _edad(edad_meses, fecha_nacimiento, fecha_evaluacion)
    s = servicio()
    try:
        contenidos = [(up.filename or "foto", await up.read()) for up in hojas]
        rutas, avisos = s.recortar_hojas(child_id, contenidos)
    except ErrorHoja as e:
        raise HTTPException(422, str(e)) from None
    res = s.evaluar_sesion(child_id, edad, rutas, nombre_nino, avisos, f_eval, fecha_nacimiento=fecha_nacimiento)
    return EvaluarOut(**res)


@app.get("/api/sesiones", response_model=list[SesionResumen])
def listar_sesiones() -> list[SesionResumen]:
    return [SesionResumen(**r) for r in db.listar_sesiones(base_sesiones())]


@app.get("/api/ninos/{child_id}/sesiones", response_model=list[SesionResumen])
def listar_sesiones_de_nino(child_id: str) -> list[SesionResumen]:
    """Evaluaciones de un niño a lo largo del tiempo (seguimiento longitudinal)."""
    return [SesionResumen(**r) for r in db.listar_sesiones_de_nino(base_sesiones(), child_id)]


@app.get("/api/sesiones/{sesion_id}", response_model=EvaluarOut)
def obtener_sesion(sesion_id: int) -> EvaluarOut:
    res = db.obtener_sesion(base_sesiones(), sesion_id)
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


@app.get("/api/criterios/{figura_id}")
def criterios_manual(figura_id: str) -> dict:
    if figura_id not in load_config().figuras:
        raise HTTPException(404, "Figura desconocida")
    ruta = REPO_ROOT / "config" / "criterios_manual.json"
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    return {"figura_id": figura_id, "criterios": datos.get(figura_id, [])}


@app.get("/api/sesiones/{sesion_id}/figuras/{figura_id}/observaciones")
def observar_figura(sesion_id: int, figura_id: str) -> dict:
    from grafomotor.features.criterios import medir
    from grafomotor.preprocessing import preprocesar_figura
    from grafomotor.webapp.observaciones import observaciones

    sesion = db.obtener_sesion(base_sesiones(), sesion_id)
    if sesion is None or not any(f["figura_id"] == figura_id for f in sesion["figuras"]):
        raise HTTPException(404, "Sesión o figura no encontrada")
    s = servicio()
    ruta = s.ruta_foto(sesion["child_id"], figura_id)
    plantilla = s.plantillas.get(figura_id)
    if ruta is None or plantilla is None:
        raise HTTPException(404, "No está disponible la foto o la plantilla de esta figura")
    pre = preprocesar_figura(str(ruta), plantilla, s.cfg.get("preprocesamiento", default={}))
    fiable = pre.registro_ok and pre.calidad >= 0.35 and not pre.sin_trazo
    medidas = medir(pre.figura_bin) if fiable else {}
    referencia = medir(plantilla) if fiable else {}
    return {"figura_id": figura_id,
            "observaciones": observaciones(figura_id, medidas, referencia, pre.sin_trazo, imagen_fiable=fiable),
            "aviso_imagen": "No se pudo alinear el dibujo con la referencia. Las medidas automáticas se han omitido." if not pre.registro_ok else pre.aviso}


@app.get("/api/guia/hoja-modelo/{formato}")
def guia_hoja_modelo(formato: str) -> FileResponse:
    if formato not in {"png", "pdf"}:
        raise HTTPException(404, "Formato no disponible")
    ruta = REPO_ROOT / "config" / "guias_privadas" / f"hoja_modelo.{formato}"
    if not ruta.exists():
        raise HTTPException(404, "La hoja de ejemplo no está instalada")
    return FileResponse(ruta, media_type="image/png" if formato == "png" else "application/pdf")


if _FRONTEND_DIST.exists():
    app.mount("/", FrontendSPA(directory=_FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    def _sin_build() -> dict:
        return {
            "info": "El frontend aún no está compilado.",
            "como_compilarlo": "cd frontend && npm install && npm run build",
            "como_desarrollarlo": "cd frontend && npm install && npm run dev  (abre http://localhost:5173)",
        }
