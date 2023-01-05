from django.conf import settings
from django.conf.urls.static import static

from . import views


urlpatterns = \
    views.route.collect() + \
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
