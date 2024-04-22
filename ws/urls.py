from django.urls import path

from ws.views import TestView, MqTestView, SysLogTestView

urlpatterns = [
    path('test', TestView.as_view()),
    path('mqtest', MqTestView.as_view()),
    path('syslogtest', SysLogTestView.as_view())

]
