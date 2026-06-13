import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(order, user):
    amount = int(order.get_total_price() * 100)

    return stripe.PaymentIntent.create(
        amount=amount,
        currency='uah',
        metadata={
            'order_id': str(order.id),
            'user_id': str(user.id),
        },
    )


def save_payment_intent(order, user):
    intent = create_payment_intent(order, user)
    order.stripe_payment_intent = intent.id
    order.save(update_fields=['stripe_payment_intent'])
    return intent


def verify_webhook(payload, sig_header):
    try:
        return stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (stripe.error.SignatureVerificationError, ValueError):
        return None


def payment_intent_succeeded(order):
    if not order.stripe_payment_intent:
        return False

    intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent)
    return intent.status == 'succeeded'


def refund_payment(order):
    if not order.stripe_payment_intent:
        raise ValueError("Payment Intent not found")

    return stripe.Refund.create(
        payment_intent=order.stripe_payment_intent,
        reason='requested_by_customer',
    )


def handle_payment_intent_event(event):
    intent = event['data']['object']
    order_id = intent.get('metadata', {}).get('order_id')

    if not order_id:
        return None

    from orders.models import Order
    from orders.services.order_service import mark_order_as_paid

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return None

    if event['type'] == 'payment_intent.succeeded':
        mark_order_as_paid(order)
    elif event['type'] == 'payment_intent.payment_failed':
        order.status = 'cancelled'
        order.save(update_fields=['status'])

    return order
