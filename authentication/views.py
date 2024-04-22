import random
import string

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.models import Session
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils.translation import LANGUAGE_SESSION_KEY

from utils.response_code import valid_fail, page, visible, page_get
from utils.views import *
from .docs import *
from .models import *


def fill_role(user):
    roles = user.get('roles', None)
    if roles:
        user['roles_meta'] = model_list_to_mongo(Role.objects.filter(pk__in=roles))


def user_to_mongo(user, wrapper=None):
    if not isinstance(user, get_user_model()):
        if wrapper:
            wrapper(user)
        return user

    user = json.loads(serialize('json', [user]))[0]

    user.update(user['fields'])
    del user['fields']
    del user['password']
    if wrapper:
        wrapper(user)
    return user


def model_to_mongo(model):
    if not isinstance(model, models.Model):
        return model

    model = json.loads(serialize('json', [model]))[0]
    model.update(model['fields'])
    del model['fields']
    del model['model']
    return model


def model_list_to_mongo(models):
    return [model_to_mongo(m) for m in models]


class UsersView(View):

    def get(self, request, **kwargs):
        """
       @api {GET} api/auth/users 用户列表
       @apiVersion 1.0.0
       @apiName User List
       @apiGroup Auth
       @apiDescription 用户列表

       @apiParam {Number}  [page=1] 当前页码 url参数 ?page=
       @apiParam {Number}  [limit=25] 每页记录数 url参数 ?limit=

       @apiParam {String}  [username] 用户名.

       @apiSuccessExample Response-Success:
           HTTP 1.1/ 200K
           {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 25,
                "totalItems": 2,
                "totalPages": 1,
                "data": [
                    {
                        "model": "Auth.user",
                        "pk": 2,
                        "last_login": null,
                        "is_superuser": false,
                        "username": "teADFA",
                        "first_name": "",
                        "last_name": "",
                        "email": "",
                        "is_staff": false,
                        "is_active": true,
                        "date_joined": "2020-05-12T20:00:00.979Z",
                        "phone_number": "",
                        "preferred_language": "zh-hans",
                        "groups": [],
                        "user_permissions": [],
                        "roles": []
                    },
                    {
                        "model": "Auth.user",
                        "pk": 17,
                        "last_login": "2020-05-18T07:43:56.322Z",
                        "is_superuser": false,
                        "username": "test",
                        "first_name": "",
                        "last_name": "",
                        "email": "",
                        "is_staff": false,
                        "is_active": true,
                        "date_joined": "2020-05-12T20:15:00.375Z",
                        "phone_number": "",
                        "preferred_language": "zh-hans",
                        "groups": [],
                        "user_permissions": [],
                        "roles": []
                    }
                ]
            }
        }
       """
        query_dict = request.GET.dict()
        name = query_dict.get('username', None)
        query = {}
        index, per_page = page_get(request.GET)
        if name:
            query['username__startswith'] = name
        query['is_deleted'] = 0
        return page(get_user_model().objects.filter(**query), index, per_page, lambda x: user_to_mongo(x))

    def post(self, request):
        """
          @api {POST} api/auth/users 创建用户
          @apiVersion 1.0.0
          @apiName User Create
          @apiGroup Auth
          @apiDescription 创建用户

          @apiParam {String}  username 用户名.
          @apiParam {String}  password 密码.
          @apiParam {Boolean}  [is_superuser=false] 是否超级用户
          @apiParam {String}  [first_name] 名.
          @apiParam {String}  [last_name] 姓.
          @apiParam {String}  [email] email.
          @apiParam {List}  [roles] 角色id list，例如[1,2].
          @apiParam {Boolean}  [is_staff=false] 是否管理员
          @apiParam {Boolean}  [is_active=true] 是否激活
          @apiParam {String}  [preferred_language=zh-hans] email.
          @apiParam {String}  [date_joined] yyyy-MM-dd HH:mm:ss加入时间.

          @apiSuccessExample Response-Success:
              HTTP 1.1/ 200K
              {
               "code": 200,
               "msg": "ok",
               "data": {
                           "model": "Auth.user",
                           "pk": 2,
                           "last_login": null,
                           "is_superuser": false,
                           "username": "teADFA",
                           "first_name": "",
                           "last_name": "",
                           "email": "",
                           "is_staff": false,
                           "is_active": true,
                           "date_joined": "2020-05-12T20:00:00.979Z",
                           "phone_number": "",
                           "preferred_language": "zh-hans",
                           "groups": [],
                           "user_permissions": [],
                           "roles": []
                       }
           }
          """
        user = UserForm(request.REQUEST)
        if not user.is_valid():
            failed_dict = user.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        user = user.clean()
        try:
            u = get_user_model().objects.create_user(user['username'], password=user['password'])
            if 'roles' in user.keys():
                u.roles.set(user.get('roles', []))
                del user['roles']
        except IntegrityError:
            return JsonResponse(ERROR.USER_EXISTS)
        del user['password']
        User.objects.filter(id=u.pk).update(**user)
        return MongoJsonResponse(ok(user_to_mongo(u)))


