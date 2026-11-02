from urllib.parse import parse_qs

from backend.server import app  # ASGI app served by Vercel's Python runtime


class RestorePath:
    """vercel.json rewrites /api/<x> to this function as ?p=<x>; put the original path back."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            p = parse_qs(scope.get("query_string", b"").decode()).get("p")
            if p:
                path = "/api/" + p[0].strip("/")
                scope = {**scope, "path": path, "raw_path": path.encode()}
        await self.inner(scope, receive, send)


app.add_middleware(RestorePath)
