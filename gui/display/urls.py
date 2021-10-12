from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('Trading', views.Trading, name='Trading'),
    path('Traded', views.Traded, name='Traded'),
    path('Graph', views.Graph, name='Graph'),
    path('Stats', views.Stats, name='Stats'),
    path('Efectivity', views.Efectivity, name='Efectivity'),
]