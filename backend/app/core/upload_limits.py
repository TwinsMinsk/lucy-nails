import tempfile

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse


MAX_MULTIPART_BYTES = 12 * 1024 * 1024


class UploadSizeLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path", "").rstrip("/") != "/api/admin/upload"
        ):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length", b"")
        if length.isdigit() and (len(length) > 9 or int(length) > MAX_MULTIPART_BYTES):
            return await JSONResponse(
                status_code=413, content={"detail": "Upload body is too large"}
            )(scope, receive, send)
        with tempfile.SpooledTemporaryFile(max_size=2 * 1024 * 1024) as body:
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > MAX_MULTIPART_BYTES:
                    return await JSONResponse(
                        status_code=413, content={"detail": "Upload body is too large"}
                    )(scope, receive, send)
                await run_in_threadpool(body.write, chunk)
                if not message.get("more_body", False):
                    break
            await run_in_threadpool(body.seek, 0)
            delivered_final = False

            async def bounded_receive():
                nonlocal delivered_final
                if delivered_final:
                    return await receive()
                chunk = await run_in_threadpool(body.read, 64 * 1024)
                delivered_final = body.tell() >= total
                return {"type": "http.request", "body": chunk, "more_body": not delivered_final}

            await self.app(scope, bounded_receive, send)
