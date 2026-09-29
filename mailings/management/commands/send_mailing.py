from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from mailings.models import Mailing
from mailings.services import MailingFinished, send_mailing


class Command(BaseCommand):
    """Отправка рассылки из командной строки (R9).

        poetry run python manage.py send_mailing 3   # конкретную
        poetry run python manage.py send_mailing     # все, кому пора
    """

    help = 'Отправляет рассылку по номеру, а без номера — все, у которых подошло время.'

    def add_arguments(self, parser):
        parser.add_argument(
            'mailing_id',
            nargs='?',
            type=int,
            help='номер рассылки; без него берутся все незавершённые, время которых пришло',
        )

    def handle(self, *args, **options):
        mailing_id = options['mailing_id']

        if mailing_id is not None:
            mailings = list(Mailing.objects.filter(pk=mailing_id))
            if not mailings:
                raise CommandError(f'Рассылка №{mailing_id} не найдена.')
        else:
            Mailing.objects.finish_expired()
            mailings = list(
                Mailing.objects.exclude(status=Mailing.Status.FINISHED).filter(
                    first_sent_at__lte=timezone.now()
                )
            )
            if not mailings:
                self.stdout.write('Рассылок к отправке нет.')
                return

        for mailing in mailings:
            try:
                result = send_mailing(mailing)
            except MailingFinished as error:
                self.stdout.write(self.style.WARNING(f'№{mailing.pk}: {error}'))
                continue

            line = f'№{mailing.pk} «{mailing.message.subject}» — отправлено: {result.sent}, ошибок: {result.failed}.'
            style = self.style.SUCCESS if not result.failed else self.style.WARNING
            self.stdout.write(style(line))
