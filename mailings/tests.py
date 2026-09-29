from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mailings.models import Client as Recipient
from mailings.models import Mailing, Message


class ClientCrudTests(TestCase):
    """Проверки блока 2 (R1, R2). Recipient — это модель Client, переименована
    при импорте, чтобы не путать её с self.client (тестовым HTTP-клиентом)."""

    def setUp(self):
        self.recipient = Recipient.objects.create(
            full_name='Иван Иванов',
            email='ivan@example.com',
            comment='постоянный покупатель',
        )

    def test_list_shows_client(self):
        response = self.client.get(reverse('mailings:client_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Иванов')

    def test_create_adds_client(self):
        response = self.client.post(
            reverse('mailings:client_create'),
            {'full_name': 'Пётр Петров', 'email': 'petr@example.com', 'comment': ''},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Recipient.objects.filter(email='petr@example.com').exists())

    def test_duplicate_email_rejected(self):
        response = self.client.post(
            reverse('mailings:client_create'),
            {'full_name': 'Двойник', 'email': 'ivan@example.com', 'comment': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['email'])
        self.assertEqual(Recipient.objects.count(), 1)

    def test_update_changes_name(self):
        update_url = reverse('mailings:client_update', args=[self.recipient.pk])
        self.assertEqual(self.client.get(update_url).status_code, 200)
        self.client.post(
            update_url,
            {'full_name': 'Иван Сидоров', 'email': 'ivan@example.com', 'comment': ''},
        )
        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.full_name, 'Иван Сидоров')

    def test_delete_removes_client(self):
        delete_url = reverse('mailings:client_delete', args=[self.recipient.pk])
        self.assertEqual(self.client.get(delete_url).status_code, 200)
        self.client.post(delete_url)
        self.assertEqual(Recipient.objects.count(), 0)


class MessageCrudTests(TestCase):
    """Проверки блока 3 (R3, R4)."""

    def setUp(self):
        self.message = Message.objects.create(
            subject='Скидки недели',
            body='Только до воскресенья.',
        )

    def test_list_shows_message(self):
        response = self.client.get(reverse('mailings:message_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Скидки недели')

    def test_detail_shows_body(self):
        response = self.client.get(reverse('mailings:message_detail', args=[self.message.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Только до воскресенья.')

    def test_create_adds_message(self):
        response = self.client.post(
            reverse('mailings:message_create'),
            {'subject': 'Новинки', 'body': 'Завезли новое.'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Message.objects.filter(subject='Новинки').exists())

    def test_empty_body_rejected(self):
        response = self.client.post(
            reverse('mailings:message_create'),
            {'subject': 'Без текста', 'body': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['body'])
        self.assertEqual(Message.objects.count(), 1)

    def test_update_changes_subject(self):
        update_url = reverse('mailings:message_update', args=[self.message.pk])
        self.assertEqual(self.client.get(update_url).status_code, 200)
        self.client.post(update_url, {'subject': 'Скидки месяца', 'body': 'Текст.'})
        self.message.refresh_from_db()
        self.assertEqual(self.message.subject, 'Скидки месяца')

    def test_delete_removes_message(self):
        delete_url = reverse('mailings:message_delete', args=[self.message.pk])
        self.assertEqual(self.client.get(delete_url).status_code, 200)
        self.client.post(delete_url)
        self.assertEqual(Message.objects.count(), 0)


class MailingTests(TestCase):
    """Проверки блока 4 (R5, R6, R7)."""

    def setUp(self):
        self.message = Message.objects.create(subject='Акция', body='Текст письма.')
        self.recipient = Recipient.objects.create(
            full_name='Иван Иванов', email='ivan@example.com'
        )
        self.now = timezone.now()

    def _mailing(self, start_delta, end_delta, status=Mailing.Status.CREATED):
        mailing = Mailing.objects.create(
            message=self.message,
            first_sent_at=self.now + start_delta,
            finished_at=self.now + end_delta,
            status=status,
        )
        mailing.clients.add(self.recipient)
        return mailing

    def test_create_via_form(self):
        response = self.client.post(
            reverse('mailings:mailing_create'),
            {
                'message': self.message.pk,
                'clients': [self.recipient.pk],
                'first_sent_at': (self.now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
                'finished_at': (self.now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            },
        )
        self.assertEqual(response.status_code, 302)
        mailing = Mailing.objects.get()
        self.assertEqual(mailing.status, Mailing.Status.CREATED)
        self.assertEqual(list(mailing.clients.all()), [self.recipient])

    def test_end_before_start_rejected(self):
        response = self.client.post(
            reverse('mailings:mailing_create'),
            {
                'message': self.message.pk,
                'clients': [self.recipient.pk],
                'first_sent_at': (self.now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
                'finished_at': (self.now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['finished_at'])
        self.assertEqual(Mailing.objects.count(), 0)

    def test_finish_expired_touches_only_past(self):
        expired = self._mailing(timedelta(days=-2), timedelta(days=-1), Mailing.Status.STARTED)
        future = self._mailing(timedelta(hours=1), timedelta(days=1))

        self.assertEqual(Mailing.objects.finish_expired(), 1)

        expired.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(expired.status, Mailing.Status.FINISHED)
        self.assertEqual(future.status, Mailing.Status.CREATED)

    def test_command_finishes_expired(self):
        expired = self._mailing(timedelta(days=-2), timedelta(days=-1))
        out = StringIO()
        call_command('update_mailing_statuses', stdout=out)
        expired.refresh_from_db()
        self.assertEqual(expired.status, Mailing.Status.FINISHED)
        self.assertIn('Завершено рассылок: 1', out.getvalue())

    def test_list_shows_mailing_and_closes_expired(self):
        expired = self._mailing(timedelta(days=-2), timedelta(days=-1), Mailing.Status.STARTED)

        response = self.client.get(reverse('mailings:mailing_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Акция')

        expired.refresh_from_db()
        self.assertEqual(expired.status, Mailing.Status.FINISHED)

    def test_mark_started_skips_finished(self):
        created = self._mailing(timedelta(hours=1), timedelta(days=1))
        finished = self._mailing(timedelta(days=-2), timedelta(days=-1), Mailing.Status.FINISHED)

        created.mark_started()
        finished.mark_started()

        created.refresh_from_db()
        finished.refresh_from_db()
        self.assertEqual(created.status, Mailing.Status.STARTED)
        self.assertEqual(finished.status, Mailing.Status.FINISHED)

    def test_delete_removes_mailing(self):
        mailing = self._mailing(timedelta(hours=1), timedelta(days=1))
        delete_url = reverse('mailings:mailing_delete', args=[mailing.pk])
        self.assertEqual(self.client.get(delete_url).status_code, 200)
        self.client.post(delete_url)
        self.assertEqual(Mailing.objects.count(), 0)
