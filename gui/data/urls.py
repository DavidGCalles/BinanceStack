from django.urls import path

from . import views

urlpatterns = [
    path('getTradeable', views.getTradeable, name='getTradeable'),
    path('putTrading', views.putTrading, name='putTrading'),
    path('putTraded', views.putTraded, name='putTraded'),
    path('getBestShift', views.getBestShift, name='getBestShift')
]