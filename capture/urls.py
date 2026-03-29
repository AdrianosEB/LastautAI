from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.monitor,           name='monitor'),
    path('start/',                    views.start_recording,   name='start_recording'),
    path('stop/',                     views.stop_recording,    name='stop_recording'),
    path('suggestions/',              views.get_suggestions,   name='get_suggestions'),
    path('suggestions/<int:pk>/',     views.update_suggestion, name='update_suggestion'),
]
