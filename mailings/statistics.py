"""Статистика (R16-R19).

Всё считается агрегатами в базе, а не циклами по queryset. Перед подсчётом
закрываются просроченные рассылки: статус хранится строкой и между запусками
фоновой задачи врёт (решение по Q3), а «активных» без этого посчитает лишние.
"""

from django.db.models import Count, Q

from mailings.models import Client, Mailing, MailingAttempt


def home_stats():
    """Три цифры главной страницы (R17, R18, R19)."""
    Mailing.objects.finish_expired()

    counts = Mailing.objects.aggregate(
        total=Count('pk'),
        active=Count('pk', filter=Q(status=Mailing.Status.STARTED)),
    )
    # Допущение по Q4 (не подтверждено куратором): «уникальный получатель» —
    # клиент, состоящий хотя бы в одной рассылке; в трёх рассылках он один.
    # Если окажется «все клиенты в базе» — здесь заменить на Client.objects.count().
    counts['recipients'] = Client.objects.filter(mailings__isnull=False).distinct().count()
    return counts


def attempt_totals():
    """Успешные / неуспешные / всего по всем письмам (R16).

    Считаем только записи о письмах: запись о запуске — это не отправка,
    и с ней одна рассылка на пятерых давала бы шесть попыток вместо пяти.
    """
    return MailingAttempt.objects.letters().aggregate(
        total=Count('pk'),
        success=Count('pk', filter=Q(status=MailingAttempt.Status.SUCCESS)),
        failure=Count('pk', filter=Q(status=MailingAttempt.Status.FAILURE)),
    )


def mailing_report():
    """Те же три числа по каждой рассылке (R16)."""
    Mailing.objects.finish_expired()

    letter = Q(attempts__client__isnull=False)
    return Mailing.objects.select_related('message').annotate(
        letters_total=Count('attempts', filter=letter),
        letters_success=Count(
            'attempts', filter=letter & Q(attempts__status=MailingAttempt.Status.SUCCESS)
        ),
        letters_failure=Count(
            'attempts', filter=letter & Q(attempts__status=MailingAttempt.Status.FAILURE)
        ),
    )
