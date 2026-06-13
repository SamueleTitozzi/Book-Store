from orders.services.order_service import get_pending_order


class PendingOrderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.pending_order = get_pending_order(request.user)
        return self.get_response(request)
