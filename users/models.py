from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Менеджер без username: стандартный UserManager требует его в create_user."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Нужен email')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # Суперпользователя заводят из консоли, письмо ему не шлётся.
        extra_fields.setdefault('email_confirmed', True)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('У суперпользователя is_staff и is_superuser должны быть True')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Пользователь сервиса. Входит по email, логина нет (решение по Q8).

    Заведена до первой миграции, потому что сменить AUTH_USER_MODEL потом
    нельзя — это снос базы и ручная пересборка миграций.
    """

    username = None
    email = models.EmailField('email', unique=True)
    # Отдельно от is_active: is_active потом снимет и блокировка (блок 9).
    # Флаг входит в хэш токена подтверждения, поэтому ссылка из письма
    # срабатывает один раз и не снимает блокировку.
    email_confirmed = models.BooleanField('email подтверждён', default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'

    def __str__(self):
        return self.email
