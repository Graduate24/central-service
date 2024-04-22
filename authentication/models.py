import datetime

from django import forms
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import *
from django.utils.translation import gettext_lazy as _


class MultipleIntegersField(forms.TypedMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        super(MultipleIntegersField, self).__init__(*args, **kwargs)
        self.coerce = int

    def valid_value(self, value):
        return True


class User(AbstractUser):
    phone_number = CharField(max_length=30, verbose_name=_('phone_number'))
    roles = models.ManyToManyField(to="Role", blank=True, null=True, related_name='user', db_table='Auth_user_roles')
    preferred_language = CharField(
        max_length=10,
        default='zh-hans',
        verbose_name=_('preferred language')
    )
    is_deleted = models.SmallIntegerField(null=False, default=0)

    class Meta:
        db_table = "Auth_user"

    def resources(self, type=1):
        rids = Role.objects.filter(id__in=self.roles.all(), status=1).values_list('resources').all()
        return Resource.objects.filter(id__in=rids, type=type).all()


class Resource(models.Model):
    # 资源名称
    name = models.CharField(max_length=50, blank=False)
    code = models.CharField(max_length=16, unique=True, blank=False)
    # 父节点
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children', on_delete=models.SET_NULL)
    # 类型ID 1 菜单 2 接口
    type = models.SmallIntegerField(null=False, default=1)
    # 1 原生，2，跳转，3，iframe
    menu_type = models.SmallIntegerField(null=False, default=1)
    # 序号
    seq = models.SmallIntegerField(null=False, default=1)
    # 前端路由名称
    route_name = models.CharField(max_length=20, null=True)
    # 接口url
    url = models.CharField(max_length=100, null=True)
    # method get,post,put,delete,option
    method = models.CharField(max_length=100, null=True)
    # 链接
    link = models.CharField(max_length=200, null=True)
    icon = models.CharField(max_length=200, null=True)
    # 备注
    memo = models.CharField(max_length=200, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Auth_resource"

    @classmethod
    def tree(cls, full, roots):
        children_list = []

        def get_children(pid):
            return sorted(list(filter(lambda r: r.get('parent') == pid, full)), key=lambda x: x.get('seq') * -1)

        for root in roots:
            children = get_children(root.get('pk'))
            root['children'] = children
            children_list.append(root)
            cls.tree(full, children)
        return children_list

    @staticmethod
    def get_resources(role_ids):
        if not role_ids:
            return []
        resources = Resource.objects.raw(
            'SELECT * FROM Auth_resource r WHERE EXISTS( SELECT 1 FROM Auth_role_resources '
            'rr WHERE rr.resource_id = r.id AND rr.role_id IN %s) AND type = 2', [role_ids])

        return [(r.method, r.url) for r in resources]


class Role(models.Model):
    name = models.CharField(max_length=20, unique=True, blank=False)
    resources = models.ManyToManyField(Resource, blank=True, related_name='role', db_table='Auth_role_resources')
    # 状态，1 启用，2 停用
    status = models.SmallIntegerField(null=False, default=1)
    # 备注
    memo = models.CharField(max_length=200, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Auth_role"

    @staticmethod
    def get_roles(user_id):
        roles = Role.objects.raw(
            'SELECT id FROM Auth_role r WHERE EXISTS( SELECT 1 FROM Auth_user_roles WHERE Auth_user_roles.user_id = %s '
            'AND r.id = Auth_user_roles.role_id) AND STATUS = 1', [user_id]
        )
        return [r.id for r in roles]


class SignupForm(forms.Form):
    username = forms.CharField(required=True, min_length=4,
                               error_messages={"required": "用户名不能为空", "min_length": "用户名最小长度为4"})
    password = forms.CharField(required=True, min_length=6, max_length=18,
                               error_messages={"min_length": "密码最小长度为6", "max_length": "密码最大长度为18"})


class LoginForm(forms.Form):
    username = forms.CharField(required=True, max_length=18, error_messages={"required": "用户名不能为空"})
    password = forms.CharField(required=True, max_length=18, error_messages={"required": "密码不能为空"})


class ResourceForm(forms.Form):
    # 资源名称
    name = forms.CharField(required=True, max_length=50, error_messages={"required": "不能为空"})
    code = forms.CharField(max_length=16, required=True, error_messages={"required": "不能为空"})
    # 父节点
    parent = forms.IntegerField(required=False)
    # 类型ID 1 菜单 2 接口
    type = forms.IntegerField(required=False, max_value=2, min_value=1, initial=1)
    # 1 原生，2，跳转，3，iframe
    menu_type = forms.IntegerField(max_value=3, min_value=1, initial=1)
    # 序号
    seq = forms.IntegerField(max_value=9999, min_value=1, initial=1)
    # 前端路由名称
    route_name = forms.CharField(required=False, max_length=20)
    # 接口url
    url = forms.CharField(required=False, max_length=100)
    # method
    method = forms.CharField(required=False, max_length=100)
    # 链接
    link = forms.CharField(required=False, max_length=200)
    icon = forms.CharField(required=False, max_length=200)
    # 备注
    memo = forms.CharField(required=False, max_length=200)


class ResourceUpdateForm(ResourceForm):
    name = forms.CharField(required=False, max_length=50)
    code = forms.CharField(required=False, max_length=16)
    # 1 原生，2，跳转，3，iframe
    menu_type = forms.IntegerField(required=False, max_value=3, min_value=1)
    # 序号
    seq = forms.IntegerField(required=False, max_value=9999, min_value=1)


class RoleForm(forms.Form):
    name = forms.CharField(required=True, max_length=50, error_messages={"required": "不能为空"})
    # 状态，1 启用，2 停用
    status = forms.IntegerField(required=False, max_value=2, min_value=1, initial=1)
    # 备注
    memo = forms.CharField(required=False, max_length=100)
    resources = MultipleIntegersField(required=False)


class RoleUpdateForm(RoleForm):
    name = forms.CharField(required=False, max_length=50)


class PW(forms.Form):
    password = forms.CharField(required=True, min_length=6, max_length=18,
                               error_messages={"min_length": "密码最小长度为6", "max_length": "密码最大长度为18"})


class UserForm(PW):
    username = forms.CharField(required=True, max_length=50, error_messages={"required": "不能为空"})
    is_superuser = forms.BooleanField(required=False, initial=False)
    first_name = forms.CharField(required=False, max_length=50)
    last_name = forms.CharField(required=False, max_length=50)
    email = forms.CharField(required=False, max_length=50)
    is_staff = forms.BooleanField(required=False, initial=False)
    is_active = forms.BooleanField(required=False, initial=True)
    phone_number = forms.CharField(required=False, max_length=50)
    preferred_language = forms.CharField(required=False, max_length=100, initial='zh-hans')
    date_joined = forms.CharField(required=False, initial=datetime.datetime.now())
    roles = MultipleIntegersField(required=False)


class UserUpdateForm(UserForm):
    username = forms.CharField(required=False, max_length=50, error_messages={"required": "不能为空"})
    is_superuser = forms.BooleanField(required=False)
    is_staff = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False)
    password = forms.CharField(required=False, min_length=6, max_length=18,
                               error_messages={"min_length": "密码最小长度为6", "max_length": "密码最大长度为18"})
