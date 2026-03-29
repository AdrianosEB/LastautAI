from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="agent_dashboard"),
    path("run/", views.run_agent, name="run_agent"),
    # Workflow pipeline
    path("workflows/generate/", views.generate_workflow_view, name="workflow_generate"),
    path("workflows/generate/steps/", views.generate_workflow_steps_view, name="workflow_generate_steps"),
    path("workflows/run/", views.run_workflow_view, name="workflow_run"),
    path("workflows/history/", views.workflow_history_view, name="workflow_history"),
    path("workflows/<int:pk>/", views.workflow_detail_view, name="workflow_detail"),
]
