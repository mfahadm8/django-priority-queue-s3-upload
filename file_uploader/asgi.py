import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import uploads.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'file_uploader.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            uploads.routing.websocket_urlpatterns
        )
    ),
})
