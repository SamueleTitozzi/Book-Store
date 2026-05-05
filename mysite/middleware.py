from orders.models import Order

class MyMiddleware:
    def __init__(self, get_response):
        # зберігаємо функцію, яка викликає наступний middleware або view
        self.get_response = get_response

    def __call__(self, request):
        # тут можна додати свою логіку для кожного запиту

        request.order = None  # створюємо атрибут order у request

        if request.user.is_authenticated:
            # якщо користувач залогінений, шукаємо його замовлення зі статусом 'pending'
            request.order = Order.objects.filter(
                user=request.user,
                status='pending'
            ).first()

        # response = self.get_response(request)  - передаємо запит далі
        # тут можна додати свою логіку для кожної відповіді

        response = self.get_response(request)  # обов’язково передаємо запит далі

        return response
