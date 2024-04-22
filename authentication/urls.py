from django.urls import path

from .views import *

urlpatterns = [
    path('users', UsersView.as_view()),
    path('users/current', CookieUserDetail.as_view()),
    path('users/<int:uid>', UsersDetailView.as_view()),
    path('signup', SignUpView.as_view()),
    path('login', LogInView.as_view()),
    path('logout', LogOutView.as_view()),
    path('resetpwd', PasswordView.as_view()),

    path('resources', ResourcesView.as_view()),
    path('resources/<int:rid>', ResourcesDetailView.as_view()),
    path('resources/tree', ResourcesTreeView.as_view()),
    path('menu/tree', MenuTreeView.as_view()),
    path('user/menu/tree', UserMenuTreeView.as_view()),

    path('roles/<int:rid>', RolesDetailView.as_view()),
    path('roles', RolesView.as_view()),
    path('roles/all', AllRolesView.as_view()),

]
