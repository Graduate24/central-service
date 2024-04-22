import json
import logging
import traceback
from importlib import import_module

from django.conf import settings
from django.http.response import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from authentication.models import Role, Resource
from sacentral.settings import PERMISSIONS_CHECK, LOGIN_EXEMPT
from utils.response_code import error, ERROR, NOT_FOUND_404_MSG

logger = logging.getLogger('django')


def match_ant(pattern, path, virtual_schema=True):
    from urlmatch import urlmatch
    try:
        if not pattern.endswith('/'):
            pattern = pattern + '/'
        if not path.endswith('/'):
            path = path + '/'
        if virtual_schema:
            host = 'http://sacentral.com'
            pattern = host + pattern
            path = host + path

        match = urlmatch(pattern, path, fuzzy_scheme=False)
        return match
    except Exception as e:
        msg = str(e)
        logger.info('MATCH ERROR=====:{}'.format(msg))
        return True


class LoginRequiredMiddleware(object):
    """
    Middleware that requires a user to be authenticated to view any page other
    than LOGIN_URL. Exemptions to this requirement can optionally be specified
    in settings via a list of regular expressions in LOGIN_EXEMPT_URLS (which
    you can copy from your urls.py).

    Requires authentication middleware and template context processors to be
    loaded. You'll get an error if they aren't.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        assert hasattr(request, 'user'), "The Login Required middleware\
             requires authentication middleware to be installed. Edit your\
             MIDDLEWARE_CLASSES setting to insert\
             'django.contrib.authentication.middlware.AuthenticationMiddleware'. If that doesn't\
             work, ensure your TEMPLATE_CONTEXT_PROCESSORS setting includes\
             'django.core.context_processors.authentication'."
        path = request.path_info
        logger.info('path:{}'.format(path))
        if LOGIN_EXEMPT:
            logger.info('LOGIN EXEMPT')
            return self.get_response(request)

        if not path.startswith('/api/') or any(match_ant(m, path) for m in settings.LOGIN_EXEMPT_URLS):
            logger.info('LOGIN EXEMPT URLS')
            return self.get_response(request)

        if request.method == 'OPTIONS':
            return self.get_response(request)

        if not request.user.is_authenticated:
            logger.info('login required')
            return JsonResponse(ERROR.LOGIN_REQUIRED)

        if PERMISSIONS_CHECK:
            # OPTION放行
            if request.method == 'OPTIONS':
                return self.get_response(request)
            # 获取角色权限
            roles = Role.get_roles(request.user.pk)
            resources = Resource.get_resources(roles)
            logger.info(resources)
            # TODO

        return self.get_response(request)


class JsonLoaderMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.REQUEST = {}
        try:
            if request.body:
                request.REQUEST = json.loads(request.body.decode("utf-8"))
        except Exception:
            traceback.print_exc()
        logger.info('--------------------')
        logger.info('method:{}; path:{}.'.format(request.method, request.path))
        logger.info('get params:{}'.format(request.GET))
        if request.content_type and request.content_type == 'application/json':
            logger.info('body:{}'.format(request.REQUEST))
        response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, PUT, POST, OPTIONS, DELETE"
        response["Access-Control-Max-Age"] = "1000"
        response["Access-Control-Allow-Headers"] = "*"
        return response

    def process_exception(self, request, exception):
        msg = str(exception)
        es = str(type(exception))
        logging.exception(type(exception))
        logger.info('ERROR=====:{}'.format(msg))
        if es.__contains__('DoesNotExist') and not es.__contains__('FieldDoesNotExist'):
            return JsonResponse(NOT_FOUND_404_MSG(msg))

        return JsonResponse(error(msg=msg))


class CookieRotateMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
        engine = import_module(settings.SESSION_ENGINE)
        self.SessionStore = engine.SessionStore

    def process_request(self, request):
        session_key = request.headers.get('Authorization', None)
        session_key = session_key if session_key else request.GET.get('token', None)
        if not request.session.session_key and session_key:
            request.session = self.SessionStore(session_key)
