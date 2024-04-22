from django.urls import path

from attachment.views import *

urlpatterns = [
    path('file/put', MiniFileView.as_view()),
    path('file/part/init', MultiPartInitView.as_view()),
    path('file/<str:id>/part/put', MultiPartPutView.as_view()),
    path('file/<str:id>', FileStorageDetailView.as_view()),
    path('file/<str:id>/part/complete', PartCompleteView.as_view()),
    path('file/<str:id>/preview', PreviewView.as_view()),
    path('file/<str:id>/download', DownloadView.as_view()),
    path('files', FileStorageView.as_view()),

]
