import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .agent import OrchestratorAgent, MarketingAgent, SalesAgent, CustomerSupportAgent, OperationsAgent
from .models import AgentRun

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
