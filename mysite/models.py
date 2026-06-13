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
