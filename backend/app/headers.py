"""Cabeceras de seguridad en todas las respuestas (middleware ASGI puro: no agrega demora)."""

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),                 # el navegador no adivina tipos de archivo
    (b"x-frame-options", b"DENY"),                           # nadie puede incrustar la API en un iframe
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"cross-origin-resource-policy", b"same-site"),
]


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                present = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [
                    (k, v) for k, v in SECURITY_HEADERS if k not in present]
            await send(message)

        await self.app(scope, receive, send_with_headers)
