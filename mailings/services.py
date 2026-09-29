"""Отправка рассылок (R8-R15).

Один вход для всех способов запуска: кнопка в интерфейсе и команда
manage.py зовут send_mailing(), а не повторяют логику каждая по-своему.
"""

from dataclasses import dataclass

from django.core.mail import send_mail

from mailings.models import Mailing, MailingAttempt


class MailingFinished(Exception):
    """Время рассылки вышло — отправлять нечего."""


@dataclass
class SendResult:
    attempt: MailingAttempt
    sent: int
    failed: int


def send_mailing(mailing):
    """Разослать письмо рассылки всем её получателям.

    Пишет попытку на запуск и по попытке на каждое письмо (решение по Q2).
    Ошибка на одном получателе не прерывает остальных: она попадает
    в «Ответ почтового сервера» своей попытки, и цикл идёт дальше.
    """
    # Статус хранится строкой, поэтому проверяем не его, а время (R7).
    Mailing.objects.filter(pk=mailing.pk).finish_expired()
    mailing.refresh_from_db()
    if mailing.status == Mailing.Status.FINISHED:
        raise MailingFinished('Время рассылки вышло — отправка не выполняется.')

    # Запись о запуске создаётся ДО отправки (R12). Статус пока «Не успешно»:
    # если процесс упадёт на середине, это и будет правдой.
    run = MailingAttempt.objects.create(
        mailing=mailing,
        status=MailingAttempt.Status.FAILURE,
        server_response='Отправка начата.',
    )

    sent = 0
    failed = 0
    for client in mailing.clients.all():
        try:
            send_mail(
                mailing.message.subject,
                mailing.message.body,
                None,  # None -> DEFAULT_FROM_EMAIL
                [client.email],
                fail_silently=False,
            )
        except Exception as error:
            failed += 1
            MailingAttempt.objects.create(
                mailing=mailing,
                client=client,
                parent=run,
                status=MailingAttempt.Status.FAILURE,
                server_response=str(error) or error.__class__.__name__,
            )
        else:
            sent += 1
            MailingAttempt.objects.create(
                mailing=mailing,
                client=client,
                parent=run,
                status=MailingAttempt.Status.SUCCESS,
                server_response='Письмо принято почтовым сервером.',
            )

    run.status = (
        MailingAttempt.Status.SUCCESS
        if sent and not failed
        else MailingAttempt.Status.FAILURE
    )
    run.server_response = f'Отправлено: {sent}, ошибок: {failed}.'
    run.save(update_fields=['status', 'server_response'])

    if sent:
        mailing.mark_started()

    return SendResult(attempt=run, sent=sent, failed=failed)
