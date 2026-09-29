from django.core.management.base import BaseCommand

from mailings.models import Mailing


class Command(BaseCommand):
    """Фоновая задача из решения по Q3: закрывает рассылки, чьё время вышло.

    Вешается на планировщик ОС (Планировщик заданий Windows или cron):
        poetry run python manage.py update_mailing_statuses
    """

    help = 'Переводит в «Завершена» рассылки, у которых прошло время окончания.'

    def handle(self, *args, **options):
        updated = Mailing.objects.finish_expired()
        self.stdout.write(self.style.SUCCESS(f'Завершено рассылок: {updated}'))
