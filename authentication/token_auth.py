import urllib.parse as urlparse
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack

from utils.log import logger


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        """
        默认cookie，header中Authorization和url param的token。优先级递减
        :param scope:
        :return:
        """
        headers = dict(scope['headers'])

        if b'cookie' in headers:
            cookies = str(headers[b'cookie'])
            logger.info('----- cookie:{}'.format(cookies))
            if cookies.find('sessionid=') != -1:
                return self.inner(scope)
        authorization = None
        if b'Authorization' in headers:
            authorization = headers[b'Authorization'].decode()
            logger.info('----- 1.Authorization:{}'.format(authorization))
        if not authorization:
            parsed = urlparse.urlparse(scope['path'] + '?' + scope['query_string'].decode())
            token = parse_qs(parsed.query).get('token', None)
            if token:
                authorization = token[0]
                logger.info('----- token:{}'.format(token))
        if authorization:
            cookies = 'sessionid=' + authorization
            scope['headers'] = [(b'cookie', cookies.encode('ascii'))]
            logger.info('----- authorization:{}'.format(authorization))
        return self.inner(scope)


TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(AuthMiddlewareStack(inner))
