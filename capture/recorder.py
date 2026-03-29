# Recording is now handled client-side via the browser's getDisplayMedia API.
# These stubs keep views.py import-compatible.

def start(user_id):    return True
def stop(user_id):     return True
def is_running(user_id): return False
