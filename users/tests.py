import re

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from users.models import User

PASSWORD = 'Sl0zhnyi-parol-42'


def link_from(message):
    """Ссылка из письма — без хоста, чтобы отдать её тестовому клиенту."""
    url = re.search(r'https?://[^/\s]+(/\S+)', message.body)
    assert url, f'в письме нет ссылки:\n{message.body}'
    return url.group(1)


class RegistrationTests(TestCase):
    """Регистрация с подтверждением email (R20, R21)."""

    def register(self, email='ivan@example.com'):
        return self.client.post(reverse('users:register'), {
            'email': email,
            'password1': PASSWORD,
            'password2': PASSWORD,
        })

    def login(self, email='ivan@example.com', password=PASSWORD):
        return self.client.post(reverse('users:login'), {
            'username': email,
            'password': password,
        })

    def test_register_creates_inactive_user_and_sends_link(self):
        response = self.register()

        self.assertRedirects(response, reverse('users:login'))
        user = User.objects.get(email='ivan@example.com')
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_confirmed)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ivan@example.com'])
        self.assertIn('/users/confirm/', mail.outbox[0].body)

    def test_cannot_login_before_confirmation(self):
        self.register()

        self.login()

        self.assertNotIn('_auth_user_id', self.client.session)

    def test_confirmation_link_activates_and_allows_login(self):
        self.register()

        response = self.client.get(link_from(mail.outbox[0]))

        self.assertRedirects(response, reverse('users:login'))
        user = User.objects.get(email='ivan@example.com')
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_confirmed)
        self.assertRedirects(self.login(), reverse('mailings:home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_confirmation_link_works_once(self):
        """Старая ссылка не должна снимать блокировку (Q11): блокировка —
        это тот же is_active = False, что и до подтверждения."""
        self.register()
        link = link_from(mail.outbox[0])
        self.client.get(link)
        User.objects.filter(email='ivan@example.com').update(is_active=False)

        self.client.get(link)

        self.assertFalse(User.objects.get(email='ivan@example.com').is_active)

    def test_broken_link_does_not_activate(self):
        self.register()
        link = link_from(mail.outbox[0])
        broken = link.rstrip('/')[:-1] + '0/'

        self.client.get(broken)
        self.client.get(reverse('users:confirm_email', args=['bm90LWFuLWlk', 'x-y']))

        self.assertFalse(User.objects.get(email='ivan@example.com').is_active)

    def test_email_is_unique_ignoring_case(self):
        self.register('ivan@example.com')

        response = self.register('Ivan@Example.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_failed_email_does_not_leave_user(self):
        """Письмо не ушло — пользователя нет, иначе email занят навсегда."""
        with self.settings(MAILERS={'default': {
            'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
            'OPTIONS': {'host': '127.0.0.1', 'port': 1, 'timeout': 1},
        }}):
            with self.assertRaises(OSError):
                self.register()

        self.assertFalse(User.objects.exists())


class LoginLogoutTests(TestCase):
    """Вход и выход (R22, R23)."""

    def setUp(self):
        self.user = User.objects.create_user(
            'ivan@example.com', PASSWORD, is_active=True, email_confirmed=True,
        )

    def test_login_by_email(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'ivan@example.com',
            'password': PASSWORD,
        })

        self.assertRedirects(response, reverse('mailings:home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_wrong_password_is_rejected(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'ivan@example.com',
            'password': 'не тот',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('users:logout'))

        self.assertRedirects(response, reverse('mailings:home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_nav_shows_login_for_guest_and_email_for_user(self):
        guest = self.client.get(reverse('mailings:home'))
        self.assertContains(guest, reverse('users:login'))
        self.assertNotContains(guest, 'ivan@example.com')

        self.client.force_login(self.user)
        logged = self.client.get(reverse('mailings:home'))
        self.assertContains(logged, 'ivan@example.com')
        self.assertContains(logged, reverse('users:logout'))

    def test_superuser_needs_no_confirmation(self):
        admin = User.objects.create_superuser('admin@example.com', PASSWORD)

        self.assertTrue(admin.email_confirmed)
        self.assertTrue(admin.is_active)


class PasswordResetTests(TestCase):
    """Восстановление пароля (R24)."""

    def setUp(self):
        self.user = User.objects.create_user(
            'ivan@example.com', PASSWORD, is_active=True, email_confirmed=True,
        )

    def test_reset_sets_new_password(self):
        response = self.client.post(reverse('users:password_reset'), {'email': 'ivan@example.com'})
        self.assertRedirects(response, reverse('users:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

        # Первый переход меняет токен в адресе на set-password и прячет его в сессию.
        form_page = self.client.get(link_from(mail.outbox[0]), follow=True)
        self.assertTrue(form_page.context['validlink'])
        response = self.client.post(form_page.request['PATH_INFO'], {
            'new_password1': 'Novyi-parol-2026',
            'new_password2': 'Novyi-parol-2026',
        })

        self.assertRedirects(response, reverse('users:password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Novyi-parol-2026'))

    def test_unknown_email_gets_same_answer_and_no_letter(self):
        response = self.client.post(reverse('users:password_reset'), {'email': 'nobody@example.com'})

        self.assertRedirects(response, reverse('users:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_unconfirmed_user_gets_no_reset_letter(self):
        """Сброс пароля не должен обходить подтверждение email."""
        self.user.is_active = False
        self.user.save()

        self.client.post(reverse('users:password_reset'), {'email': 'ivan@example.com'})

        self.assertEqual(len(mail.outbox), 0)
