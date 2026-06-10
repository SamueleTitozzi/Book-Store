from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from mysite.models import Book


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Очікує оплати'),
        ('paid', 'Оплачено'),
        ('processing', 'В обробці'),
        ('shipped', 'Відправлено'),
        ('delivered', 'Доставлено'),
        ('cancelled', 'Скасовано'),
        ('refunded', 'Повернено кошти')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # нові поля для даних покупця
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(default='unknown@example.com', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(default='Не вказано', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)

    delivery_method = models.CharField(
        max_length=50,
        choices=[('nova_poshta', 'Нова Пошта'), ('courier', 'Кур’єр')],
        default='nova_poshta'
    )
    payment_method = models.CharField(
        max_length=50,
        choices=[('stripe', 'Stripe'), ('cod', 'Наложений платіж')],
        default='stripe'
    )

    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())

    """Замовлення можна скасувати лише поки воно не передано в обробку."""

    @property
    def can_be_cancelled(self):
        return self.status not in [
            'shipped',
            'delivered',
            'cancelled',
            'refunded'
        ]

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
