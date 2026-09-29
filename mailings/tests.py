from django.test import TestCase
from django.urls import reverse

from mailings.models import Client as Recipient


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
