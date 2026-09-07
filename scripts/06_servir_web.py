"""Levanta la app web para el docente en http://localhost:8000"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("grafomotor.webapp.main:app", host="127.0.0.1", port=8000, reload=True)
