class SecurityResponseHeadersMiddleware:
    """Apply conservative browser and caching policies to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )

        if request.path.startswith("/api/auth/"):
            response["Cache-Control"] = "no-store, max-age=0"
            response["Pragma"] = "no-cache"

        return response
