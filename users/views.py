from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView

from users.forms import (
    LoginForm,
    RegisterForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from users.models import User
from users.tokens import email_confirmation_token


class RegisterView(CreateView):
    """Регистрация (R20): пользователь неактивен, пока не перейдёт по ссылке (R21)."""

    form_class = RegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        # Письмо не ушло — пользователя тоже нет: иначе email занят,
        # а подтвердить его нечем, и зарегистрироваться заново нельзя.
        with transaction.atomic():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            self._send_confirmation(user)
        self.object = user
        messages.info(
            self.request,
            f'Письмо со ссылкой отправлено на {user.email}. Перейдите по ней, чтобы войти.',
        )
        return redirect(self.get_success_url())

    def _send_confirmation(self, user):
        path = reverse('users:confirm_email', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': email_confirmation_token.make_token(user),
        })
        body = render_to_string('users/emails/confirm_email.txt', {
            'user': user,
            'link': self.request.build_absolute_uri(path),
        })
        send_mail('Подтверждение регистрации', body, None, [user.email])


class ConfirmEmailView(View):
    """Переход по ссылке из письма: активирует пользователя один раз (R21)."""

    def get(self, request, uidb64, token):
        try:
            pk = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=pk)
        except (ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not email_confirmation_token.check_token(user, token):
            messages.error(request, 'Ссылка недействительна или устарела.')
            return redirect('users:login')

        user.email_confirmed = True
        user.is_active = True
        user.save(update_fields=['email_confirmed', 'is_active'])
        messages.success(request, 'Email подтверждён, можно входить.')
        return redirect('users:login')


class LoginView(auth_views.LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'


class PasswordResetView(auth_views.PasswordResetView):
    """Восстановление пароля (R24). Шаблоны и адреса свои: встроенные ссылаются
    на маршруты без namespace и на странице упали бы с NoReverseMatch."""

    form_class = StyledPasswordResetForm
    template_name = 'users/password_reset_form.html'
    email_template_name = 'users/emails/password_reset_email.txt'
    subject_template_name = 'users/emails/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = StyledSetPasswordForm
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'
