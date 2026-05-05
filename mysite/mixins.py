import os
import re

from django.conf import settings


class AutoTemplateNameMixin:
    # -----------------------------------------------------------------------------------------------------------------
    # Section: Context (додає назву сторінки у контекст)
    # -----------------------------------------------------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, 'template_name') and self.template_name:
            if "cart" in self.template_name:
                context["page_title"] = "Мій Кошик"
            elif "checkout" in self.template_name:
                context["page_title"] = "Оплата"
            elif "order_history" in self.template_name:
                context["page_title"] = "Історія замовлень"
        return context

    # -----------------------------------------------------------------------------------------------------------------
    # Section: Template resolution (пошук правильного шаблону)
    # -----------------------------------------------------------------------------------------------------------------
    def get_template_names(self):
        if hasattr(self, 'template_name') and self.template_name:
            return [self.template_name]

        # Назва класу без "View"
        view_type = self.__class__.__name__.replace('View', '')

        # snake_case варіант
        view_type_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', view_type).lower()
        snake_templates = [
            f"orders/{view_type_snake}.html",
            f"mysite/{view_type_snake}.html",
        ]

        # CamelCase варіант
        camel_templates = [
            f"orders/{view_type}.html",
            f"mysite/{view_type}.html",
        ]

        # Перевіряємо, який файл реально існує
        template_dirs = settings.TEMPLATES[0]['DIRS']
        for d in template_dirs:
            for candidate in snake_templates + camel_templates:
                if os.path.exists(os.path.join(d, candidate)):
                    return [candidate]

        # fallback — перший варіант
        return [snake_templates[0]]
