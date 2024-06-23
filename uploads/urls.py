# uploads/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileUploadViewSet

router = DefaultRouter()
router.register(r'file_uploads', FileUploadViewSet, basename='file_uploads')

urlpatterns = [
    path('', include(router.urls)),
]
