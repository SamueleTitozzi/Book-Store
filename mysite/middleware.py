from orders.services.order_service import get_pending_order
from django.http import HttpResponseNotFound


class PendingOrderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.pending_order = get_pending_order(request.user)
        return self.get_response(request)

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        print("PATH:", request.path)
        print("AUTH:", request.user.is_authenticated)

        if request.path.startswith('/dashboard'):

            if (
                not request.user.is_authenticated
                or (
                    not request.user.is_superuser
                    and not request.user.groups.filter(
                        name__in=["ProductManager", "OrderManager"]
                    ).exists()
                )
            ):
                return HttpResponseNotFound("<h1>404 Not Found</h1>")

        if request.path.startswith('/admin/'):

            if (
                not request.user.is_authenticated
                or not request.user.is_superuser
            ):
                return HttpResponseNotFound("<h1>404 Not Found</h1>")

        return self.get_response(request)
