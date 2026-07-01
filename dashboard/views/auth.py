from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponseNotFound
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import AuthenticationForm
from django.template.context_processors import csrf

from mysite.mixins import AutoTemplateNameMixin
from dashboard.decorators import is_admin_user


# ==========================================================
# Авторизація в dashboard
# ==========================================================

class AdminLoginView(AutoTemplateNameMixin, View):
    def get(self, request):
        # якщо не увійшов
        if not request.user.is_authenticated:
            return HttpResponseNotFound("<h1>404 Not Found</h1>")
        # якщо вже увійшов
        if request.user.is_authenticated:
            # є доступ → dashboard
            if is_admin_user(request.user):
                return redirect('dashboard:home')

            # немає доступу
            messages.error(
                request,
                "У вас немає доступу до адмін-панелі"
            )

            return redirect('mysite:index')

        form = LoginForm()

        return render(
            request,
            self.template_name,
            {
                'form': form
            }
        )

    def post(self, request):

        form = LoginForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is not None:

                # перевірка доступу
                if is_admin_user(user):
                    login(
                        request,
                        user
                    )

                    return redirect(
                        reverse_lazy(
                            'dashboard:home'
                        )
                    )

                messages.error(
                    request,
                    "У вас немає прав доступу до адмін-панелі"
                )

                return redirect(
                    reverse_lazy(
                        'mysite:index'
                    )
                )

            messages.error(
                request,
                "Невірний логін або пароль"
            )

        return render(
            request,
            self.template_name,
            {
                'form': form
            }
        )
