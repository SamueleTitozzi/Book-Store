import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView

from mysite.forms import CheckoutForm
from mysite.mixins import AutoTemplateNameMixin

logger = logging.getLogger(__name__)

from mysite.services.order_service import (
    get_or_create_order,
    add_book_to_order,
    decrease_quantity,
    mark_order_as_paid, get_unpaid_order_for_user,
    update_order_from_checkout, process_cod_order,
)

from mysite.services.payment_service import (
    create_payment_intent,
    verify_webhook, refund_payment
)

from orders.models import Order, OrderItem


# ----------------------------------------------------------------------------------------------------------------------
# Section: Basket (Cart management) — взаємодія з order_service
# ----------------------------------------------------------------------------------------------------------------------
class AddToCartView(LoginRequiredMixin, View):  # (order_service: get_or_create_order, add_book_to_order)
    def post(self, request, *args, **kwargs):
        order = get_or_create_order(request.user)
        add_book_to_order(order, kwargs.get('pk'))
        return redirect('orders:cart')


class CartView(AutoTemplateNameMixin, LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # краще брати останнє замовлення
        order = Order.objects.filter(user=self.request.user, status='pending').last()
        context['order'] = order
        context['items'] = order.items.all() if order else []
        return context


class ResetCartView(LoginRequiredMixin, View):  # (order_service: тільки видалення Order)
    def post(self, request):
        order = Order.objects.filter(user=request.user, status='pending').first()
        if order:
            order.delete()
        return redirect('orders:cart')


class DecreaseQuantityView(LoginRequiredMixin, View):  # (order_service: decrease_quantity)
    def post(self, request, *args, **kwargs):
        item_id = kwargs.get('pk')
        order_item = get_object_or_404(OrderItem, pk=item_id, order__user=request.user, order__status='pending')
        decrease_quantity(order_item)
        return redirect('orders:cart')


class AddQuantityView(LoginRequiredMixin, View):  # (order_service: тільки оновлення OrderItem)
    def post(self, request, *args, **kwargs):
        item_id = kwargs.get('pk')
        order_item = get_object_or_404(OrderItem, pk=item_id, order__user=request.user, order__status='pending')
        order_item.quantity += 1
        order_item.save()
        return redirect('orders:cart')


class OrderHistoryView(AutoTemplateNameMixin, LoginRequiredMixin, ListView):
    model = Order
    context_object_name = "orders"
    paginate_by = 6

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(status="pending").order_by("-id")


class OrderDetailView(AutoTemplateNameMixin, LoginRequiredMixin, TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        order = get_object_or_404(
            Order,
            pk=self.kwargs['pk'],
            user=self.request.user
        )

        context['order'] = order
        context['items'] = order.items.all()

        return context


class OrderConfirmationView(LoginRequiredMixin, TemplateView):
    template_name = "orders/confirmation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(Order, pk=self.kwargs['pk'], user=self.request.user)
        context['order'] = order
        return context


class CancelOrderView(AutoTemplateNameMixin, LoginRequiredMixin, View): # (order_service: )

    def post(self, request, pk):

        order = get_object_or_404(
            Order,
            pk=pk,
            user=request.user
        )

        if not order.can_be_cancelled:
            messages.error(
                request,
                "Замовлення вже не можна скасувати."
            )
            return redirect("orders:order_history")

        try:

            if order.is_paid:

                refund_payment(order)

                order.status = 'refunded'

            else:

                order.status = 'cancelled'

            order.save(update_fields=['status'])

            messages.success(
                request,
                "Замовлення успішно скасовано."
            )

        except Exception as e:

            messages.error(
                request,
                f"Помилка повернення коштів: {str(e)}"
            )
        return redirect("orders:order_history")


@method_decorator(login_required, name='dispatch')
class CheckOrderStatusView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)

        return JsonResponse({
            'status': order.status,
            'is_paid': order.is_paid
        })


# ----------------------------------------------------------------------------------------------------------------------
# Section: Payment (Stripe integration) — взаємодія з payment_service + order_service
# ----------------------------------------------------------------------------------------------------------------------
# (payment_service: create_payment_intent, order_service: get_unpaid_order_for_user)
@method_decorator(csrf_exempt, name="dispatch")
class CreatePaymentView(LoginRequiredMixin, View):
    def post(self, request):
        order = get_unpaid_order_for_user(request.user)

        if not order or not order.items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        intent = create_payment_intent(order, request.user)

        order.stripe_payment_intent = intent.id
        order.save(update_fields=['stripe_payment_intent'])

        return JsonResponse({
            'client_secret': intent.client_secret,
            'order_id': order.pk
        })


class ConfirmPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, user=request.user)

            mark_order_as_paid(order)

            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)


class CheckoutView(LoginRequiredMixin, View):  # (payment_service: тільки передача ключа у шаблон)
    def get(self, request):
        form = CheckoutForm()

        return render(request, 'orders/checkout.html', {
            'form': form,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
            'order_confirmed': False
        })

    def post(self, request):
        form = CheckoutForm(request.POST)

        if not form.is_valid():
            return render(request, 'orders/checkout.html', {
                'form': form,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
                'order_confirmed': False
            })

        order = get_unpaid_order_for_user(request.user)

        if not order or not order.items.exists():
            form.add_error(None, "Кошик пустий")
            return render(request, 'orders/checkout.html', {
                'form': form,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
                'order_confirmed': False
            })

        # 🔥 зберігаємо дані
        update_order_from_checkout(order, form.cleaned_data)

        # =========================
        # 💰 НАЛОЖЕНИЙ ПЛАТІЖ
        # =========================
        if order.payment_method == 'cod':
            process_cod_order(order)
            return redirect('orders:confirmation', pk=order.pk)

        # =========================
        # 💳 STRIPE
        # =========================
        if order.payment_method == 'stripe':
            return render(request, 'orders/checkout.html', {
                'form': form,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
                'order_confirmed': True,  # 🔥 КЛЮЧ
                'order': order
            })

        return redirect('orders:cart')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        event = verify_webhook(payload, sig_header)
        if not event:
            return HttpResponse(status=400)

        # 🔥 беремо PaymentIntent
        intent = event['data']['object']

        # 🔥 дістаємо order_id
        order_id = intent.get('metadata', {}).get('order_id')

        if not order_id:
            return HttpResponse(status=200)

        try:
            order = Order.objects.get(id=order_id)

            # ✅ УСПІШНА ОПЛАТА
            if event['type'] == 'payment_intent.succeeded':

                if not order.is_paid:
                    order.is_paid = True
                    order.status = 'processing'
                    order.paid_at = timezone.now()
                    order.save(update_fields=['is_paid', 'status', 'paid_at'])

            # ❌ НЕВДАЛА ОПЛАТА
            elif event['type'] == 'payment_intent.payment_failed':

                order.status = 'cancelled'
                order.save(update_fields=['status'])

        except Order.DoesNotExist:
            pass

        return HttpResponse(status=200)

# ----------------------------------------------------------------------------------------------------------------------
