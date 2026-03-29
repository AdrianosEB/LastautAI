from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="agent_dashboard"),
    path("run/", views.run_agent, name="run_agent"),
]
