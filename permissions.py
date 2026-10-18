from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def role_required(level):
    """level: 'admin' or 'analyst'. Admin passes both; analyst passes 'analyst' only."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            allowed = user.is_admin_role if level == "admin" else user.is_analyst_role
            if not allowed:
                return render(request, "core/forbidden.html", status=403)
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator
