from django.db import models
from django.contrib.auth.models import User


class EventLog(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp    = models.DateTimeField(auto_now_add=True)
    event_type   = models.CharField(max_length=50)   # "click", "app_switch"
    app_name     = models.CharField(max_length=200)
    window_title = models.CharField(max_length=500, blank=True)
    detail       = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.timestamp:%H:%M:%S} [{self.event_type}] {self.app_name}"


class WorkflowSuggestion(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('dismissed', 'Dismissed'),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at  = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    raw_events  = models.TextField()
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.user.username} — {self.created_at:%Y-%m-%d %H:%M} ({self.status})"
