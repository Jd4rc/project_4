from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Своя модель пользователя.

    Пока это точная копия стандартной: вход и регистрация отложены.
    Заведена сразу, потому что сменить AUTH_USER_MODEL после первой миграции
    нельзя — это снос базы и ручная пересборка миграций.
    """

    class Meta(AbstractUser.Meta):
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'
