from django.urls import path
from . import views

urlpatterns = [
    path('', views.score, name="score"),
    path('compare/', views.compare_image, name="compare_image"),
    path('status/<int:task_id>/', views.check_status, name="check_status"),
]