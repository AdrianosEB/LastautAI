import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from .agent import OrchestratorAgent, MarketingAgent, SalesAgent, CustomerSupportAgent, OperationsAgent
from .models import AgentRun, Workflow
from pipeline import generate_workflow, generate_workflow_steps, PipelineError, AmbiguityRejection
from pipeline.executor.engine import execute_workflow

AGENT_MAP = {
    "orchestrator": OrchestratorAgent(),
    "marketing": MarketingAgent(),
    "sales": SalesAgent(),
    "support": CustomerSupportAgent(),
    "operations": OperationsAgent(),
}


@login_required
def dashboard(request):
    recent_runs = AgentRun.objects.order_by("-created_at")[:20]
    return render(request, "agents/dashboard.html", {"recent_runs": recent_runs})


@login_required
@require_POST
def run_agent(request):
    try:
        data = json.loads(request.body)
        task = data.get("task", "").strip()
        agent_key = data.get("agent", "orchestrator")

        if not task:
            return JsonResponse({"error": "Task cannot be empty."}, status=400)

        agent = AGENT_MAP.get(agent_key, AGENT_MAP["orchestrator"])

        if agent_key == "orchestrator":
            output = agent.run(task)
            agent_name = output["agent_name"]
            result = output["result"]
            department = output["department"]
        else:
            result = agent.run(task)
            agent_name = agent.name
            department = agent_key

        AgentRun.objects.create(agent_name=agent_name, task=task, result=result)

        return JsonResponse({
            "agent_name": agent_name,
            "department": department,
            "result": result,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# --- Workflow Pipeline views ---

@login_required
@require_POST
def generate_workflow_view(request):
    """Generate a workflow definition from a natural language description."""
    try:
        data = json.loads(request.body)
        description = data.get("description", "").strip()
        output_format = data.get("output_format", "json")
        strict_mode = data.get("strict_mode", False)

        if not description:
            return JsonResponse({"error": "Description cannot be empty."}, status=400)

        workflow = generate_workflow(
            description=description,
            output_format=output_format,
            strict_mode=strict_mode,
        )

        # Save as a draft workflow
        wf = Workflow.objects.create(
            user=request.user,
            name=workflow.get("name", "Untitled Workflow") if isinstance(workflow, dict) else "Untitled Workflow",
            description=description,
            definition=workflow if isinstance(workflow, dict) else {},
            status="draft",
        )

        return JsonResponse({
            "id": wf.id,
            "workflow": workflow,
        })

    except AmbiguityRejection as e:
        return JsonResponse({
            "error": "ambiguous_input",
            "message": "Input is ambiguous and strict_mode is enabled",
            "ambiguities": e.ambiguities,
        }, status=422)
    except PipelineError as e:
        return JsonResponse({"error": "pipeline_error", "stage": e.stage, "message": e.message}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def generate_workflow_steps_view(request):
    """Generate a workflow with per-stage pipeline debug output."""
    try:
        data = json.loads(request.body)
        description = data.get("description", "").strip()
        strict_mode = data.get("strict_mode", False)

        if not description:
            return JsonResponse({"error": "Description cannot be empty."}, status=400)

        stages = generate_workflow_steps(description=description, strict_mode=strict_mode)
        return JsonResponse(stages)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def run_workflow_view(request):
    """Generate a workflow from a description and execute it immediately."""
    try:
        data = json.loads(request.body)
        description = data.get("description", "").strip()
        strict_mode = data.get("strict_mode", False)

        if not description:
            return JsonResponse({"error": "Description cannot be empty."}, status=400)

        workflow = generate_workflow(description=description, output_format="json", strict_mode=strict_mode)

        wf = Workflow.objects.create(
            user=request.user,
            name=workflow.get("name", "Untitled Workflow"),
            description=description,
            definition=workflow,
            status="running",
        )

        execution = execute_workflow(workflow)

        exec_data = {
            "status": execution.status,
            "total_duration_seconds": round(execution.total_duration_seconds, 2),
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "status": s.status,
                    "output": s.output,
                    "error": s.error,
                    "duration_seconds": round(s.duration_seconds, 2),
                }
                for s in execution.steps
            ],
        }

        wf.execution_result = exec_data
        wf.status = execution.status
        wf.save()

        return JsonResponse({"id": wf.id, "workflow": workflow, "execution": exec_data})

    except AmbiguityRejection as e:
        return JsonResponse({
            "error": "ambiguous_input",
            "ambiguities": e.ambiguities,
        }, status=422)
    except PipelineError as e:
        return JsonResponse({"error": "pipeline_error", "stage": e.stage, "message": e.message}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_GET
def workflow_history_view(request):
    """List all workflows for the current user."""
    workflows = Workflow.objects.filter(user=request.user).values(
        "id", "name", "description", "status", "created_at"
    )
    return JsonResponse({"workflows": list(workflows)})


@login_required
@require_GET
def workflow_detail_view(request, pk):
    """Get a single workflow with its definition and execution result."""
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    return JsonResponse({
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "definition": wf.definition,
        "execution_result": wf.execution_result,
        "status": wf.status,
        "created_at": wf.created_at.isoformat(),
    })
