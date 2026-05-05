from django.db import transaction
from django.utils import timezone

from mysite.models import Book
from orders.models import Order, OrderItem


# ---------------------------------------------------------------------------------------------------------------------
# Section: Order management (створення та пошук замовлень)
# ---------------------------------------------------------------------------------------------------------------------
def get_or_create_order(user):
    orders = Order.objects.filter(user=user, status='pending').order_by('-id')

    if orders.exists():
        # залишаємо тільки останній
        main_order = orders.first()

        # видаляємо інші
        orders.exclude(id=main_order.id).delete()

        return main_order

    return Order.objects.create(user=user, status='pending')


def get_unpaid_order_for_user(user):
    """Повертає неоплачене замовлення користувача або None."""
    return Order.objects.filter(user=user, status='pending').last()


# ---------------------------------------------------------------------------------------------------------------------
# Section: Cart items (робота з товарами у замовленні)
# ---------------------------------------------------------------------------------------------------------------------
@transaction.atomic
def add_book_to_order(order, book_id):
    """Додає книгу у замовлення або збільшує кількість."""
    book = Book.objects.select_for_update().get(pk=book_id)

    order_item, created = OrderItem.objects.get_or_create(
        order=order,
        book=book,
        defaults={
            'price': book.price,
            'quantity': 1
        }
    )

    if not created:
        order_item.quantity += 1
        order_item.save(update_fields=['quantity'])

    return order_item


@transaction.atomic
def increase_quantity(order_item):
    """Збільшує кількість товару."""
    order_item.quantity += 1
    order_item.save(update_fields=['quantity'])
    return order_item


@transaction.atomic
def decrease_quantity(order_item):
    """Зменшує кількість або видаляє товар."""
    if order_item.quantity > 1:
        order_item.quantity -= 1
        order_item.save(update_fields=['quantity'])
    else:
        order_item.delete()


@transaction.atomic
def clear_order(order):
    """Очищає замовлення (видаляє всі товари)."""
    order.items.all().delete()


# ---------------------------------------------------------------------------------------------------------------------
# Section: Payment status (оплата замовлення)
# ---------------------------------------------------------------------------------------------------------------------
@transaction.atomic
def mark_order_as_paid(order):
    if not order.is_paid:
        order.is_paid = True
        order.status = 'processing'
        order.paid_at = timezone.now()
        order.save(update_fields=['is_paid', 'status', 'paid_at'])
        return True
    return False


@transaction.atomic
def mark_order_as_processing(order):
    """Переводить замовлення у статус 'В обробці'."""
    if order.status == 'pending':
        order.status = 'processing'
        order.save(update_fields=['status'])
        return True
    return False


@transaction.atomic
def mark_order_as_shipped(order):
    """Позначає замовлення як 'Відправлене'."""
    if order.status == 'processing':
        order.status = 'shipped'
        order.save(update_fields=['status'])
        return True
    return False


@transaction.atomic
def mark_order_as_delivered(order):
    """Позначає замовлення як 'Доставлене'."""
    if order.status == 'shipped':
        order.status = 'delivered'
        order.save(update_fields=['status'])
        return True
    return False


@transaction.atomic
def mark_order_as_cancelled(order):
    """Позначає замовлення як 'Скасоване'."""
    if order.status != 'delivered':
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return True
    return False


@transaction.atomic
def update_order_from_checkout(order, cleaned_data):
    """Заповнює замовлення даними з форми"""
    for field, value in cleaned_data.items():
        setattr(order, field, value)

    order.save()
    return order


@transaction.atomic
def process_cod_order(order):
    """Обробка наложеного платежу"""
    order.status = 'processing'
    order.is_paid = False  # 🔥 ключове
    order.save(update_fields=['status', 'is_paid'])
    return order
