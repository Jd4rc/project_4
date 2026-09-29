from django.conf import settings
from django.db import models
from django.urls import reverse


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
