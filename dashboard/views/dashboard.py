from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from dashboard.services.services import get_user_roles, is_admin_user
from dashboard.decorators import admin_required

# ==========================================================
# Dashboard
# ==========================================================

@login_required
@admin_required
def dashboard_home(request):
    user = request.user
    roles = get_user_roles(request.user)

    return render(
        request,
        "dashboard/home.html",
        {"roles": roles}
    )

