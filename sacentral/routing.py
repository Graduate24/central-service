from channels.routing import ProtocolTypeRouter, URLRouter

from authentication.token_auth import TokenAuthMiddlewareStack
from ws.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'websocket': TokenAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
