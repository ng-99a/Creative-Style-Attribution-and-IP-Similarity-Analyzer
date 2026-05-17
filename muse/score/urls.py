from django.urls import path
from . import views

urlpatterns = [
    path('', views.score, name="score"),
    path('compare/', views.compare_image, name="compare_image"),
]