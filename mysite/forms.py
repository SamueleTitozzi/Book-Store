from django import forms
from django.contrib.auth.models import User

from orders.models import Order


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, label="Ім'я")
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')
    email = forms.CharField(widget=forms.EmailInput, label='E-mail')


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="Ім'я")
    last_name = forms.CharField(max_length=150, label='Прізвище')
    username = forms.CharField(max_length=150, label="Username")
    email = forms.CharField(widget=forms.EmailInput, label='E-mail')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Пароль')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Повторіть пароль')

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        email = cleaned_data.get("email")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Паролі не співпадають")

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Користувач з таким ім'ям вже існує")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Користувач з таким email вже існує")

        return cleaned_data

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'delivery_method',
            'payment_method',
        ]