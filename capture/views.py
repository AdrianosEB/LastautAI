import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import WorkflowSuggestion
from .analyzer import analyze_frame


@login_required
def monitor(request):
    suggestions = WorkflowSuggestion.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]

    return render(request, 'capture/monitor.html', {
        'suggestions': suggestions,
    })


@login_required
@require_POST
def receive_frame(request):
    data   = json.loads(request.body)
    image  = data.get('image', '')
    clicks = data.get('clicks', [])

    if not image:
        return JsonResponse({'status': 'skipped'})

    description = analyze_frame(image, clicks)
    print(f'[Analyzer] response: {description}')

    return JsonResponse({'status': 'ok', 'description': description})


@login_required
@require_POST
def save_suggestion(request):
    data = json.loads(request.body)
    description = data.get('description', '').strip()
    if not description:
        return JsonResponse({'error': 'No description provided.'}, status=400)
    suggestion = WorkflowSuggestion.objects.create(
        user=request.user,
        description=description,
        raw_events=data.get('raw_events', ''),
        status='approved',
    )
    return JsonResponse({'id': suggestion.id})


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
