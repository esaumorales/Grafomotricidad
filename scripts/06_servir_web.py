"""Levanta la app web para el docente en http://localhost:8000

Escucha en 0.0.0.0 para poder entrar también desde otro dispositivo
de la misma red local usando la IP de esta máquina (ver `ipconfig`).
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("grafomotor.webapp.main:app", host="0.0.0.0", port=8000, reload=True)
