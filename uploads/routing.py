from django.urls import re_path
from .consumers import UploadProgressConsumer

websocket_urlpatterns = [
    re_path(r'ws/progress/(?P<guid>[^/]+)/$', UploadProgressConsumer.as_asgi()),
]
