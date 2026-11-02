import sys
import traceback
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # project root, so `backend` imports

try:
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

except Exception:  # startup diagnostics: show the error instead of a blank 500
    _err = traceback.format_exc()[-1800:]
    print(_err, file=sys.stderr)

    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        body = ('{"ok": false, "startup_error": %s}' % __import__("json").dumps(_err)).encode()
        await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})
