from django.urls import path
from .consumers import UploadProgressConsumer

websocket_urlpatterns = [
    path('ws/progress/', UploadProgressConsumer.as_asgi()),
]
