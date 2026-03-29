from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.monitor,           name='monitor'),
    path('frame/',                    views.receive_frame,     name='receive_frame'),
    path('save/',                     views.save_suggestion,   name='save_suggestion'),
    path('suggestions/',              views.get_suggestions,   name='get_suggestions'),
    path('suggestions/<int:pk>/',     views.update_suggestion, name='update_suggestion'),
]
