from django.urls import path
from .views import get_upload_progress

urlpatterns = [
    path('progress/<str:filename>/', get_upload_progress, name='get_upload_progress'),
]
