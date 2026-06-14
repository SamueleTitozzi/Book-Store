from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from mysite.models import Book
from orders.models import Order, OrderItem


class InsufficientStockError(Exception):
    def __init__(self, book_title, available):
        self.book_title = book_title
        self.available = available
        super().__init__(f"Недостатньо товару «{book_title}» (залишок: {available})")


def get_pending_order(user):
    """Повертає останнє неоплачене замовлення або None."""
    if not user.is_authenticated:
        return None
    return Order.objects.filter(user=user, status='pending').order_by('-id').first()


def get_cart_item_count(user):
    order = get_pending_order(user)
    if not order:
        return 0
    return order.items.aggregate(total=Sum('quantity'))['total'] or 0


def get_or_create_order(user):
    order = get_pending_order(user)
    if order:
        Order.objects.filter(user=user, status='pending').exclude(id=order.id).delete()
        return order
    return Order.objects.create(user=user, status='pending')


def get_unpaid_order_for_user(user):
    return get_pending_order(user)


@transaction.atomic
def add_book_to_order(order, book_id):
    book = Book.objects.select_for_update().get(pk=book_id)

    order_item = OrderItem.objects.filter(order=order, book=book).first()
    current_qty = order_item.quantity if order_item else 0

    if current_qty + 1 > book.stock:
        raise InsufficientStockError(book.title, book.stock)

    if order_item:
        order_item.quantity += 1
        order_item.save(update_fields=['quantity'])
        return order_item

    return OrderItem.objects.create(
        order=order,
        book=book,
        price=book.price,
        quantity=1,
    )


@transaction.atomic
def increase_quantity(order_item):
    book = Book.objects.select_for_update().get(pk=order_item.book_id)
    if order_item.quantity + 1 > book.stock:
        raise InsufficientStockError(book.title, book.stock)

    order_item.quantity += 1
    order_item.save(update_fields=['quantity'])
    return order_item


@transaction.atomic
def decrease_quantity(order_item):
    if order_item.quantity > 1:
        order_item.quantity -= 1
        order_item.save(update_fields=['quantity'])
    else:
        order_item.delete()


@transaction.atomic
def clear_pending_order(user):
    order = get_pending_order(user)
    if order:
        order.delete()
    return order


@transaction.atomic
def mark_order_as_paid(order):
    if order.is_paid:
        return False

    order.is_paid = True
    order.status = 'processing'
    order.paid_at = timezone.now()
    order.save(update_fields=['is_paid', 'status', 'paid_at'])
    return True


@transaction.atomic
def update_order_from_checkout(order, cleaned_data):
    for field, value in cleaned_data.items():
        setattr(order, field, value)
    order.save()
    return order


@transaction.atomic
def process_cod_order(order):
    order.status = 'processing'
    order.is_paid = False
    order.save(update_fields=['status', 'is_paid'])
    return order


class OrderCancellationError(Exception):
    pass


@transaction.atomic
def restore_order_stock(order):
    for item in order.items.select_related('book'):
        book = Book.objects.select_for_update().get(pk=item.book_id)
        book.stock += item.quantity
        book.save(update_fields=['stock'])


@transaction.atomic
def cancel_order(order):
    if not order.can_be_cancelled:
        raise OrderCancellationError("Замовлення вже не можна скасувати.")

    now = timezone.now()
    order.cancelled_at = now

    if order.status == Order.STATUS_PROCESSING:
        if order.is_online_paid:
            from orders.services.payment_service import refund_payment
            refund_payment(order)
            order.refunded_at = now

        restore_order_stock(order)
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=['status', 'cancelled_at', 'refunded_at'])
        return 'cancelled'

    if order.status in (Order.STATUS_SHIPPED, Order.STATUS_DELIVERED):
        if order.is_online_paid:
            order.status = Order.STATUS_RETURN_PENDING
            order.save(update_fields=['status', 'cancelled_at'])
            return 'return_pending'

        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=['status', 'cancelled_at'])
        return 'cancelled'

    raise OrderCancellationError("Замовлення вже не можна скасувати.")


@transaction.atomic
def complete_return_and_refund(order):
    if order.status != Order.STATUS_RETURN_PENDING:
        raise OrderCancellationError("Замовлення не очікує повернення товару.")

    now = timezone.now()

    if order.is_online_paid and not order.is_refunded:
        from orders.services.payment_service import refund_payment
        refund_payment(order)
        order.refunded_at = now

    restore_order_stock(order)
    order.status = Order.STATUS_CANCELLED
    order.save(update_fields=['status', 'refunded_at'])