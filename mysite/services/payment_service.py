import stripe
from django.conf import settings


# ---------------------------------------------------------------------------------------------------------------------
# Section: Payment creation (створення платежу у Stripe)
# ---------------------------------------------------------------------------------------------------------------------
def create_payment_intent(order, user):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    amount = int(order.get_total_price() * 100)

    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency='uah',
        metadata={
            'order_id': str(order.id),  # 🔥 важливо: str
            'user_id': str(user.id)
        }
    )

    return intent


def create_payment_for_order(order, user):
    intent = create_payment_intent(order, user)

    order.stripe_payment_intent = intent.id
    order.save(update_fields=['stripe_payment_intent'])

    return intent


# ---------------------------------------------------------------------------------------------------------------------
# Section: Webhook verification (перевірка підпису Stripe)
# ---------------------------------------------------------------------------------------------------------------------
def verify_webhook(payload, sig_header):
    """Перевіряє підпис Stripe webhook."""
    try:
        return stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return None


# ---------------------------------------------------------------------------------------------------------------------
# Section: Refund (повернення коштів)
# ---------------------------------------------------------------------------------------------------------------------

def refund_payment(order):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not order.stripe_payment_intent:
        raise ValueError("Payment Intent not found")

    refund = stripe.Refund.create(
        payment_intent=order.stripe_payment_intent,
        reason='requested_by_customer'
    )

    return refund
# ---------------------------------------------------------------------------------------------------------------------
