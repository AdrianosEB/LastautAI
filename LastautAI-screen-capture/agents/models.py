from django.db import models


class AgentRun(models.Model):
    agent_name = models.CharField(max_length=100)
    task = models.TextField()
    result = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent_name} - {self.created_at:%Y-%m-%d %H:%M}"
