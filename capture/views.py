import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from . import recorder as rec
from .models import WorkflowSuggestion


@login_required
def monitor(request):
    suggestions = WorkflowSuggestion.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]

    return render(request, 'capture/monitor.html', {
        'suggestions':   suggestions,
        'is_recording':  rec.is_running(request.user.id),
    })


@login_required
@require_POST
def start_recording(request):
    started = rec.start(request.user.id)
    return JsonResponse({'status': 'started' if started else 'already_running'})


@login_required
@require_POST
def stop_recording(request):
    stopped = rec.stop(request.user.id)
    return JsonResponse({'status': 'stopped' if stopped else 'not_running'})


@login_required
def get_suggestions(request):
    qs = WorkflowSuggestion.objects.filter(
        user=request.user, status='pending'
    ).order_by('-created_at').values('id', 'description', 'created_at')

    suggestions = [
        {**s, 'created_at': s['created_at'].strftime('%b %d, %H:%M')}
        for s in qs
    ]
    return JsonResponse({'suggestions': suggestions})


@login_required
@require_POST
def update_suggestion(request, pk):
    data = json.loads(request.body)
    status = data.get('status')

    if status not in ('approved', 'dismissed'):
        return JsonResponse({'error': 'Invalid status.'}, status=400)

    try:
        suggestion = WorkflowSuggestion.objects.get(pk=pk, user=request.user)
        suggestion.status = status
        suggestion.save()
        return JsonResponse({'ok': True})
    except WorkflowSuggestion.DoesNotExist:
        return JsonResponse({'error': 'Not found.'}, status=404)