class UsersMetaView(APIMetaView):
    def get_fields(self):
        fields = get_user_model()._meta.get_fields()

        for field in fields:
            if field.name == 'preferred_language':
                field.choices = settings.LANGUAGES

        return fields


class UsersDetailView(View):
    def get(self, request, uid):
        """
        @api {GET} api/auth/users/:id 用户详情
        @apiVersion 1.0.0
        @apiName User Detail
        @apiGroup Auth
        @apiDescription 用户详情

        @apiParam {Number} id 用户 ID.

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "model": "Auth.user",
                    "pk": 2,
                    "last_login": null,
                    "is_superuser": false,
                    "username": "teADFA",
                    "first_name": "",
                    "last_name": "",
                    "email": "",
                    "is_staff": false,
                    "is_active": true,
                    "date_joined": "2020-05-12T20:00:00.979Z",
                    "phone_number": "",
                    "preferred_language": "zh-hans",
                    "groups": [],
                    "user_permissions": [],
                    "roles": []
                }
            }

        """
        user = get_user_model().objects.get(id=uid)
        if user.is_deleted != 0:
            return JsonResponse(ERROR.NOT_FOUND_404)
        return JsonResponse(ok(user_to_mongo(user)))

    def put(self, request, uid):
        """
        @api {PUT} api/auth/users/:id 修改用户
        @apiVersion 1.0.0
        @apiName User Update
        @apiGroup Auth
        @apiDescription 修改用户

        @apiParam {Number}  id 用户ID.
        @apiParam {String}  [username] 用户名.
        @apiParam {String}  [password] 密码.
        @apiParam {Boolean}  [is_superuser=false] 是否超级用户
        @apiParam {String}  [first_name] 名.
        @apiParam {String}  [last_name] 姓.
        @apiParam {String}  [email] email.
        @apiParam {List}  [roles] 角色id list，例如[1,2].
        @apiParam {Boolean}  [is_staff=false] 是否管理员
        @apiParam {Boolean}  [is_active=true] 是否激活
        @apiParam {String}  [preferred_language=zh-hans] email.
        @apiParam {String}  [date_joined] yyyy-MM-dd HH:mm:ss加入时间.

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
               "code": 200,
               "msg": "ok",
               "data": {
                           "model": "Auth.user",
                           "pk": 2,
                           "last_login": null,
                           "is_superuser": false,
                           "username": "teADFA",
                           "first_name": "",
                           "last_name": "",
                           "email": "",
                           "is_staff": false,
                           "is_active": true,
                           "date_joined": "2020-05-12T20:00:00.979Z",
                           "phone_number": "",
                           "preferred_language": "zh-hans",
                           "groups": [],
                           "user_permissions": [],
                           "roles": []
                       }
           }
          """

        if not get_user_model().objects.filter(pk=uid, is_deleted=0).exists():
            return JsonResponse(ERROR.NOT_FOUND_404)
        u = get_user_model().objects.get(id=uid)
        user = UserUpdateForm(request.REQUEST)
        if not user.is_valid():
            failed_dict = user.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        user = visible(user.clean(), request.REQUEST)
        if user.get('password', None):
            user['password'] = make_password(user.get('password'))

        if 'roles' in user.keys():
            u.roles.set(user.get('roles', []))
            del user['roles']
        get_user_model().objects.filter(pk=uid).update(**user)
        return MongoJsonResponse(ok(user_to_mongo(get_user_model().objects.get(id=uid))))

    def patch(self, request, id):
        user = get_object_or_404(get_user_model(), pk=id)

        fields = json.loads(request.body.decode('UTF-8'))

        if fields.get('date_joined', None):
            fields['date_joined'] = datetime.datetime.fromtimestamp(fields['date_joined']['$date'] / 1000)
        if fields.get('last_login', None):
            fields['last_login'] = datetime.datetime.fromtimestamp(fields['last_login']['$date'] / 1000)

        for field, value in fields.items():
            try:
                if field == 'password':
                    user.set_password(value)
                elif field == 'groups':
                    user.groups.set(value)
                else:
                    setattr(user, field, value)
            except Exception:
                pass

        user.save()

        request.session[LANGUAGE_SESSION_KEY] = user.preferred_language

        return MongoJsonResponse({'data': user_to_mongo(user)})

    def delete(self, request, uid):
        """
        @api {DELETE} api/auth/users/:id 删除用户
        @apiVersion 1.0.0
        @apiName User Delete
        @apiGroup Auth
        @apiDescription 删除用户

        @apiParam {Number} id 用户 ID.
        """
        user = get_user_model().objects.get(id=uid)
        if user.is_deleted != 0:
            return JsonResponse(ERROR.NOT_FOUND_404)
        user.is_deleted = 1
        user.username = user.username + '(deleted_' + ''.join(
            random.sample(string.ascii_lowercase + string.digits, 3)) + ')'
        user.save()
        return JsonResponse(ok())


