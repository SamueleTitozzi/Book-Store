from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from mysite.models import Book


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_RETURN_PENDING = 'return_pending'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Очікує оплати'),
        ('paid', 'Оплачено'),
        (STATUS_PROCESSING, 'В обробці'),
        (STATUS_SHIPPED, 'Відправлено'),
        (STATUS_DELIVERED, 'Доставлено'),
        (STATUS_CANCELLED, 'Скасовано'),
        (STATUS_RETURN_PENDING, 'Очікує повернення'),
        (STATUS_REFUNDED, 'Повернено кошти'),
    ]

    STATUS_BADGE_CLASSES = {
        STATUS_PENDING: 'bg-secondary',
        STATUS_PROCESSING: 'bg-warning text-dark',
        STATUS_SHIPPED: 'bg-info text-dark',
        STATUS_DELIVERED: 'bg-primary',
        STATUS_CANCELLED: 'bg-danger',
        STATUS_RETURN_PENDING: 'bg-warning text-dark',
        STATUS_REFUNDED: 'bg-info text-dark',
        'paid': 'bg-success',
    }

    CANCELLABLE_STATUSES = (
        STATUS_PROCESSING,
        STATUS_SHIPPED,
        STATUS_DELIVERED,
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(default='unknown@example.com', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(default='Не вказано', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)

    delivery_method = models.CharField(
        max_length=50,
        choices=[('nova_poshta', 'Нова Пошта'), ('courier', 'Кур’єр')],
        default='nova_poshta',
    )
    payment_method = models.CharField(
        max_length=50,
        choices=[('stripe', 'Stripe'), ('cod', 'Наложений платіж')],
        default='stripe',
    )

    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())

    @property
    def is_online_paid(self):
        return self.is_paid and self.payment_method == 'stripe'

    @property
    def is_refunded(self):
        return self.refunded_at is not None

    @property
    def can_be_cancelled(self):
        return self.status in self.CANCELLABLE_STATUSES

    @property
    def status_display_label(self):
        if self.status == self.STATUS_REFUNDED or (
            self.is_refunded and self.status == self.STATUS_CANCELLED
        ):
            return 'Скасовано (кошти повернено)'
        if self.status == self.STATUS_RETURN_PENDING:
            return 'Очікує повернення на склад'
        return self.get_status_display()

    @property
    def status_badge_class(self):
        if self.status == self.STATUS_REFUNDED or (
            self.is_refunded and self.status == self.STATUS_CANCELLED
        ):
            return self.STATUS_BADGE_CLASSES[self.STATUS_REFUNDED]
        return self.STATUS_BADGE_CLASSES.get(self.status, 'bg-secondary')

    @property
    def payment_display_label(self):
        if self.is_refunded:
            return 'Повернено кошти'
        if self.is_paid:
            return 'Оплачено'
        if self.payment_method == 'cod':
            return 'При отриманні'
        return 'Не оплачено'

    @property
    def payment_badge_class(self):
        if self.is_refunded:
            return 'bg-info text-dark'
        if self.is_paid:
            return 'bg-success'
        if self.payment_method == 'cod':
            return 'bg-warning text-dark'
        return 'bg-danger'

    @property
    def is_terminal_status(self):
        return self.status in (
            self.STATUS_CANCELLED,
            self.STATUS_RETURN_PENDING,
            self.STATUS_REFUNDED,
        )

    def __str__(self):
        return f"Order {self.pk} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return self.book.title
