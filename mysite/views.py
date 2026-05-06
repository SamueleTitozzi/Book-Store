from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.views import LogoutView
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.templatetags.static import static
from django.views import View
from django.views.generic import ListView, DetailView

from .forms import LoginForm, RegisterForm
from .mixins import AutoTemplateNameMixin
from .models import Category, Book


# section HomePage -----------------------------------------------------------------------------------------------------
class BookListView(ListView):
    model = Book
    context_object_name = 'books'
    template_name = 'mysite/base.html'


class HomeView(AutoTemplateNameMixin, ListView):
    model = Book
    context_object_name = 'books'

    def get_queryset(self):
        return Book.objects.order_by('-id')[:8]


# ----------------------------------------------------------------------------------------------------------------------

# Section User ------------------------------------------------------------------------------------------------------
class UserLoginView(AutoTemplateNameMixin, View):

    def get(self, request):
        form = LoginForm()
        return render(request, self.get_template_names()[0], {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('mysite:index')
            else:
                messages.error(request, 'Невірний логін або пароль')
        return render(request, self.get_template_names()[0], {'form': form})


class RegisterView(AutoTemplateNameMixin, View):

    def get(self, request):
        form = RegisterForm()
        return render(request, self.get_template_names()[0], {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            email = form.cleaned_data['email']

            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name,
                                            last_name=last_name)

            messages.success(request, 'Реєстрація пройшла успішно!')
            if user is not None:
                login(request, user)
                return redirect('mysite:index')
            else:
                messages.error(request, 'Помилка входу після реєстрації')
        return render(request, self.get_template_names()[0], {'form': form})


class UserLogoutView(LogoutView):
    next_page = 'mysite:index'


# ---------------------------------------------------------------------------------------------------------------------

# section Category -----------------------------------------------------------------------------------------------------
class CategoryListView(AutoTemplateNameMixin, ListView):
    model = Category
    context_object_name = 'categories'


class SingleCategoryView(AutoTemplateNameMixin, ListView):
    model = Book
    context_object_name = 'books'

    def get_queryset(self):
        return Book.objects.filter(category__pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_category = get_object_or_404(Category, pk=self.kwargs['pk'])
        context['category'] = current_category

        # логіка для наступної категорії
        next_category = Category.objects.filter(pk__gt=current_category.pk).order_by('pk').first()

        if not next_category:
            next_category = Category.objects.order_by('pk').first()

        context['next_category'] = next_category
        return context


class SingleBookInfoView(AutoTemplateNameMixin, DetailView):
    model = Book
    context_object_name = 'book'


# ---------------------------------------------------------------------------------------------------------------------

# section Search ------------------------------------------------------------------------------------------------------
class SearchView(AutoTemplateNameMixin, ListView):
    model = Book
    context_object_name = 'books'

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()

        if query:
            return Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query))
        return Book.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class LiveSearchView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'results': []})

        books = Book.objects.filter(title__icontains=query).only('id', 'title', 'image_path')[:5]

        results = []

        for book in books:
            results.append({
                'title': book.title,
                'image': static(f'{book.image_path}') if book.image_path else '',
                'id': book.pk,
            })

        return JsonResponse({'results': results})

# ---------------------------------------------------------------------------------------------------------------------
