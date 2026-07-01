from django.contrib.auth.models import Group
from django.contrib.auth.decorators import user_passes_test

from dashboard.decorators import is_admin_user

def get_user_roles(user):
    """
    Повертає список ролей користувача.
    """

    if user.is_superuser:
        return ["products", "orders"]

    roles = []

    if user.groups.filter(name="ProductManager").exists():
        roles.append("products")

    if user.groups.filter(name="OrderManager").exists():
        roles.append("orders")

    return roles

# ==========================================================
# Перевірка доступу до dashboard
# ==========================================================

def is_admin_user(user):
    return (
            user.is_authenticated
            and (
                    user.is_superuser
                    or user.groups.filter(
                name__in=[
                    "ProductManager",
                    "OrderManager"
                ]
            ).exists()
            )
    )


admin_required = user_passes_test(
    is_admin_user,
    login_url='mysite:login'
)