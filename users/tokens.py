from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """Токен ссылки подтверждения email (R21).

    Свой key_salt — токен сброса пароля здесь не подходит и наоборот.
    email_confirmed в хэше делает ссылку одноразовой: после подтверждения
    флаг стал True, и старая ссылка уже не совпадает. Срок жизни — общий
    PASSWORD_RESET_TIMEOUT (по умолчанию трое суток).
    """

    key_salt = 'users.tokens.EmailConfirmationTokenGenerator'

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{user.email}{user.email_confirmed}{timestamp}'


email_confirmation_token = EmailConfirmationTokenGenerator()
