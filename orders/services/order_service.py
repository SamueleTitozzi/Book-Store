from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from mysite.models import Book
from orders.models import Order, OrderItem


class InsufficientStockError(Exception):
    """
    Власний виняток для ситуацій, коли кількість товару перевищує доступний залишок.
    - Зберігає назву книги та доступну кількість.
    - Формує повідомлення: "Недостатньо товару «назва» (залишок: X)".
    Використовується у методах add_book_to_order та increase_quantity.
    """
    def __init__(self, book_title, available):
        self.book_title = book_title
        self.available = available
        super().__init__(f"Недостатньо товару «{book_title}» (залишок: {available})")


def get_pending_order(user):
    """
    Повертає останнє неоплачене замовлення користувача зі статусом 'pending'.
    - Якщо користувач не автентифікований → повертає None.
    - Якщо є кілька замовлень у статусі 'pending' → бере останнє (за id).
    Використовується як базова функція у багатьох інших методах.
    """
    """Повертає останнє неоплачене замовлення або None."""
    if not user.is_authenticated:
        return None
    return Order.objects.filter(user=user, status='pending').order_by('-id').first()


def get_cart_item_count(user):
    """
    Рахує кількість товарів у кошику користувача.
    - Використовує get_pending_order для отримання замовлення.
    - Якщо замовлення немає → повертає 0.
    - Якщо є → рахує суму quantity у всіх OrderItem.
    Використовується для відображення кількості товарів у UI (іконка кошика).
    """
    order = get_pending_order(user)
    if not order:
        return 0
    return order.items.aggregate(total=Sum('quantity'))['total'] or 0


def get_or_create_order(user):
    """
    Повертає існуюче замовлення зі статусом 'pending' або створює нове.
    - Якщо знайдено замовлення → видаляє інші 'pending' замовлення цього користувача.
    - Якщо немає → створює нове замовлення зі статусом 'pending'.
    Використовується при додаванні товарів у кошик.
    """
    order = get_pending_order(user)
    if order:
        Order.objects.filter(user=user, status='pending').exclude(id=order.id).delete()
        return order
    return Order.objects.create(user=user, status='pending')


def get_unpaid_order_for_user(user):
    """
    Синонім get_pending_order.
    Використовується у checkout для отримання неоплаченого замовлення.
    """
    return get_pending_order(user)


@transaction.atomic
def add_book_to_order(order, book_id):
    """
    Додає книгу у замовлення.
    - Використовує select_for_update для блокування книги (щоб уникнути гонок).
    - Якщо книга вже є у замовленні → збільшує кількість.
    - Якщо книги немає → створює новий OrderItem.
    - Якщо кількість перевищує stock → кидає InsufficientStockError.
    Використовується при додаванні товару у кошик.
    """
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
    """
    Збільшує кількість товару у замовленні на 1.
    - Використовує select_for_update для блокування книги.
    - Якщо кількість перевищує stock → кидає InsufficientStockError.
    - Інакше збільшує quantity і зберігає.
    Використовується у UI кнопці "+".
    """
    book = Book.objects.select_for_update().get(pk=order_item.book_id)
    if order_item.quantity + 1 > book.stock:
        raise InsufficientStockError(book.title, book.stock)

    order_item.quantity += 1
    order_item.save(update_fields=['quantity'])
    return order_item


@transaction.atomic
def decrease_quantity(order_item):
    """
    Зменшує кількість товару у замовленні на 1.
    - Якщо кількість > 1 → зменшує і зберігає.
    - Якщо кількість = 1 → видаляє OrderItem.
    Використовується у UI кнопці "–".
    """
    if order_item.quantity > 1:
        order_item.quantity -= 1
        order_item.save(update_fields=['quantity'])
    else:
        order_item.delete()


@transaction.atomic
def clear_pending_order(user):
    """
    Видаляє неоплачене замовлення користувача (зі статусом 'pending').
    - Якщо замовлення є → видаляє його.
    - Якщо немає → повертає None.
    Використовується при очищенні кошика.
    """
    order = get_pending_order(user)
    if order:
        order.delete()
    return order


@transaction.atomic
def mark_order_as_paid(order):
    """
    Позначає замовлення як оплачене.
    - Якщо вже оплачено → повертає False.
    - Інакше:
      * ставить is_paid=True
      * змінює статус на 'processing'
      * додає дату paid_at
      * зберігає зміни
    Використовується після успішної онлайн-оплати.
    """
    if order.is_paid:
        return False

    order.is_paid = True
    order.status = 'processing'
    order.paid_at = timezone.now()
    order.save(update_fields=['is_paid', 'status', 'paid_at'])
    return True


@transaction.atomic
def update_order_from_checkout(order, cleaned_data):
    """
    Оновлює замовлення даними з форми checkout.
    - Для кожного поля у cleaned_data → оновлює значення у замовленні.
    - Зберігає зміни.
    Використовується при підтвердженні замовлення.
    """
    for field, value in cleaned_data.items():
        setattr(order, field, value)
    order.save()
    return order


@transaction.atomic
def process_cod_order(order):
    """
    Обробка замовлення з оплатою при отриманні (Cash on Delivery).
    - Переводить замовлення у статус 'processing' (замовлення прийняте в роботу).
    - Позначає, що оплата ще не здійснена (is_paid=False).
    - Зберігає зміни у базі даних.
    Використовується у checkout для замовлень з оплатою при отриманні.
    """
    order.status = 'processing'
    order.is_paid = False
    order.save(update_fields=['status', 'is_paid'])
    return order


class OrderCancellationError(Exception):
    """
    Власний виняток для ситуацій, коли замовлення не можна скасувати.
    Використовується у методах cancel_order та complete_return_and_refund.
    """
    pass


@transaction.atomic
def restore_order_stock(order):
    """
    Повертає товари зі скасованого/поверненого замовлення назад на склад.
    - Для кожного товару в замовленні бере відповідну книгу.
    - Використовує select_for_update() для блокування рядка у БД (щоб уникнути гонок).
    - Збільшує залишок (stock) на кількість у замовленні.
    - Зберігає зміни.
    Викликається у cancel_order та complete_return_and_refund.
    """
    for item in order.items.select_related('book'):
        book = Book.objects.select_for_update().get(pk=item.book_id)
        book.stock += item.quantity
        book.save(update_fields=['stock'])


@transaction.atomic
def cancel_order(order):
    """
    Скасовує замовлення з урахуванням його статусу та способу оплати.
    Логіка:
    1. Якщо замовлення не можна скасувати (can_be_cancelled=False) → виняток.
    2. Якщо статус = PROCESSING:
       - Якщо онлайн-оплата → викликає refund_payment(order) і ставить refunded_at.
       - Повертає товари на склад (restore_order_stock).
       - Стає статус CANCELLED.
    3. Якщо статус = SHIPPED або DELIVERED:
       - Якщо онлайн-оплата → статус стає RETURN_PENDING (очікує повернення).
       - Якщо COD → одразу CANCELLED.
    4. Інакше → виняток.
    Повертає 'cancelled' або 'return_pending'.
    """
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
    """
    Завершує процес повернення товару і робить refund (якщо була онлайн-оплата).
    - Перевіряє, що статус = RETURN_PENDING.
    - Якщо онлайн-оплата і ще не було refund → викликає refund_payment.
    - Повертає товари на склад (restore_order_stock).
    - Стає статус CANCELLED.
    Використовується у бек-офісі, коли товар реально повернувся.
    """
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