class CookieUserDetail(View):
    def get(self, request):
        """
        @api {GET} api/auth/users/current cookie用户详情
        @apiVersion 1.0.0
        @apiName User Cookie Detail
        @apiGroup Auth
        @apiDescription cookie用户详情

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "model": "Auth.user",
                    "pk": 2,
                    "last_login": null,
                    "is_superuser": false,
                    "username": "teADFA",
                    "first_name": "",
                    "last_name": "",
                    "email": "",
                    "is_staff": false,
                    "is_active": true,
                    "date_joined": "2020-05-12T20:00:00.979Z",
                    "phone_number": "",
                    "preferred_language": "zh-hans",
                    "groups": [],
                    "user_permissions": [],
                    "roles": []
                }
            }
        """
        if not request.user.is_authenticated:
            logger.info('login required')
            return JsonResponse(ERROR.LOGIN_REQUIRED)
        user = get_user_model().objects.get(id=request.user.pk)
        if user.is_deleted != 0:
            return JsonResponse(ERROR.NOT_FOUND_404)
        return JsonResponse(ok(user_to_mongo(user)))


class SignUpView(View):

    def post(self, request):
        """
        @api {POST} api/auth/signup 用户注册
        @apiVersion 1.0.0
        @apiName signup
        @apiGroup Auth
        @apiDescription 用户注册
        @apiHeaderExample {json} Header-Example:
        {
         "Content-Type": "application/json"
       }

        @apiParam {String} username username
        @apiParam {String} password password

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
           {
            "code": 200,
            "msg": "ok",
            "data": {
                "model": "Auth.user",
                "pk": 17,
                "last_login": null,
                "is_superuser": false,
                "username": "test",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_staff": false,
                "is_active": true,
                "date_joined": "2020-05-12T20:15:00.375Z",
                "phone_number": "",
                "preferred_language": "zh-hans",
                "groups": [],
                "user_permissions": [],
                "roles": []
            }
        }
        """
        signup = SignupForm(request.REQUEST)
        if not signup.is_valid():
            # 错误的信息
            failed_dict = signup.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        # 正确的信息
        signup = signup.clean()
        try:
            user = get_user_model().objects.create_user(signup['username'], password=signup['password'])
        except IntegrityError:
            return JsonResponse(ERROR.USER_EXISTS)

        return JsonResponse(ok(user_to_mongo(user)))


