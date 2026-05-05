from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Category(models.Model):
    title = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class Book(models.Model):
    title = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    author = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    image_path = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.title


# class Order(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(default=timezone.now)
#     is_paid = models.BooleanField(default=False)
#     stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
#
#     def get_total_price(self):
#         return sum(item.book.price * item.quantity for item in self.items.all())
#
#     def __str__(self):
#         return self.user.username
#
#
# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
#     book = models.ForeignKey(Book, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField(default=1)
#
#     def get_total_price(self):
#         return self.quantity * self.book.price
#
#     def __str__(self):
#         return self.book.title
