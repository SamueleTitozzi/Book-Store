from orders.services.order_service import get_cart_item_count


def cart_item(request):
    return {'cart_item': get_cart_item_count(request.user)}