class LogInView(View):

    def post(self, request):
        """
        @api {POST} api/auth/login 用户登录
        @apiVersion 1.0.0
        @apiName login
        @apiGroup Auth
        @apiDescription 用户登录
        @apiHeaderExample {json} Header-Example:
        {
         "Content-Type": "application/json"
       }

        @apiParam {String} username username
        @apiParam {String} password password

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
           {
            "code": 200,
            "msg": "ok",
            "data": {
                "model": "Auth.user",
                "pk": 17,
                "last_login": null,
                "is_superuser": false,
                "username": "test",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_staff": false,
                "is_active": true,
                "date_joined": "2020-05-12T20:15:00.375Z",
                "phone_number": "",
                "preferred_language": "zh-hans",
                "groups": [],
                "user_permissions": [],
                "roles": []
            }
        }
        """
        login = LoginForm(request.REQUEST)
        if not login.is_valid():
            # 错误的信息
            failed_dict = login.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        # 正确的信息
        login = login.clean()
        user = auth.authenticate(username=login.get('username'),
                                 password=login.get('password'))
        if user is None:
            return JsonResponse(ERROR.LOGIN_ERROR)
        auth.login(request, user)
        request.session[LANGUAGE_SESSION_KEY] = user.preferred_language
        session_key = request.session.session_key
        login_response = user_to_mongo(user)
        login_response['session_id'] = session_key
        return JsonResponse(ok(login_response))


class LogOutView(View):

    def post(self, request):
        """
        @api {POST} api/auth/logout 退出登录
        @apiVersion 1.0.0
        @apiName logout
        @apiGroup Auth
        @apiDescription 退出登录
        @apiHeaderExample {json} Header-Example:
        {
         "Content-Type": "application/json"
       }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
           {
            "code": 200,
            "msg": "ok"
        }
        """
        auth.logout(request)
        if request.session.session_key:
            Session.objects.filter(session_key=request.session.session_key).delete()
        return JsonResponse(ok())


class PasswordView(View):
    def post(self, request):
        user = auth.authenticate(username=request.user.username,
                                 password=request.REQUEST.get('old_password'))
        if user is None:
            return HttpResponse(status=401)

        user.set_password(request.REQUEST.get('password'))
        user.save()
        return JsonResponse(user_to_mongo(user))


class ResourcesView(View):

    def get(self, request, **kwargs):
        """
        @api {GET} api/auth/resources 资源列表
        @apiVersion 1.0.0
        @apiName Resources List
        @apiGroup Auth
        @apiDescription 资源列表

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                'code': 200,
                'msg': 'ok'
                'data':{
                }
            }

        """
        resources = Resource.objects.all()
        return MongoJsonResponse(ok(model_list_to_mongo(resources)))

    def post(self, request):
        """
        @api {POST} api/auth/resources 创建资源
        @apiVersion 1.0.0
        @apiName Create Resources
        @apiGroup Auth
        @apiDescription 创建资源

        @apiParam {String} name 名称
        @apiParam {String} code code,唯一
        @apiParam {Number} [parent] 父节点
        @apiParam {Number} [type=1] 类型ID 1 菜单 2 接口
        @apiParam {Number} [menu_type=1] 1 原生，2，跳转，3，iframe
        @apiParam {Number} [seq=1] 序号 1-9999
        @apiParam {String} [route_name] 前端路由名称
        @apiParam {String} [url] 接口url
        @apiParam {String} [link] 备注
        @apiParam {String} [icon] icon
        @apiParam {String} [memo] 接口url


        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "pk": 43,
                    "name": "提交记录",
                    "code": "TJB3412",
                    "parent": null,
                    "type": 1,
                    "menu_type": 1,
                    "seq": 10,
                    "route_name": "tasklist",
                    "url": "task/list",
                    "link": "",
                    "memo": "asdfasdfasdf",
                    "create_time": "2020-05-13T06:59:00.219Z",
                    "update_time": "2020-05-13T06:59:00.219Z"
                }
            }
        """
        resource = ResourceForm(request.REQUEST)
        if not resource.is_valid():
            failed_dict = resource.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        resource = resource.clean()
        resource['parent_id'] = resource.pop('parent')
        resource = Resource(**resource)
        resource.save()
        return MongoJsonResponse(ok(model_to_mongo(resource)))


