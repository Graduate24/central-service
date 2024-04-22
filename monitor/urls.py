from django.urls import path

from monitor.views import MonitorView, MonitorDetailView, StatisticsView

urlpatterns = [
    path('clients', MonitorView.as_view()),
    path('clients/<str:id>', MonitorDetailView.as_view()),
    path('statistics', StatisticsView.as_view()),

]
