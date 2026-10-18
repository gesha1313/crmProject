from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]

# Статику раздаём сами: раннер платформы стартует приложение без collectstatic-
# обвязки, а при DEBUG=False встроенная раздача отключается.
urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', static_serve,
            {'document_root': settings.STATIC_ROOT}),
]
