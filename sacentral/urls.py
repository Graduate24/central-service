"""sacentral URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib.staticfiles import views
from django.urls import re_path, include
from django.views.static import serve

from sacentral import settings

urlpatterns = [
    url(r'^api/ws/', include('ws.urls')),
    url(r'^api/monitor/', include('monitor.urls')),
    url(r'^api/auth/', include('authentication.urls')),
    url(r'^api/analysis/', include('analysis.urls')),
    url(r'^api/attachments/', include('attachment.urls')),
    re_path(r'^apidoc/(?P<path>.*)$', serve, {'document_root': settings.APIDOC_ROOT}),
    re_path(r'^code/(?P<path>.*)$', serve, {'document_root': settings.CODE_ROOT}),
]
if settings.DEBUG:
    urlpatterns += [
        url(r'^$', views.serve, kwargs={'path': 'index.html'}),
        url(r'^(?P<path>.*)$', views.serve),
    ]
