from django.test import TestCase
from django.urls import reverse

from mailings.models import Client as Recipient
from mailings.models import Message


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