class ResourcesDetailView(View):
    def get(self, request, rid, **kwargs):
        """
        @api {GET} api/auth/resources:id 资源详情
        @apiVersion 1.0.0
        @apiName Resources Detail
        @apiGroup Auth
        @apiDescription 资源详情

        @apiParam {Number} id 资源id

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "pk": 45,
                    "name": "efs",
                    "code": "RWLB72",
                    "parent": 1,
                    "type": 1,
                    "menu_type": 1,
                    "seq": 10,
                    "route_name": "tasasdfklist",
                    "url": "task/list",
                    "link": "",
                    "memo": "asdfasdfasasdfdf",
                    "create_time": "2020-05-13T07:06:12Z",
                    "update_time": "2020-05-19T04:57:42Z"
                }
            }

        """
        return MongoJsonResponse(ok(model_to_mongo(Resource.objects.get(pk=rid))))

    def put(self, request, rid):
        """
        @api {PUT} api/auth/resources/:rid 修改资源
        @apiVersion 1.0.0
        @apiName Put Resources
        @apiGroup Auth
        @apiDescription 修改资源

        @apiParam {Number} rid 资源 ID.
        @apiParam {String} [name] 名称
        @apiParam {String} [code] code,唯一
        @apiParam {Number} [parent] 父节点
        @apiParam {Number} [type] 类型ID 1 菜单 2 接口
        @apiParam {Number} [menu_type] 1 原生，2，跳转，3，iframe
        @apiParam {Number} [seq] 序号 1-9999
        @apiParam {String} [route_name] 前端路由名称
        @apiParam {String} [url] 接口url
        @apiParam {String} [link] 备注
        @apiParam {String} [icon] icon
        @apiParam {String} [memo] 接口url

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "pk": 43,
                    "name": "提交记录",
                    "code": "TJB3412",
                    "parent": null,
                    "type": 1,
                    "menu_type": 1,
                    "seq": 10,
                    "route_name": "tasklist",
                    "url": "task/list",
                    "link": "",
                    "memo": "asdfasdfasdf",
                    "create_time": "2020-05-13T06:59:00.219Z",
                    "update_time": "2020-05-13T06:59:00.219Z"
                }
            }
        """
        if not Resource.objects.filter(pk=rid).exists():
            return JsonResponse(ERROR.NOT_FOUND_404)

        resource = ResourceUpdateForm(request.REQUEST)
        if not resource.is_valid():
            failed_dict = resource.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        resource = visible(resource.clean(), request.REQUEST)
        if resource.get('parent', None):
            resource['parent_id'] = resource.pop('parent')
        resource['update_time'] = datetime.datetime.now()
        Resource.objects.filter(id=rid).update(**resource)
        return MongoJsonResponse(ok(model_to_mongo(Resource.objects.get(id=rid))))

    def delete(self, request, rid):
        """
        @api {DELETE} api/auth/resources/:id 资源删除
        @apiVersion 1.0.0
        @apiName Resources Delete
        @apiGroup Auth
        @apiDescription 资源删除



        @apiSuccessExample Response-Success:
        HTTP 1.1/ 200K
        {
            "code": 200,
            "msg": "ok",
            "data": null
        """
        Resource.objects.filter(pk=rid).delete()
        return JsonResponse(ok())


class ResourcesTreeView(View):

    def get(self, request):
        """
        @api {GET} api/auth/resources/tree 资源树
        @apiVersion 1.0.0
        @apiName ResourceTree
        @apiGroup Auth
        @apiDescription 资源树
        @apiHeaderExample {json} Header-Example:
        {
         "Content-Type": "application/json"
       }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                'code': 200,
                'msg': 'ok'
                'data':[
                    {
                        "pk": 1,
                        "name": "系统管理",
                        "code": "RWLB6",
                        "parent": null,
                        "type": 1,
                        "menu_type": 1,
                        "seq": 10,
                        "route_name": "tasklist",
                        "url": "task/list",
                        "link": "",
                        "memo": "asdfasdfasdf",
                        "create_time": "2020-05-03T08:31:47Z",
                        "update_time": "2020-05-03T19:12:58Z",
                        "children": []

                    }
                ]
            }
        """
        resources = Resource.objects.all()
        for r in resources:
            if r.parent and r.parent.id == r.id:
                r.parent = None
        roots = model_list_to_mongo(list(filter(lambda r: not r.parent, resources)))
        roots = sorted(roots, key=lambda x: x.get('seq') * -1)
        tree = Resource.tree(model_list_to_mongo(resources), roots)
        return MongoJsonResponse({'data': tree})


