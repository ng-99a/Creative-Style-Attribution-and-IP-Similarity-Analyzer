from django.urls import path
from . import views

urlpatterns = [
    path('', views.score, name="score"),
    path('explore/', views.explore_art, name="explore_art"),
    path('explore/<int:collection_id>/', views.explore_gallery, name="explore_gallery"),
    path('compare/', views.compare_image, name="compare_image"),
    path('status/<int:task_id>/', views.check_status, name="check_status"),
    path('batch/', views.batch_upload, name="batch_upload"),
    path('batch/compare/', views.batch_compare, name="batch_compare"),
    path('batch/status/<int:batch_id>/', views.batch_status, name="batch_status"),
]