import asyncio
from fastapi import FastAPI
from grafomotor.webapp.frontend import FrontendSPA


def test_recargar_vistas_sirve_react_sin_ocultar_errores_api(tmp_path):
    (tmp_path / "index.html").write_text("<html>Aplicación React</html>", encoding="utf-8")
    (tmp_path / "foto.png").write_bytes(b"ejemplo")
    app = FastAPI()
    @app.get("/api/prueba")
    def api():
        return {"ok": True}
    app.mount("/", FrontendSPA(directory=tmp_path, html=True))

    async def request(path, method="GET"):
        messages = []
        async def send(message):
            messages.append(message)
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        await app({"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
                   "method": method, "path": path, "raw_path": path.encode(), "root_path": "",
                   "query_string": b"", "headers": [], "scheme": "http", "http_version": "1.1",
                   "server": ("test", 80), "client": ("test", 1234)}, receive, send)
        status = next(m["status"] for m in messages if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return status, body

    async def comprobar():
        for ruta in ["/", "/historial", "/resultados/1", "/informe/1", "/seguimiento/1", "/comparar/1/F01", "/ninos/NIN"]:
            status, body = await request(ruta)
            assert status == 200, (ruta, status, body)
            assert "Aplicación React" in body.decode()
        assert await request("/api/prueba") == (200, b'{"ok":true}')
        assert await request("/foto.png") == (200, b"ejemplo")
        for ruta in ["/api/no-existe", "/assets/no-existe.js", "/no-existe", "/resultados/1/extra"]:
            assert (await request(ruta))[0] == 404
        assert (await request("/historial", "HEAD"))[0] == 200
    asyncio.run(comprobar())