class MenuTreeView(View):

    def get(self, request):
        """
        @api {GET} api/auth/menu/tree 菜单树
        @apiVersion 1.0.0
        @apiName MenuTree
        @apiGroup Auth
        @apiDescription 菜单树
        @apiHeaderExample {json} Header-Example:
        {
         "Content-Type": "application/json"
       }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                'code': 200,
                'msg': 'ok'
                'data':[
                    {
                        "pk": 1,
                        "name": "系统管理",
                        "code": "RWLB6",
                        "parent": null,
                        "type": 1,
                        "menu_type": 1,
                        "seq": 10,
                        "route_name": "tasklist",
                        "url": "task/list",
                        "link": "",
                        "memo": "asdfasdfasdf",
                        "create_time": "2020-05-03T08:31:47Z",
                        "update_time": "2020-05-03T19:12:58Z",
                        "children": []

                    }
                ]
            }
        """

        resources = Resource.objects.filter(type=1).all()
        for r in resources:
            if r.parent and r.parent.id == r.id:
                r.parent = None
        roots = model_list_to_mongo(list(filter(lambda r: not r.parent, resources)))
        for r in roots:
            if r.get('parent', None) and r.get('parent') == r.get('pk'):
                r['parent'] = None
        roots = sorted(roots, key=lambda x: x.get('seq') * -1)
        tree = Resource.tree(model_list_to_mongo(resources), roots)
        return MongoJsonResponse(ok(tree))


class UserMenuTreeView(View):

    def getMenus(self, user):
        user = User.objects.get(id=user.id)
        resources = Resource.objects.filter(type=1).all() if user.is_superuser else user.resources()
        for r in resources:
            if r.parent and r.parent.id == r.id:
                r.parent = None

        roots = model_list_to_mongo(list(filter(lambda r: not r.parent, resources)))
        roots = sorted(roots, key=lambda x: x.get('seq') * -1)
        tree = Resource.tree(model_list_to_mongo(resources), roots)
        return tree

    def get(self, request):
        """
        @api {GET} api/auth/user/menu/tree 用户菜单树
        @apiVersion 1.0.0
        @apiName UserMenuTree
        @apiGroup Auth
        @apiDescription 用户菜单树
        @apiHeaderExample {json} Header-Example:
        {
         "Content-Type": "application/json"
       }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                'code': 200,
                'msg': 'ok'
                'data':[
                    {
                        "pk": 1,
                        "name": "系统管理",
                        "code": "RWLB6",
                        "parent": null,
                        "type": 1,
                        "menu_type": 1,
                        "seq": 10,
                        "route_name": "tasklist",
                        "url": "task/list",
                        "link": "",
                        "memo": "asdfasdfasdf",
                        "create_time": "2020-05-03T08:31:47Z",
                        "update_time": "2020-05-03T19:12:58Z",
                        "children": []

                    }
                ]
            }
        """
        user = request.user
        return MongoJsonResponse(ok(self.getMenus(user)))


class RolesDetailView(View):
    def get(self, request, rid, **kwargs):
        """
        @api {GET} api/auth/roles/:id 角色详情
        @apiVersion 1.0.0
        @apiName Roles Detail
        @apiGroup Auth
        @apiDescription 角色详情

        @apiParam {Number}  id 角色id

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "pk": 5,
                    "name": "role5",
                    "status": 1,
                    "memo": "asdasdfasdff",
                    "create_time": "2020-05-18T10:47:03.027Z",
                    "update_time": "2020-05-19T05:05:29.872Z",
                    "resources": []
                }
            }

        """
        return MongoJsonResponse(ok(model_to_mongo(Role.objects.get(pk=rid))))

    def put(self, request, rid):
        """
        @api {PUT} api/auth/roles/:rid 修改角色
        @apiVersion 1.0.0
        @apiName Put Roles
        @apiGroup Auth
        @apiDescription 修改角色

        @apiParam {Number} rid 资源 ID.
        @apiParam {String} [name] 名称
        @apiParam {String} [memo] memo
        @apiParam {List} [resources] 资源id列表，例如[1,2]

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K

        """
        if not Role.objects.filter(pk=rid).exists():
            return JsonResponse(ERROR.NOT_FOUND_404)
        r = Role.objects.get(pk=rid)
        role = RoleUpdateForm(request.REQUEST)
        if not role.is_valid():
            failed_dict = role.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        role = visible(role.clean(), request.REQUEST)
        if 'resources' in role.keys():
            resources = role.get('resources', [])
            del role['resources']
            r.resources.set(resources)

        role['update_time'] = datetime.datetime.now()
        Role.objects.filter(pk=rid).update(**role)
        return MongoJsonResponse(ok(model_to_mongo(Role.objects.get(pk=rid))))

    def delete(self, request, rid):
        """
        @api {DELETE} api/auth/roles/:id 角色删除
        @apiVersion 1.0.0
        @apiName Roles Delete
        @apiGroup Auth
        @apiDescription 角色删除



        @apiSuccessExample Response-Success:
        HTTP 1.1/ 200K
        {
            "code": 200,
            "msg": "ok",
            "data": null
        """
        role = Role.objects.get(pk=rid)
        if role.resources:
            return JsonResponse(ERROR.ROLE_RESOURCE_NOT_EMPTY)
        Role.objects.filter(pk=rid).delete()
        return JsonResponse(ok())


