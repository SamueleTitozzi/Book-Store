from django.contrib.auth.decorators import user_passes_test


def is_admin_user(user):
    return (
        user.is_superuser
        or user.groups.filter(
            name__in=["ProductManager", "OrderManager"]
        ).exists()
    )


admin_required = user_passes_test(
    is_admin_user,
    login_url="mysite:login"
)