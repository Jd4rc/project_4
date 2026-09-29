from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Client(models.Model):
    """Получатель рассылки (R1)."""

    email = models.EmailField(unique=True, verbose_name='email')
    full_name = models.CharField(max_length=255, verbose_name='Ф. И. О.')
    comment = models.TextField(blank=True, verbose_name='комментарий')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='clients',
        verbose_name='владелец',
    )

    class Meta:
        verbose_name = 'получатель'
        verbose_name_plural = 'получатели'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} <{self.email}>'

    def get_absolute_url(self):
        return reverse('mailings:client_detail', args=[self.pk])


class Message(models.Model):
    """Письмо, которое уходит в рассылке (R3)."""

    subject = models.CharField(max_length=255, verbose_name='тема письма')
    body = models.TextField(verbose_name='тело письма')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages',
        verbose_name='владелец',
    )

    class Meta:
        verbose_name = 'сообщение'
        verbose_name_plural = 'сообщения'
        ordering = ['subject']

    def __str__(self):
        return self.subject

    def get_absolute_url(self):
        return reverse('mailings:message_detail', args=[self.pk])


class MailingQuerySet(models.QuerySet):
    def finish_expired(self):
        """Перевести в «Завершена» всё, у чего время окончания прошло (R7).

        Один UPDATE в базе, а не цикл с save(): статус меняется у множества
        строк сразу, и промежуточные значения никому не нужны.
        Возвращает количество затронутых рассылок.
        """
        finished = self.model.Status.FINISHED
        return (
            self.exclude(status=finished)
            .filter(finished_at__lt=timezone.now())
            .update(status=finished)
        )


class Mailing(models.Model):
    """Рассылка (R5). Статусы и правила перехода — R7."""

    class Status(models.TextChoices):
        CREATED = 'created', 'Создана'
        STARTED = 'started', 'Запущена'
        FINISHED = 'finished', 'Завершена'

    first_sent_at = models.DateTimeField(verbose_name='дата и время первой отправки')
    finished_at = models.DateTimeField(verbose_name='дата и время окончания отправки')
    status = models.CharField(
        max_length=10,
        choices=Status,
        default=Status.CREATED,
        verbose_name='статус',
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='mailings',
        verbose_name='сообщение',
    )
    clients = models.ManyToManyField(
        Client,
        related_name='mailings',
        verbose_name='получатели',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mailings',
        verbose_name='владелец',
    )

    objects = MailingQuerySet.as_manager()

    class Meta:
        verbose_name = 'рассылка'
        verbose_name_plural = 'рассылки'
        ordering = ['-first_sent_at']

    def __str__(self):
        return f'{self.message.subject} ({self.get_status_display()})'

    def get_absolute_url(self):
        return reverse('mailings:mailing_detail', args=[self.pk])

    def mark_started(self):
        """После первой удачной отправки рассылка становится «Запущена» (R7).

        Зовётся из отправки (блок 5). Завершённую не трогаем: её время уже вышло.
        """
        if self.status == self.Status.CREATED:
            self.status = self.Status.STARTED
            self.save(update_fields=['status'])


class MailingAttemptQuerySet(models.QuerySet):
    def letters(self):
        """Только записи о конкретных письмах, без записей о запусках.

        Статистика (R16, R18) считается по ним: иначе одна отправка пяти
        получателям даёт шесть попыток вместо пяти.
        """
        return self.filter(client__isnull=False)


class MailingAttempt(models.Model):
    """Попытка рассылки (R11) в две ступени — решение по Q2 в SPEC.md.

    Запись о запуске: client пуст, parent пуст, в ответе сервера — сводка.
    Запись о письме: client заполнен, parent ссылается на запуск.
    """

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Успешно'
        FAILURE = 'failure', 'Не успешно'

    attempted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='дата и время попытки',
    )
    status = models.CharField(max_length=10, choices=Status, verbose_name='статус')
    server_response = models.TextField(blank=True, verbose_name='ответ почтового сервера')
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name='рассылка',
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attempts',
        verbose_name='получатель',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='letters',
        verbose_name='попытка запуска',
    )

    objects = MailingAttemptQuerySet.as_manager()

    class Meta:
        verbose_name = 'попытка рассылки'
        verbose_name_plural = 'попытки рассылок'
        ordering = ['-attempted_at', '-pk']

    def __str__(self):
        target = self.client.email if self.client else 'запуск'
        return f'{target}: {self.get_status_display()}'

    @property
    def is_run(self):
        return self.client_id is None
