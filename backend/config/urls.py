from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve


def react_app(request):
    index_file = settings.FRONTEND_DIST_DIR / "index.html"

    if not index_file.exists():
        return HttpResponse(
            "The React production build was not found. "
            "Run 'npm run build' inside the frontend folder.",
            status=503,
            content_type="text/plain",
        )

    response = FileResponse(
        index_file.open("rb"),
        content_type="text/html",
    )
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def health_check(request):
    """Cheap unauthenticated endpoint for Render and external uptime probes."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/chat/", include("chat.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
else:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]


urlpatterns += [
    re_path(
        r"^(?!api/|admin/|media/|static/).*$",
        react_app,
        name="react-app",
    )
]
