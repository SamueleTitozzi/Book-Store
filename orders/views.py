import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, TemplateView

from mysite.forms import CheckoutForm
from mysite.mixins import AutoTemplateNameMixin
from mysite.models import Book
from orders.models import Order, OrderItem
from orders.services.order_service import (
    InsufficientStockError,
    OrderCancellationError,
    add_book_to_order,
    cancel_order,
    clear_pending_order,
    decrease_quantity,
    get_or_create_order,
    get_pending_order,
    get_unpaid_order_for_user,
    increase_quantity,
    mark_order_as_paid,
    process_cod_order,
    update_order_from_checkout,
)
from orders.services.payment_service import (
    handle_payment_intent_event,
    payment_intent_succeeded,
    save_payment_intent,
    verify_webhook,
)

logger = logging.getLogger(__name__)


def _checkout_context(form, *, order_confirmed=False, order=None):
    context = {
        'form': form,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'order_confirmed': order_confirmed,
    }
    if order is not None:
        context['order'] = order
    return context


class AddToCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        order = get_or_create_order(request.user)
        try:
            add_book_to_order(order, kwargs.get('pk'))
        except InsufficientStockError as exc:
            messages.error(request, str(exc))
        except Book.DoesNotExist:
            messages.error(request, "Книгу не знайдено.")
        return redirect('orders:cart')


class CartView(AutoTemplateNameMixin, LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_pending_order(self.request.user)
        context['order'] = order
        context['items'] = order.items.select_related('book') if order else []
        return context


class ResetCartView(LoginRequiredMixin, View):
    def post(self, request):
        clear_pending_order(request.user)
        return redirect('orders:cart')


class DecreaseQuantityView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        order_item = get_object_or_404(
            OrderItem,
            pk=kwargs.get('pk'),
            order__user=request.user,
            order__status='pending',
        )
        decrease_quantity(order_item)
        return redirect('orders:cart')


class AddQuantityView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        order_item = get_object_or_404(
            OrderItem,
            pk=kwargs.get('pk'),
            order__user=request.user,
            order__status='pending',
        )
        try:
            increase_quantity(order_item)
        except InsufficientStockError as exc:
            messages.error(request, str(exc))
        return redirect('orders:cart')


class OrderHistoryView(AutoTemplateNameMixin, LoginRequiredMixin, ListView):
    model = Order
    context_object_name = "orders"
    paginate_by = 6

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .exclude(status="pending")
            .order_by("-created_at", "-id")
        )


class OrderDetailView(AutoTemplateNameMixin, LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(Order, pk=self.kwargs['pk'], user=self.request.user)
        context['order'] = order
        context['items'] = order.items.select_related('book')
        return context


class OrderConfirmationView(LoginRequiredMixin, TemplateView):
    template_name = "orders/confirmation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = get_object_or_404(
            Order,
            pk=self.kwargs['pk'],
            user=self.request.user,
        )
        return context


class CancelOrderView(AutoTemplateNameMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)

        try:
            result = cancel_order(order)

            if result == 'return_pending':
                messages.success(
                    request,
                    "Заявку на скасування прийнято. Повернення коштів відбудеться "
                    "після отримання товару на склад.",
                )
            elif order.is_refunded:
                messages.success(
                    request,
                    "Замовлення скасовано. Кошти повернено на вашу картку.",
                )
            else:
                messages.success(request, "Замовлення успішно скасовано.")
        except OrderCancellationError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            logger.exception("Order cancellation failed for order %s", pk)
            messages.error(request, f"Помилка скасування: {exc}")

        return redirect("orders:order_history")


class CheckOrderStatusView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        return JsonResponse({'status': order.status, 'is_paid': order.is_paid})


class CreatePaymentView(LoginRequiredMixin, View):
    def post(self, request):
        order = get_unpaid_order_for_user(request.user)

        if not order or not order.items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        intent = save_payment_intent(order, request.user)

        return JsonResponse({
            'client_secret': intent.client_secret,
            'order_id': order.pk,
        })


class ConfirmPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user, status='pending')

        if not payment_intent_succeeded(order):
            return JsonResponse({'error': 'Payment not confirmed'}, status=400)

        mark_order_as_paid(order)
        return JsonResponse({'success': True})


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'orders/checkout.html', _checkout_context(CheckoutForm()))

    def post(self, request):
        form = CheckoutForm(request.POST)

        if not form.is_valid():
            return render(request, 'orders/checkout.html', _checkout_context(form))

        order = get_unpaid_order_for_user(request.user)

        if not order or not order.items.exists():
            form.add_error(None, "Кошик пустий")
            return render(request, 'orders/checkout.html', _checkout_context(form))

        update_order_from_checkout(order, form.cleaned_data)

        if order.payment_method == 'cod':
            process_cod_order(order)
            return redirect('orders:confirmation', pk=order.pk)

        if order.payment_method == 'stripe':
            return render(
                request,
                'orders/checkout.html',
                _checkout_context(form, order_confirmed=True, order=order),
            )

        return redirect('orders:cart')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request):
        event = verify_webhook(request.body, request.META.get('HTTP_STRIPE_SIGNATURE'))
        if not event:
            return HttpResponse(status=400)

        handle_payment_intent_event(event)
        return HttpResponse(status=200)
