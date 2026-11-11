"""Archivos estáticos y acceso directo a las rutas de React."""
import re
from starlette.staticfiles import StaticFiles


class FrontendSPA(StaticFiles):
    async def get_response(self, path, scope):
        ruta = path.replace(chr(92), "/").strip("/")
        es_vista = bool(re.fullmatch(
            r"acceso|historial|(?:resultados|informe|seguimiento)/[^/]+|comparar/[^/]+/[^/]+|ninos/[^/]+", ruta
        ))
        if scope["method"] in {"GET", "HEAD"} and es_vista:
            return await super().get_response("index.html", scope)
        return await super().get_response(path, scope)
