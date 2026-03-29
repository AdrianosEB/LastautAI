import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aut_app.settings')
django.setup()
from accounts.models import WaitlistEntry
from django.contrib.auth.models import User

for line in WaitlistEntry.objects.all().values('email', 'joined_at'):
    print(line)