class AllRolesView(View):
    def get(self, request, **kwargs):
        """
        @api {GET} api/auth/roles/all 所有可选角色
        @apiVersion 1.0.0
        @apiName Roles All
        @apiGroup Auth
        @apiDescription 所有可选角色

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": [
                    {
                        "pk": 1,
                        "name": "主观评价者",
                        "status": 1,
                        "memo": null,
                        "create_time": "2020-05-18T18:34:35Z",
                        "update_time": "2020-05-18T18:34:44Z",
                        "resources": [
                            1,
                            2,
                            4
                        ]
                    },
                    {
                        "pk": 2,
                        "name": "role1",
                        "status": 1,
                        "memo": "asdf",
                        "create_time": "2020-05-18T10:45:38.396Z",
                        "update_time": "2020-05-18T10:45:38.396Z",
                        "resources": []
                    },
                    {
                        "pk": 5,
                        "name": "role5",
                        "status": 1,
                        "memo": "asdasdfasdff",
                        "create_time": "2020-05-18T10:47:03.027Z",
                        "update_time": "2020-05-19T05:05:29.872Z",
                        "resources": []
                    }
                ]
            }
        """
        return MongoJsonResponse(ok(model_list_to_mongo(Role.objects.filter(status=1))))


class RolesView(View):

    def get(self, request, **kwargs):
        """
        @api {GET} api/auth/roles 角色列表
        @apiVersion 1.0.0
        @apiName Roles List
        @apiGroup Auth
        @apiDescription 角色列表

        @apiParam {Number}  [page=1] 当前页码 url参数 ?page=
        @apiParam {Number}  [limit=25] 每页记录数 url参数 ?limit=

        @apiParam {String}  [name] 名称.
        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "itemsPerPage": "2",
                    "totalItems": 1,
                    "totalPages": 1,
                    "data": [
                        {
                            "pk": 1,
                            "name": "主观评价者",
                            "status": 1,
                            "memo": null,
                            "create_time": "2020-05-18T18:34:35Z",
                            "update_time": "2020-05-18T18:34:44Z",
                            "resources": []
                        }
                    ]
                }
            }

        """
        name = request.REQUEST.get('name', None)
        index, per_page = page_get(request.GET)
        query = {}
        if name:
            query['name__startswith'] = name
        return page(Role.objects.filter(**query), index, per_page, lambda x: model_to_mongo(x))

    def post(self, request):
        """
        @api {POST} api/auth/roles 创建角色
        @apiVersion 1.0.0
        @apiName Create Roles
        @apiGroup Auth
        @apiDescription 创建角色

        @apiParam {String} name 名称
        @apiParam {Number} status 状态，1 启用，2 停用
        @apiParam {String} [memo] 备注
        @apiParam {List} [resources] 资源id列表，例如[1,2]


        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
           {
                "code": 200,
                "msg": "ok",
                "data": {
                    "pk": 5,
                    "name": "role2",
                    "status": 1,
                    "memo": "asdf",
                    "create_time": "2020-05-18T10:47:03.027Z",
                    "update_time": "2020-05-18T10:47:03.027Z",
                    "resources": []
                }
            }
        """
        role = RoleForm(request.REQUEST)
        if not role.is_valid():
            failed_dict = role.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        role = role.clean()
        resources = []
        if 'resources' in role.keys():
            resources = role.get('resources', [])
            del role['resources']

        role = Role(**role)
        role.save()
        if resources:
            role.resources.set(resources)
        return MongoJsonResponse(ok(model_to_mongo(role)))
