"""Accounts and single-use invitations for the teacher deployment."""
from contextlib import closing
from contextvars import ContextVar
import hashlib
import os
from pathlib import Path
import secrets
import re
from datetime import datetime, timedelta, timezone
import sqlite3
import time

from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

cuenta = ContextVar("cuenta_docente", default="docente")
COOKIE = "__Host-trazo"
DURACION = 12 * 60 * 60


def archivo():
    valor = os.environ.get("TRAZO_CUENTAS_DB")
    return Path(valor) if valor else None


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def conectar():
    return sqlite3.connect(archivo())


def autenticar(request):
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with closing(conectar()) as db:
        fila = db.execute(
            "SELECT usuario FROM sesiones_login WHERE huella=? AND vence>?",
            (digest(token), time.time()),
        ).fetchone()
    return fila[0] if fila else None


class Invitacion(BaseModel):
    token: str


def canjear(body: Invitacion, response: Response):
    if not archivo():
        raise HTTPException(404)
    if not 32 <= len(body.token) <= 128:
        raise HTTPException(401, "Enlace inválido o vencido.")
    token = secrets.token_urlsafe(32)
    with closing(conectar()) as db, db:
        fila = db.execute(
            "DELETE FROM invitaciones WHERE huella=? AND vence>? RETURNING usuario",
            (digest(body.token), time.time()),
        ).fetchone()
        if not fila:
            raise HTTPException(401, "Enlace inválido o vencido.")
        db.execute("DELETE FROM sesiones_login WHERE vence<=?", (time.time(),))
        db.execute("INSERT INTO sesiones_login VALUES(?,?,?)", (digest(token), fila[0], time.time() + DURACION))
    response.set_cookie(COOKIE, token, max_age=DURACION, secure=True, httponly=True, samesite="strict", path="/")
    return {"usuario": fila[0]}


class Demo(BaseModel):
    usuario: str


def acceso_demo(body: Demo, response: Response):
    lima = timezone(timedelta(hours=-5))
    cierre = datetime(2026, 11, 12, tzinfo=lima).timestamp()
    ahora = time.time()
    if not archivo() or ahora >= cierre:
        raise HTTPException(410, "La prueba de hoy ya terminó.")
    usuario = body.usuario.strip().lower()
    if not re.fullmatch(r"profesora(?:0[1-9]|[12][0-9]|30)", usuario):
        raise HTTPException(422, "Escribe un usuario de profesora01 a profesora30.")
    token = secrets.token_urlsafe(32)
    with closing(conectar()) as db, db:
        db.execute("INSERT INTO sesiones_login VALUES(?,?,?)", (digest(token), "demo-" + usuario, cierre))
    response.set_cookie(COOKIE, token, max_age=int(cierre - ahora), secure=True,
                        httponly=True, samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"usuario": usuario}


def acceso_admin(request: Request):
    clave = os.environ.get("TRAZO_ADMIN_PROXY", "")
    if not archivo() or not clave or not secrets.compare_digest(request.headers.get("X-Trazo-Admin", ""), clave):
        raise HTTPException(401)
    token = secrets.token_urlsafe(32)
    with closing(conectar()) as db, db:
        db.execute("INSERT INTO sesiones_login VALUES(?,?,?)", (digest(token), "docente", time.time() + DURACION))
    respuesta = RedirectResponse("/", status_code=303)
    respuesta.set_cookie(COOKIE, token, max_age=DURACION, secure=True, httponly=True, samesite="strict", path="/")
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def provisionar(usuarios):
    if not archivo():
        raise ValueError("Configura TRAZO_CUENTAS_DB.")
    archivo().parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(archivo(), os.O_CREAT | os.O_WRONLY, 0o600)
    os.close(fd)
    cuentas = ["docente", *(f"profesora{i:02}" for i in range(1, 31))]
    with closing(conectar()) as db, db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS cuentas(usuario TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS invitaciones(huella TEXT PRIMARY KEY, usuario TEXT UNIQUE, vence INTEGER);
        CREATE TABLE IF NOT EXISTS sesiones_login(huella TEXT PRIMARY KEY, usuario TEXT, vence INTEGER);
        """)
        db.executemany("INSERT OR IGNORE INTO cuentas VALUES(?)", [(u,) for u in cuentas])
        enlaces = {}
        for usuario in usuarios or cuentas:
            if usuario not in cuentas:
                raise ValueError("Cuenta desconocida.")
            token = secrets.token_urlsafe(32)
            db.execute("INSERT OR REPLACE INTO invitaciones VALUES(?,?,?)",
                       (digest(token), usuario, time.time() + 7 * 86400))
            enlaces[usuario] = token
    return enlaces


if __name__ == "__main__":
    import sys
    for usuario, token in provisionar(sys.argv[1:]).items():
        print(f"{usuario}\t/acceso#token={token}")

def ruta_privada(ruta: Path) -> Path:
    usuario = cuenta.get()
    if usuario == "docente":
        return ruta
    privada = ruta.parent / "cuentas" / usuario / ruta.name
    privada.parent.mkdir(parents=True, exist_ok=True)
    return privada
