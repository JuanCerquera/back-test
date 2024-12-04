
from django.urls import path, include
from rest_framework import routers
from accounts.urls import router as accounts_router
from appointments.urls import router as appointments_router
from django.conf.urls.static import static
from django.conf import settings


router = routers.DefaultRouter()
router.registry.extend(accounts_router.registry)
router.registry.extend(appointments_router.registry)


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/', include('accounts.urls')),
    path('api/', include('appointments.urls')),
    path('api/auth/', include('rest_framework.urls', namespace='rest_framework')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
