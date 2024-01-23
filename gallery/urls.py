from django.conf import settings
from django.conf.urls.static import static

from . import views
from . import api

# This slash is important!
views.route.include('api/', api.route.collect())

urlpatterns = \
    views.route.collect() + \
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
