from datetime import timedelta
from io import StringIO
from smtplib import SMTPException
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mailings.models import Client as Recipient
from mailings.models import Mailing, MailingAttempt, Message
from mailings.services import MailingFinished, send_mailing
from mailings.statistics import attempt_totals, home_stats, mailing_report


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


class SendMailingTests(TestCase):
    """Проверки блока 5 (R8-R15). Почта в тестах — locmem, письма в mail.outbox."""

    def setUp(self):
        self.message = Message.objects.create(subject='Акция', body='Текст письма.')
        self.first = Recipient.objects.create(full_name='Иван', email='ivan@example.com')
        self.second = Recipient.objects.create(full_name='Пётр', email='petr@example.com')
        self.now = timezone.now()
        self.mailing = Mailing.objects.create(
            message=self.message,
            first_sent_at=self.now - timedelta(hours=1),
            finished_at=self.now + timedelta(days=1),
        )
        self.mailing.clients.set([self.first, self.second])

    def test_success_writes_run_and_letters(self):
        result = send_mailing(self.mailing)

        self.assertEqual((result.sent, result.failed), (2, 0))
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(MailingAttempt.objects.count(), 3)  # запуск + два письма
        self.assertEqual(MailingAttempt.objects.letters().count(), 2)

        result.attempt.refresh_from_db()
        self.assertEqual(result.attempt.status, MailingAttempt.Status.SUCCESS)
        self.assertIn('Отправлено: 2, ошибок: 0.', result.attempt.server_response)

        self.mailing.refresh_from_db()
        self.assertEqual(self.mailing.status, Mailing.Status.STARTED)

    def test_failure_does_not_stop_the_rest(self):
        with patch(
            'mailings.services.send_mail',
            side_effect=[SMTPException('сервер недоступен'), None],
        ):
            result = send_mailing(self.mailing)

        self.assertEqual((result.sent, result.failed), (1, 1))

        failed = MailingAttempt.objects.letters().get(status=MailingAttempt.Status.FAILURE)
        self.assertIn('сервер недоступен', failed.server_response)

        result.attempt.refresh_from_db()
        self.assertEqual(result.attempt.status, MailingAttempt.Status.FAILURE)
        self.assertIn('Отправлено: 1, ошибок: 1.', result.attempt.server_response)

    def test_total_failure_keeps_status_created(self):
        with patch('mailings.services.send_mail', side_effect=SMTPException('нет связи')):
            result = send_mailing(self.mailing)

        self.assertEqual((result.sent, result.failed), (0, 2))
        self.mailing.refresh_from_db()
        self.assertEqual(self.mailing.status, Mailing.Status.CREATED)

    def test_finished_mailing_is_not_sent(self):
        expired = Mailing.objects.create(
            message=self.message,
            first_sent_at=self.now - timedelta(days=2),
            finished_at=self.now - timedelta(days=1),
        )
        expired.clients.add(self.first)

        with self.assertRaises(MailingFinished):
            send_mailing(expired)

        self.assertEqual(MailingAttempt.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_view_posts_and_reports(self):
        response = self.client.post(
            reverse('mailings:mailing_send', args=[self.mailing.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Отправлено писем: 2')
        self.assertEqual(len(mail.outbox), 2)

    def test_command_sends_one_mailing(self):
        out = StringIO()
        call_command('send_mailing', self.mailing.pk, stdout=out)

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('отправлено: 2, ошибок: 0', out.getvalue())

    def test_command_without_id_skips_future_mailings(self):
        future = Mailing.objects.create(
            message=self.message,
            first_sent_at=self.now + timedelta(days=1),
            finished_at=self.now + timedelta(days=2),
        )
        future.clients.add(self.first)

        call_command('send_mailing', stdout=StringIO())

        self.assertEqual(len(mail.outbox), 2)  # только та, у которой время пришло
        self.assertFalse(future.attempts.exists())


class StatisticsTests(TestCase):
    """Проверки блока 6 (R16-R19)."""

    def setUp(self):
        self.message = Message.objects.create(subject='Акция', body='Текст.')
        self.ivan = Recipient.objects.create(full_name='Иван', email='ivan@example.com')
        self.petr = Recipient.objects.create(full_name='Пётр', email='petr@example.com')
        # Этот получатель ни в одной рассылке не состоит.
        self.alone = Recipient.objects.create(full_name='Одинокий', email='alone@example.com')
        self.now = timezone.now()

    def _mailing(self, clients, status=Mailing.Status.CREATED, ends_in=timedelta(days=1)):
        mailing = Mailing.objects.create(
            message=self.message,
            first_sent_at=self.now - timedelta(days=3),
            finished_at=self.now + ends_in,
            status=status,
        )
        mailing.clients.set(clients)
        return mailing

    def _letter(self, mailing, client, status, run=None):
        return MailingAttempt.objects.create(
            mailing=mailing, client=client, parent=run, status=status, server_response='ответ'
        )

    def _run(self, mailing, status=MailingAttempt.Status.SUCCESS):
        return MailingAttempt.objects.create(mailing=mailing, status=status, server_response='сводка')

    def test_home_counts_mailings_and_unique_recipients(self):
        self._mailing([self.ivan, self.petr])                                # создана
        self._mailing([self.ivan], Mailing.Status.STARTED)                   # запущена
        expired = self._mailing([self.petr], Mailing.Status.STARTED, ends_in=timedelta(days=-1))

        response = self.client.get(reverse('mailings:home'))

        self.assertEqual(response.status_code, 200)
        # Просроченная «Запущена» перед подсчётом закрывается и в активные не попадает.
        self.assertEqual(response.context['stats'], {'total': 3, 'active': 1, 'recipients': 2})
        expired.refresh_from_db()
        self.assertEqual(expired.status, Mailing.Status.FINISHED)

    def test_recipient_in_many_mailings_counted_once(self):
        for _ in range(3):
            self._mailing([self.ivan])

        self.assertEqual(home_stats()['recipients'], 1)

    def test_home_on_empty_database(self):
        Recipient.objects.all().delete()

        response = self.client.get(reverse('mailings:home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats'], {'total': 0, 'active': 0, 'recipients': 0})

    def test_attempt_totals_ignore_run_records(self):
        mailing = self._mailing([self.ivan, self.petr])
        # Два запуска: если бы их считали, итог был бы 7, а не 5.
        first_run = self._run(mailing, MailingAttempt.Status.SUCCESS)
        second_run = self._run(mailing, MailingAttempt.Status.FAILURE)
        self._letter(mailing, self.ivan, MailingAttempt.Status.SUCCESS, first_run)
        self._letter(mailing, self.petr, MailingAttempt.Status.SUCCESS, first_run)
        self._letter(mailing, self.ivan, MailingAttempt.Status.FAILURE, second_run)

        self.assertEqual(attempt_totals(), {'total': 3, 'success': 2, 'failure': 1})

    def test_report_is_per_mailing_without_join_fanout(self):
        busy = self._mailing([self.ivan, self.petr])
        quiet = self._mailing([self.ivan])
        run = self._run(busy)
        self._letter(busy, self.ivan, MailingAttempt.Status.SUCCESS, run)
        self._letter(busy, self.petr, MailingAttempt.Status.SUCCESS, run)
        self._letter(busy, self.petr, MailingAttempt.Status.FAILURE, run)

        rows = {row.pk: row for row in mailing_report()}

        self.assertEqual(
            (rows[busy.pk].letters_success, rows[busy.pk].letters_failure, rows[busy.pk].letters_total),
            (2, 1, 3),
        )
        # Рассылка, которую ни разу не запускали, показывает нули, а не пропадает.
        self.assertEqual(
            (rows[quiet.pk].letters_success, rows[quiet.pk].letters_failure, rows[quiet.pk].letters_total),
            (0, 0, 0),
        )

    def test_statistics_page_renders(self):
        mailing = self._mailing([self.ivan])
        self._letter(mailing, self.ivan, MailingAttempt.Status.SUCCESS, self._run(mailing))

        response = self.client.get(reverse('mailings:statistics'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['totals'], {'total': 1, 'success': 1, 'failure': 0})
        self.assertContains(response, 'Акция')

    def test_statistics_after_real_sending(self):
        """Сквозная проверка: настоящая отправка, одно письмо из трёх падает."""
        mailing = self._mailing([self.ivan, self.petr, self.alone])

        with patch(
            'mailings.services.send_mail',
            side_effect=[None, SMTPException('нет связи'), None],
        ):
            send_mailing(mailing)

        self.assertEqual(attempt_totals(), {'total': 3, 'success': 2, 'failure': 1})
        row = mailing_report().get(pk=mailing.pk)
        self.assertEqual((row.letters_success, row.letters_failure), (2, 1))
