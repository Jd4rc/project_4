from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from mailings.forms import StyleFormMixin
from users.models import User


class RegisterForm(StyleFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data['email']
        # unique в базе регистр учитывает: Ivan@ и ivan@ — два разных пользователя,
        # а письмо и сброс пароля ищут без учёта регистра.
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже есть.')
        return email


class LoginForm(StyleFormMixin, AuthenticationForm):
    pass


class StyledPasswordResetForm(StyleFormMixin, PasswordResetForm):
    pass


class StyledSetPasswordForm(StyleFormMixin, SetPasswordForm):
    pass
