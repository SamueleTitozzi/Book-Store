from django.contrib import admin, messages

from orders.models import Order, OrderItem
from orders.services.order_service import OrderCancellationError, complete_return_and_refund


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('book', 'quantity', 'price')


@admin.action(description='Підтвердити повернення товару та повернути кошти')
def confirm_return_and_refund(modeladmin, request, queryset):
    success_count = 0
    for order in queryset:
        try:
            complete_return_and_refund(order)
            success_count += 1
        except OrderCancellationError as exc:
            modeladmin.message_user(request, f"Замовлення №{order.id}: {exc}", messages.ERROR)
        except Exception as exc:
            modeladmin.message_user(
                request,
                f"Замовлення №{order.id}: помилка повернення коштів — {exc}",
                messages.ERROR,
            )

    if success_count:
        modeladmin.message_user(
            request,
            f"Оброблено замовлень: {success_count}.",
            messages.SUCCESS,
        )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "status", "is_paid", "refunded_at")
    inlines = [OrderItemInline]
    list_filter = ("status", "payment_method", "created_at", "user")
    readonly_fields = ("created_at", "paid_at", "cancelled_at", "refunded_at")
    actions = [confirm_return_and_refund]
    fieldsets = (
        (None, {
            'fields': (
                'user', 'status', 'is_paid', 'payment_method', 'delivery_method',
            ),
        }),
        ('Покупець', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'address'),
        }),
        ('Оплата', {
            'fields': ('stripe_payment_intent', 'paid_at', 'cancelled_at', 'refunded_at', 'created_at'),
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "book", "quantity", "price")
